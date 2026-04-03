"""
Pinecone vector search service for Cinema-Guide.
Drop-in companion to chroma_service.py — same public API.

Used by ml_api.py for semantic search and similar-movie lookups.
"""

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from sentence_transformers import SentenceTransformer

PINECONE_API_KEY = (
    os.environ.get("PINECONE_API_KEY") or
    os.environ.get("PINE_CONE_API_KEY") or
    os.environ.get("PINECONE_KEY") or
    ""
)
INDEX_NAME = "cinema-guide"
NAMESPACE  = "movies"


class PineconeService:
    """
    Singleton wrapper around a Pinecone index.
    Provides search() and get_nearest_neighbors() with a 5-minute result cache.
    """

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
        self._nn_cache_ttl = 300  # seconds

        if not PINECONE_API_KEY:
            print("PineconeService: PINECONE_API_KEY not set — service disabled.")
            return

        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=PINECONE_API_KEY)

            # Check the index exists
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

    # ── Public API ────────────────────────────────────────────────────────────

    def is_initialized(self) -> bool:
        return self._initialized and self.index is not None

    def search(
        self,
        query: str,
        k: int = 20,
        filters: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic text search — embed `query` then query Pinecone for top-k results.
        `filters` is an optional Pinecone metadata filter dict, e.g.
            {"original_language": {"$eq": "en"}}
        """
        if not self.is_initialized():
            return []

        try:
            query_vec = self.model.encode(query).tolist()

            response = self.index.query(
                vector=query_vec,
                top_k=k * 2,          # over-fetch to allow dedup
                namespace=NAMESPACE,
                include_metadata=True,
                filter=filters or None,
            )

            return self._format_matches(response.matches, skip_ids=set(), limit=k)

        except Exception as e:
            print(f"PineconeService.search error: {e}")
            return []

    def get_nearest_neighbors(
        self, tmdb_id: int, k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find movies similar to `tmdb_id` by looking up its stored vector
        and querying for its nearest neighbours.
        Caches results for 5 minutes.
        """
        if not self.is_initialized():
            return []

        # Cache hit
        if tmdb_id in self._nn_cache:
            ts, cached = self._nn_cache[tmdb_id]
            if time.time() - ts < self._nn_cache_ttl:
                return cached[:k]

        try:
            # 1. Fetch the stored embedding
            fetch_result = self.index.fetch(
                ids=[str(tmdb_id)], namespace=NAMESPACE
            )
            vectors = fetch_result.vectors
            if not vectors or str(tmdb_id) not in vectors:
                # Movie not in vector DB. We must auto-fetch, embed, and index it on the fly!
                try:
                    from movies.api import tmdb_request
                    details = tmdb_request(f"/movie/{tmdb_id}", params={"append_to_response": "credits"})
                    if details:
                        # Format it
                        cast = []
                        director = ""
                        credits = details.get('credits', {})
                        if credits:
                            cast = [c['name'] for c in credits.get('cast', [])[:5]]
                            directors = [c['name'] for c in credits.get('crew', []) if c.get('job') == 'Director']
                            if directors:
                                director = directors[0]
                                
                        genres = [g['name'] for g in details.get('genres', [])]
                        
                        movie_data = {
                            'id': details.get('id') or tmdb_id,
                            'title': details.get('title') or details.get('name', ''),
                            'overview': details.get('overview', ''),
                            'genres': ', '.join(genres),
                            'director': director,
                            'cast': ', '.join(cast),
                            'release_date': details.get('release_date') or details.get('first_air_date', ''),
                            'vote_average': details.get('vote_average', 0),
                            'poster_path': details.get('poster_path', '')
                        }
                        
                        # Upsert synchronously so we can use it immediately!
                        self.upsert_movie(movie_data)
                        print(f"PineconeService: Auto-indexed missing movie: {movie_data['title']}")
                        
                        # Now re-fetch the newly minted vector
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

            # 2. Query for neighbours (fetch extra to account for dedup/self)
            response = self.index.query(
                vector=source_vec,
                top_k=k * 3 + 1,
                namespace=NAMESPACE,
                include_metadata=True,
            )

            results = self._format_matches(
                response.matches,
                skip_ids={str(tmdb_id)},
                skip_titles={source_title} if source_title else set(),
                limit=k,
                explanation_template="Thematically Similar ({pct}%)",
            )

            # Cache
            self._nn_cache[tmdb_id] = (time.time(), results)
            self._evict_cache()

            return results

        except Exception as e:
            print(f"PineconeService.get_nearest_neighbors error: {e}")
            return []

    # ── Internals ─────────────────────────────────────────────────────────────

    def upsert_movie(self, movie_data: Dict[str, Any]):
        """
        Embed and upsert a movie into the Pinecone index.
        """
        if not self.is_initialized():
            return
            
        try:
            # Create text to encode matching ingestion format
            title = str(movie_data.get('title', ''))
            overview = str(movie_data.get('overview', ''))
            genres = str(movie_data.get('genres', ''))
            director = str(movie_data.get('director', ''))
            cast = str(movie_data.get('cast', ''))
            
            text_to_encode = f"Title: {title}. Overview: {overview}. Genres: {genres}. Director: {director}. Cast: {cast}."
            vector = self.model.encode(text_to_encode).tolist()
            
            self.index.upsert(
                vectors=[
                    {
                        "id": str(movie_data['id']),
                        "values": vector,
                        "metadata": {
                            "title": title,
                            "overview": overview,
                            "genres": genres,
                            "director": director,
                            "poster_path": str(movie_data.get('poster_path', '')),
                            "vote_average": float(movie_data.get('vote_average', 0.0)),
                            "release_date": str(movie_data.get('release_date', ''))
                        }
                    }
                ],
                namespace=NAMESPACE
            )
            print(f"PineconeService: Upserted movie {title} ({movie_data['id']})")
        except Exception as e:
            print(f"PineconeService.upsert_movie error: {e}")

    def _format_matches(
        self,
        matches,
        skip_ids: set = None,
        skip_titles: set = None,
        limit: int = 20,
        explanation_template: str = "Semantic Match ({pct}%)",
    ) -> List[Dict[str, Any]]:
        skip_ids    = skip_ids    or set()
        skip_titles = skip_titles or set()
        results     = []
        seen_titles : set = set(skip_titles)

        for match in matches:
            if len(results) >= limit:
                break

            if match.id in skip_ids:
                continue

            meta  = match.metadata or {}
            title = meta.get("title", "Unknown")
            title_key = title.strip().lower()

            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Pinecone cosine score is in [0, 1] (1 = identical)
            similarity = round(float(match.score), 4)

            results.append({
                "id":           int(match.id) if match.id.isdigit() else match.id,
                "title":        title,
                "overview":     meta.get("overview", ""),
                "release_date": meta.get("release_date", ""),
                "vote_average": meta.get("vote_average", 0),
                "poster_path":  meta.get("poster_path", ""),
                "director":     meta.get("director", ""),
                "genres":       meta.get("genres", ""),
                "similarity":   similarity,
                "explanation":  explanation_template.format(pct=int(similarity * 100)),
            })

        return results

    def _evict_cache(self):
        if len(self._nn_cache) > 128:
            now     = time.time()
            expired = [
                k for k, (ts, _) in self._nn_cache.items()
                if now - ts > self._nn_cache_ttl
            ]
            for k in expired:
                del self._nn_cache[k]


# Singleton instance — imported by ml_api.py
pinecone_service = PineconeService()
