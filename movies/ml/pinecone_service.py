"""
Pinecone vector search service for Cinema-Guide.
Drop-in companion to chroma_service.py — same public API.

Used by ml_api.py for semantic search and similar-movie lookups.
"""

import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sentence_transformers import SentenceTransformer

PINECONE_API_KEY = (
    os.environ.get("PINECONE_API_KEY") or
    os.environ.get("PINE_CONE_API_KEY") or
    os.environ.get("PINECONE_KEY") or
    ""
)
INDEX_NAME = "cinema-guide"
NAMESPACE  = "movies"

RECENCY_WEIGHT = 0.15
POPULARITY_WEIGHT = 0.10
SIMILARITY_WEIGHT = 0.75

FRANCHISE_PATTERNS = [
    r"^(.*?)\s*\d+$",
    r"^(.*?)\s*:\s",
    r"^(.*?)\s+part\s+\d",
    r"^(.*?)\s+chapter\s+\d",
]


from movies.ml.embedding_text import build_enriched_text as _build_enriched_text


def _extract_year(date_str: str) -> int:
    if not date_str or len(date_str) < 4:
        return 0
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return 0


def _compute_recency_score(year: int) -> float:
    if year <= 0:
        return 0.0
    current_year = datetime.now().year
    age = max(0, current_year - year)
    if age <= 2:
        return 1.0
    elif age <= 5:
        return 0.8
    elif age <= 10:
        return 0.6
    elif age <= 20:
        return 0.4
    elif age <= 40:
        return 0.2
    return 0.1


def _compute_popularity_score(vote_average: float, popularity: float = 0) -> float:
    rating_score = min(1.0, max(0.0, (vote_average - 5.0) / 5.0)) if vote_average > 0 else 0.0
    pop_score = min(1.0, popularity / 200.0) if popularity > 0 else 0.0
    return 0.6 * rating_score + 0.4 * pop_score


