"""
Management command to refresh the Pinecone vector index with recent/popular movies from TMDB.

Usage:
    python manage.py refresh_pinecone
    python manage.py refresh_pinecone --pages 5
    python manage.py refresh_pinecone --dry-run
"""

import logging
import os
import time
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')
TMDB_BASE_URL = "https://api.themoviedb.org/3"


def tmdb_api_request(endpoint, params=None):
    import requests
    if not TMDB_API_KEY:
        return None
    url = f"{TMDB_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("TMDB request failed: %s — %s", endpoint, e)
        return None


class Command(BaseCommand):
    help = "Fetch recent/popular/trending movies from TMDB and upsert into Pinecone"

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=3, help="Pages to fetch per endpoint (default 3)")
        parser.add_argument("--dry-run", action="store_true", help="Fetch from TMDB but skip Pinecone upsert")
        parser.add_argument("--batch-size", type=int, default=50, help="Pinecone upsert batch size")

    def handle(self, *args, **options):
        pages = options["pages"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if not TMDB_API_KEY:
            self.stderr.write(self.style.ERROR("TMDB_API_KEY not set"))
            return

        self.stdout.write(self.style.NOTICE(f"Fetching movies from TMDB (pages={pages}, dry_run={dry_run})"))

        all_movies = {}

        endpoints = [
            ("/trending/movie/week", "Trending (week)"),
            ("/movie/now_playing", "Now Playing"),
            ("/movie/popular", "Popular"),
            ("/movie/upcoming", "Upcoming"),
            ("/movie/top_rated", "Top Rated"),
        ]

        discover_configs = [
            {"sort_by": "popularity.desc", "vote_count.gte": "100"},
            {"sort_by": "revenue.desc", "vote_count.gte": "50"},
            {"sort_by": "primary_release_date.desc", "vote_count.gte": "20"},
        ]

        for endpoint, label in endpoints:
            for page in range(1, pages + 1):
                data = tmdb_api_request(endpoint, {"page": page})
                if not data or "results" not in data:
                    continue
                for movie in data["results"]:
                    mid = movie.get("id")
                    if mid and mid not in all_movies:
                        all_movies[mid] = movie
            self.stdout.write(f"  {label}: collected {len(all_movies)} unique movies so far")

        for i, params in enumerate(discover_configs):
            for page in range(1, pages + 1):
                params_with_page = {**params, "page": page}
                data = tmdb_api_request("/discover/movie", params_with_page)
                if not data or "results" not in data:
                    continue
                for movie in data["results"]:
                    mid = movie.get("id")
                    if mid and mid not in all_movies:
                        all_movies[mid] = movie
            self.stdout.write(f"  Discover config {i+1}: collected {len(all_movies)} unique movies so far")

        self.stdout.write(self.style.SUCCESS(f"Total unique movies fetched: {len(all_movies)}"))

        if not all_movies:
            self.stdout.write("No movies to process.")
            return

        enriched = []
        movie_list = list(all_movies.values())
        self.stdout.write(f"Enriching {len(movie_list)} movies with credits/keywords...")

        import concurrent.futures

        def enrich_movie(movie):
            mid = movie["id"]
            details = tmdb_api_request(f"/movie/{mid}", {"append_to_response": "credits,keywords"})
            if not details:
                return movie
            movie["overview"] = details.get("overview") or movie.get("overview", "")
            movie["poster_path"] = details.get("poster_path") or movie.get("poster_path", "")
            movie["vote_average"] = details.get("vote_average") or movie.get("vote_average", 0)
            movie["popularity"] = details.get("popularity") or movie.get("popularity", 0)
            movie["release_date"] = details.get("release_date") or movie.get("release_date", "")
            movie["genres"] = [g["name"] for g in details.get("genres", [])]
            credits = details.get("credits", {})
            movie["cast"] = [c["name"] for c in credits.get("cast", [])[:5]]
            directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
            movie["director"] = directors[0] if directors else ""
            keywords = details.get("keywords", {}).get("keywords", [])
            movie["keyword_names"] = [k["name"] for k in keywords[:10]]
            return movie

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            enriched = list(executor.map(enrich_movie, movie_list))

        self.stdout.write(self.style.SUCCESS(f"Enriched {len(enriched)} movies"))

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — skipping Pinecone upsert"))
            for m in enriched[:5]:
                self.stdout.write(f"  [{m['id']}] {m.get('title', '?')} ({m.get('release_date', '?')})")
            return

        from movies.ml.pinecone_service import pinecone_service

        if not pinecone_service.is_initialized():
            self.stderr.write(self.style.ERROR("PineconeService not initialized — check API key and index"))
            return

        inserted = 0
        updated = 0
        skipped = 0
        start = time.time()

        existing_ids = set()
        try:
            all_ids = [str(m["id"]) for m in enriched]
            for chunk_start in range(0, len(all_ids), 100):
                chunk_ids = all_ids[chunk_start : chunk_start + 100]
                fetch_result = pinecone_service.index.fetch(ids=chunk_ids, namespace="movies")
                existing_ids.update(fetch_result.vectors.keys())
            self.stdout.write(f"  Pre-check: {len(existing_ids)} already in index, {len(all_ids) - len(existing_ids)} new")
        except Exception as e:
            self.stderr.write(f"  Could not pre-check existing IDs: {e}")

        for i in range(0, len(enriched), batch_size):
            batch = enriched[i : i + batch_size]
            for movie in batch:
                try:
                    genres_str = ", ".join(movie.get("genres", [])) if isinstance(movie.get("genres"), list) else str(movie.get("genres", ""))
                    cast_str = ", ".join(movie.get("cast", [])) if isinstance(movie.get("cast"), list) else str(movie.get("cast", ""))
                    keywords_str = ", ".join(movie.get("keyword_names", []))

                    release_date = str(movie.get("release_date", ""))
                    release_year = ""
                    if release_date and len(release_date) >= 4:
                        release_year = release_date[:4]

                    movie_data = {
                        "id": movie["id"],
                        "title": movie.get("title", ""),
                        "overview": movie.get("overview", ""),
                        "genres": genres_str,
                        "director": movie.get("director", ""),
                        "cast": cast_str,
                        "release_date": release_date,
                        "release_year": release_year,
                        "vote_average": float(movie.get("vote_average", 0)),
                        "popularity": float(movie.get("popularity", 0)),
                        "poster_path": movie.get("poster_path", ""),
                        "keywords": keywords_str,
                        "original_language": movie.get("original_language", ""),
                    }
                    pinecone_service.upsert_movie(movie_data)
                    if str(movie["id"]) in existing_ids:
                        updated += 1
                    else:
                        inserted += 1
                except Exception as e:
                    skipped += 1
                    self.stderr.write(f"  Skip {movie.get('id')}: {e}")

            self.stdout.write(f"  Batch {i // batch_size + 1}: inserted {inserted}, updated {updated}, skipped {skipped}")

        elapsed = time.time() - start
        self.stdout.write(self.style.SUCCESS(
            f"Done. Inserted {inserted}, updated {updated}, skipped {skipped} in {elapsed:.1f}s"
        ))
