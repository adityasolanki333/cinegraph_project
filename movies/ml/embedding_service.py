"""
Semantic Embedding Service for CineGraph
Provides TF-IDF based text embeddings for movies and TV shows.
Used as a fallback when Pinecone is unavailable.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class EmbeddingResult:
    tmdb_id: int
    media_type: str
    embedding: np.ndarray
    text_hash: str


def _extract_year(date_str: str) -> int:
    if not date_str or len(date_str) < 4:
        return 0
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return 0


def _recency_score(year: int) -> float:
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


def _popularity_score(vote_average: float, popularity: float = 0) -> float:
    rating_score = min(1.0, max(0.0, (vote_average - 5.0) / 5.0)) if vote_average > 0 else 0.0
    pop_score = min(1.0, popularity / 200.0) if popularity > 0 else 0.0
    return 0.6 * rating_score + 0.4 * pop_score


class SemanticEmbeddingService:
    def __init__(self, max_features: int = 5000, ngram_range: Tuple[int, int] = (1, 2)):
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            stop_words='english',
            lowercase=True,
            strip_accents='unicode'
        )
        self.embedding_cache: Dict[str, EmbeddingResult] = {}
        self.corpus_texts: List[str] = []
        self.corpus_ids: List[Tuple[int, str]] = []
        self.is_fitted = False
        self.corpus_embeddings: Optional[np.ndarray] = None
        self._prefitted = False

    def _create_text_hash(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]

    def _extract_text(self, item: Dict[str, Any]) -> str:
        title = item.get('title') or item.get('name') or ''
        overview = item.get('overview') or ''
        genres = ''
        genre_data = item.get('genres') or item.get('genre_ids') or []
        if isinstance(genre_data, list) and genre_data:
            if isinstance(genre_data[0], dict):
                genres = ' '.join(g.get('name', '') for g in genre_data)
            elif isinstance(genre_data[0], str):
                genres = ' '.join(genre_data)
        elif isinstance(genre_data, str):
            genres = genre_data

        release_date = item.get('release_date') or item.get('first_air_date') or ''
        year = release_date[:4] if release_date and len(release_date) >= 4 else ''

        parts = [title, title, overview]
        if genres:
            parts.append(genres)
        if year:
            parts.append(year)

        return ' '.join(parts).strip()

    def prefit_from_db(self) -> bool:
        if self._prefitted:
            return self.is_fitted
        self._prefitted = True

        try:
            from movies.models import TmdbTrainingData
            count = TmdbTrainingData.objects.count()
            if count == 0:
                return False

            limit = min(count, 20000)
            qs = TmdbTrainingData.objects.order_by('-popularity')[:limit]

            texts = []
            for row in qs.iterator(chunk_size=2000):
                parts = [row.title or '', row.title or '', row.overview or '']
                if row.genres:
                    parts.append(row.genres)
                if row.release_date and len(row.release_date) >= 4:
                    parts.append(row.release_date[:4])
                text = ' '.join(parts).strip()
                if text:
                    texts.append(text)

            if texts:
                self.vectorizer.fit(texts)
                self.is_fitted = True
                print(f"SemanticEmbeddingService: pre-fitted on {len(texts)} movies from DB")
                return True
        except Exception as e:
            print(f"SemanticEmbeddingService: prefit failed — {e}")
        return False

    def fit_corpus(self, items: List[Dict[str, Any]]) -> None:
        self.corpus_texts = []
        self.corpus_ids = []

        for item in items:
            text = self._extract_text(item)
            if text:
                tmdb_id = item.get('id') or item.get('tmdb_id') or item.get('tmdbId')
                media_type = item.get('media_type', 'movie')
                self.corpus_texts.append(text)
                self.corpus_ids.append((tmdb_id, media_type))

        if self.corpus_texts:
            if self._prefitted and self.is_fitted:
                self.corpus_embeddings = self.vectorizer.transform(self.corpus_texts)
            else:
                self.corpus_embeddings = self.vectorizer.fit_transform(self.corpus_texts)
                self.is_fitted = True

    def encode_query(self, text: str) -> np.ndarray:
        if not self.is_fitted:
            return np.array([])
        query_embedding = self.vectorizer.transform([text])
        return query_embedding

    def compute_similarity(self, query_embedding: np.ndarray,
                          item_embeddings: np.ndarray) -> np.ndarray:
        if query_embedding.size == 0 or item_embeddings.size == 0:
            return np.array([])
        similarities = cosine_similarity(query_embedding, item_embeddings)
        return similarities.flatten()

    def get_or_create_embeddings(self, items_list: List[Dict[str, Any]]) -> np.ndarray:
        if not items_list:
            return np.array([])

        texts = []
        cache_keys = []
        uncached_indices = []

        for idx, item in enumerate(items_list):
            text = self._extract_text(item)
            text_hash = self._create_text_hash(text)
            cache_key = f"{item.get('id', idx)}_{text_hash}"
            cache_keys.append(cache_key)
            texts.append(text)

            if cache_key in self.embedding_cache:
                pass
            else:
                uncached_indices.append(idx)

        self.fit_corpus(items_list)

        if not self.is_fitted:
            return np.array([])

        all_embeddings = self.corpus_embeddings.toarray()

        for idx in uncached_indices:
            if idx < len(all_embeddings):
                item = items_list[idx]
                tmdb_id = item.get('id') or item.get('tmdb_id') or idx
                media_type = item.get('media_type', 'movie')

                self.embedding_cache[cache_keys[idx]] = EmbeddingResult(
                    tmdb_id=tmdb_id,
                    media_type=media_type,
                    embedding=all_embeddings[idx],
                    text_hash=self._create_text_hash(texts[idx])
                )

        return self.corpus_embeddings

    def search_with_similarity(self, query: str, items: List[Dict[str, Any]],
                               top_k: Optional[int] = None,
                               apply_reranking: bool = True) -> List[Tuple[Dict[str, Any], float]]:
        if not items or not query:
            return [(item, 0.0) for item in items]

        self.prefit_from_db()

        item_embeddings = self.get_or_create_embeddings(items)

        if not self.is_fitted:
            return [(item, 0.0) for item in items]

        query_embedding = self.encode_query(query)

        if query_embedding.size == 0:
            return [(item, 0.0) for item in items]

        similarities = self.compute_similarity(query_embedding, item_embeddings)

        results = list(zip(items, similarities.tolist()))

        if apply_reranking:
            query_lower = query.lower()
            reranked = []
            for item, sim in results:
                title = (item.get('title') or item.get('name') or '').lower()
                title_boost = 0.15 if query_lower in title else (0.10 if title in query_lower else 0.0)

                release_date = item.get('release_date') or item.get('first_air_date') or ''
                year = _extract_year(release_date)
                recency = _recency_score(year)

                vote_avg = float(item.get('vote_average', 0))
                pop = float(item.get('popularity', 0))
                pop_score = _popularity_score(vote_avg, pop)

                composite = (
                    0.65 * sim
                    + 0.15 * recency
                    + 0.10 * pop_score
                    + title_boost
                )
                reranked.append((item, min(1.0, composite)))

            reranked.sort(key=lambda x: x[1], reverse=True)
            results = reranked
        else:
            results.sort(key=lambda x: x[1], reverse=True)

        if top_k:
            results = results[:top_k]

        return results

    def get_cache_stats(self) -> Dict[str, Any]:
        return {
            'cache_size': len(self.embedding_cache),
            'corpus_size': len(self.corpus_texts),
            'is_fitted': self.is_fitted,
            'prefitted': self._prefitted,
            'vocabulary_size': len(self.vectorizer.vocabulary_) if self.is_fitted else 0
        }

    def clear_cache(self) -> None:
        self.embedding_cache.clear()
        self.corpus_texts = []
        self.corpus_ids = []
        self.is_fitted = False
        self._prefitted = False
        self.corpus_embeddings = None


semantic_embedding_service = SemanticEmbeddingService()