def _extract_franchise_name(title: str) -> Optional[str]:
    title_lower = title.strip().lower()
    for pattern in FRANCHISE_PATTERNS:
        m = re.match(pattern, title_lower, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            if len(name) >= 3:
                return name
    return None


def _is_franchise_query(query: str) -> bool:
    query_lower = query.lower().strip()
    known_franchises = [
        "john wick", "fast and furious", "mission impossible",
        "spider-man", "spider man", "batman", "star wars",
        "harry potter", "lord of the rings", "avengers",
        "transformers", "x-men", "iron man", "captain america",
        "thor", "jurassic", "pirates of the caribbean",
        "the matrix", "mad max", "alien", "terminator",
        "indiana jones", "rocky", "rambo", "die hard",
        "toy story", "shrek", "incredibles", "frozen",
        "hunger games", "twilight", "maze runner", "divergent",
    ]
    for franchise in known_franchises:
        if franchise in query_lower or query_lower in franchise:
            return True
    sequel_tokens = re.compile(
        r'\b(part\s*\d|chapter\s*\d|sequel|prequel|trilogy|saga|franchise|series)\b',
        re.IGNORECASE,
    )
    if sequel_tokens.search(query_lower):
        return True
    return False


class PineconeService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.index = None
        self.model = None
        self._nn_cache: Dict[int, Tuple[float, List[Dict[str, Any]]]] = {}
        self._nn_cache_ttl = 300

        if not PINECONE_API_KEY:
            print("PineconeService: PINECONE_API_KEY not set — service disabled.")
            return

        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=PINECONE_API_KEY)

            existing = [idx.name for idx in pc.list_indexes()]
            if INDEX_NAME not in existing:
                print(
                    f"PineconeService: index '{INDEX_NAME}' not found. "
                    "Run scripts/ingest_pinecone.py first."
                )
                return

            self.index = pc.Index(INDEX_NAME)

            print("PineconeService: loading sentence-transformer model...")
            self.model = SentenceTransformer("all-MiniLM-L6-v2")

            self._initialized = True
            stats = self.index.describe_index_stats()
            print(
                f"PineconeService: ready. "
                f"Index has {stats.total_vector_count:,} vectors."
            )

        except Exception as e:
            print(f"PineconeService init error: {e}")

    def is_initialized(self) -> bool:
        return self._initialized and self.index is not None

    def search(
        self,
        query: str,
        k: int = 20,
        filters: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        if not self.is_initialized():
            return []

        try:
            query_vec = self.model.encode(query).tolist()
            is_franchise = _is_franchise_query(query)

            response = self.index.query(
                vector=query_vec,
                top_k=k * 3,
                namespace=NAMESPACE,
                include_metadata=True,
                filter=filters or None,
            )

            raw_results = self._format_matches_v2(
                response.matches,
                skip_ids=set(),
                limit=k * 2,
            )

            reranked = self._rerank(raw_results, query, is_franchise=is_franchise)

            return reranked[:k]

        except Exception as e:
            print(f"PineconeService.search error: {e}")
            return []

    def get_nearest_neighbors(
        self, tmdb_id: int, k: int = 20
    ) -> List[Dict[str, Any]]:
        if not self.is_initialized():
            return []

        if tmdb_id in self._nn_cache:
            ts, cached = self._nn_cache[tmdb_id]
            if time.time() - ts < self._nn_cache_ttl:
                return cached[:k]

        try:
            fetch_result = self.index.fetch(
                ids=[str(tmdb_id)], namespace=NAMESPACE
            )
            vectors = fetch_result.vectors
            if not vectors or str(tmdb_id) not in vectors:
                try:
                    from movies.api import tmdb_request
                    details = tmdb_request(f"/movie/{tmdb_id}", params={"append_to_response": "credits,keywords"})
                    if details:
                        cast = []
                        director = ""
                        credits = details.get('credits', {})
                        if credits:
                            cast = [c['name'] for c in credits.get('cast', [])[:5]]
                            directors = [c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director']
                            if directors:
                                director = directors[0]

                        genres = [g['name'] for g in details.get('genres', [])]
                        keywords_list = details.get('keywords', {}).get('keywords', [])
                        keyword_names = [kw['name'] for kw in keywords_list[:10]]
                        release_date = details.get('release_date') or details.get('first_air_date', '')
                        release_year = release_date[:4] if release_date and len(release_date) >= 4 else ''

                        movie_data = {
                            'id': details.get('id') or tmdb_id,
                            'title': details.get('title') or details.get('name', ''),
                            'overview': details.get('overview', ''),
                            'genres': ', '.join(genres),
                            'director': director,
                            'cast': ', '.join(cast),
                            'release_date': release_date,
                            'release_year': release_year,
                            'vote_average': details.get('vote_average', 0),
                            'popularity': details.get('popularity', 0),
                            'poster_path': details.get('poster_path', ''),
                            'keywords': ', '.join(keyword_names),
                        }

                        self.upsert_movie(movie_data)
                        print(f"PineconeService: Auto-indexed missing movie: {movie_data['title']}")

                        fetch_result = self.index.fetch(ids=[str(tmdb_id)], namespace=NAMESPACE)
                        vectors = fetch_result.vectors
                        if not vectors or str(tmdb_id) not in vectors:
                            return []
                    else:
                        return []
                except Exception as e:
                    print(f"Pinecone auto-ingest failed: {e}")
                    return []

            source_vec  = vectors[str(tmdb_id)].values
            source_meta = vectors[str(tmdb_id)].metadata or {}
            source_title = source_meta.get("title", "").strip().lower()

            response = self.index.query(
                vector=source_vec,
                top_k=k * 3 + 1,
                namespace=NAMESPACE,
                include_metadata=True,
            )

            results = self._format_matches_v2(
                response.matches,
                skip_ids={str(tmdb_id)},
                limit=k,
                explanation_template="Thematically Similar ({pct}%)",
            )

            results = [r for r in results if r["title"].strip().lower() != source_title or r["release_year"] != _extract_year(source_meta.get("release_date", ""))]

            self._nn_cache[tmdb_id] = (time.time(), results)
            self._evict_cache()

            return results[:k]

        except Exception as e:
            print(f"PineconeService.get_nearest_neighbors error: {e}")
            return []

    def upsert_movie(self, movie_data: Dict[str, Any]):
        if not self.is_initialized():
            return

        try:
            release_date = str(movie_data.get("release_date", ""))
            release_year = str(movie_data.get("release_year", ""))
            if not release_year and release_date and len(release_date) >= 4:
                release_year = release_date[:4]

            movie_data_with_year = {**movie_data, "release_year": release_year}
            text_to_encode = _build_enriched_text(movie_data_with_year)
            vector = self.model.encode(text_to_encode).tolist()

            title = str(movie_data.get("title", ""))
            overview = str(movie_data.get("overview", ""))
            genres = str(movie_data.get("genres", ""))
            director = str(movie_data.get("director", ""))
            poster_path = str(movie_data.get("poster_path", ""))
            vote_average = float(movie_data.get("vote_average", 0.0))
            popularity = float(movie_data.get("popularity", 0.0))

            metadata = {
                "title": title,
                "overview": overview[:1000],
                "genres": genres,
                "director": director,
                "poster_path": poster_path,
                "vote_average": vote_average,
                "popularity": popularity,
                "release_date": release_date,
                "release_year": release_year,
            }

            original_language = str(movie_data.get("original_language", ""))
            if original_language:
                metadata["original_language"] = original_language

            keywords = str(movie_data.get("keywords", ""))
            if keywords:
                metadata["keywords"] = keywords[:500]

            self.index.upsert(
                vectors=[
                    {
                        "id": str(movie_data["id"]),
                        "values": vector,
                        "metadata": metadata,
                    }
                ],
                namespace=NAMESPACE,
            )
        except Exception as e:
            print(f"PineconeService.upsert_movie error: {e}")

    def _format_matches_v2(
        self,
        matches,
        skip_ids: Set[str] = None,
        limit: int = 20,
        explanation_template: str = "Semantic Match ({pct}%)",
    ) -> List[Dict[str, Any]]:
        skip_ids = skip_ids or set()
        results = []
        seen_keys: Set[str] = set()

        for match in matches:
            if len(results) >= limit:
                break

            if match.id in skip_ids:
                continue

            meta = match.metadata or {}
            title = meta.get("title", "Unknown")
            release_date = meta.get("release_date", "")
            year = _extract_year(release_date)
            release_year_str = meta.get("release_year", "")
            if not release_year_str and year > 0:
                release_year_str = str(year)

            dedup_key = f"{title.strip().lower()}|{year}" if year > 0 else title.strip().lower()

            tmdb_id_str = match.id
            tmdb_dedup = f"tmdb:{tmdb_id_str}"
            if tmdb_dedup in seen_keys or dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            seen_keys.add(tmdb_dedup)

            similarity = round(float(match.score), 4)
            popularity = float(meta.get("popularity", 0))
            vote_average = float(meta.get("vote_average", 0))

            results.append({
                "id": int(match.id) if match.id.isdigit() else match.id,
                "title": title,
                "overview": meta.get("overview", ""),
                "release_date": release_date,
                "release_year": year,
                "vote_average": vote_average,
                "popularity": popularity,
                "poster_path": meta.get("poster_path", ""),
                "director": meta.get("director", ""),
                "genres": meta.get("genres", ""),
                "keywords": meta.get("keywords", ""),
                "similarity": similarity,
                "explanation": explanation_template.format(pct=int(similarity * 100)),
            })

        return results

    def _rerank(
        self,
        results: List[Dict[str, Any]],
        query: str,
        is_franchise: bool = False,
        sim_weight: float = SIMILARITY_WEIGHT,
        recency_weight: float = RECENCY_WEIGHT,
        popularity_weight: float = POPULARITY_WEIGHT,
    ) -> List[Dict[str, Any]]:
        if not results:
            return results

        query_lower = query.lower().strip()

        for item in results:
            similarity = item["similarity"]
            year = item.get("release_year", 0) or _extract_year(item.get("release_date", ""))
            recency = _compute_recency_score(year)
            pop = _compute_popularity_score(
                item.get("vote_average", 0),
                item.get("popularity", 0),
            )

            title_lower = item["title"].lower()
            title_boost = 0.0
            if query_lower in title_lower:
                title_boost = 0.15
            elif title_lower in query_lower:
                title_boost = 0.10

            composite = (
                sim_weight * similarity
                + recency_weight * recency
                + popularity_weight * pop
                + title_boost
            )
            item["composite_score"] = min(1.0, composite)
            item["recency_boost"] = round(recency, 3)
            item["popularity_boost"] = round(pop, 3)

            match_pct = int(item["composite_score"] * 100)
            labels = []
            if similarity >= 0.7:
                labels.append("Semantic match")
            if recency >= 0.8:
                labels.append("Recent")
            if pop >= 0.6:
                labels.append("Popular")
            if title_boost > 0:
                labels.append("Title match")

            item["match_quality"] = ", ".join(labels) if labels else "Related"
            item["explanation"] = f"{match_pct}% match — {item['match_quality']}"

        if is_franchise:
            franchise_items = [
                r for r in results
                if query_lower in r["title"].lower() or r["title"].lower() in query_lower
            ]
            other_items = [r for r in results if r not in franchise_items]

            franchise_items.sort(key=lambda x: x.get("release_year", 0) or 0, reverse=True)
            other_items.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

            return franchise_items + other_items
        else:
            results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)
            return results

    def _evict_cache(self):
        if len(self._nn_cache) > 128:
            now = time.time()
            expired = [
                k for k, (ts, _) in self._nn_cache.items()
                if now - ts > self._nn_cache_ttl
            ]
            for k in expired:
                del self._nn_cache[k]


pinecone_service = PineconeService()
