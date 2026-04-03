"""
Embedding Manager

Builds and stores user profile embeddings by averaging embeddings of
top-rated/favorited movies. Uses these for user-to-item similarity scoring.
"""
from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple


class EmbeddingManager:

    def build_user_embedding(self, user) -> Optional[List[float]]:
        from movies.models import UserEmbedding, UserFavorites, UserReview
        from .signal_aggregator import signal_aggregator

        signals = signal_aggregator.get_user_signals(user)
        if not signals:
            return None

        top_items = sorted(signals.items(), key=lambda x: x[1], reverse=True)[:20]
        top_tmdb_ids = [tid for tid, _ in top_items]

        embeddings = self._get_item_embeddings(top_tmdb_ids)
        if not embeddings:
            return None

        dims = set(len(v) for v in embeddings.values())
        if len(dims) > 1:
            target_dim = max(dims, key=lambda d: sum(1 for v in embeddings.values() if len(v) == d))
            embeddings = {k: v for k, v in embeddings.items() if len(v) == target_dim}
            if not embeddings:
                return None

        weights = [signals.get(tid, 0.5) for tid in embeddings.keys()]
        vectors = list(embeddings.values())

        weight_arr = np.array(weights)
        vec_arr = np.array(vectors)
        weighted_avg = np.average(vec_arr, axis=0, weights=weight_arr)

        norm = np.linalg.norm(weighted_avg)
        if norm > 0:
            weighted_avg = weighted_avg / norm

        embedding_list = weighted_avg.tolist()

        UserEmbedding.objects.update_or_create(
            user=user,
            defaults={
                'embedding': embedding_list,
                'embedding_version': 'v2_weighted',
            }
        )

        return embedding_list

    def _get_item_embeddings(self, tmdb_ids: List[int]) -> Dict[int, List[float]]:
        from movies.models import ItemEmbedding, TmdbMovieCache

        result = {}

        existing = ItemEmbedding.objects.filter(
            tmdb_id__in=tmdb_ids,
        ).values('tmdb_id', 'embedding')
        for ie in existing:
            if ie['embedding']:
                result[ie['tmdb_id']] = ie['embedding']

        missing = [tid for tid in tmdb_ids if tid not in result]
        if missing:
            cached_movies = TmdbMovieCache.objects.filter(
                tmdb_id__in=missing
            ).values('tmdb_id', 'title', 'overview', 'genres')

            for movie in cached_movies:
                emb = self._generate_tfidf_embedding(movie)
                if emb is not None:
                    result[movie['tmdb_id']] = emb
                    ItemEmbedding.objects.update_or_create(
                        tmdb_id=movie['tmdb_id'],
                        media_type='movie',
                        defaults={
                            'embedding': emb,
                            'embedding_version': 'v2_tfidf',
                        }
                    )

        return result

    def _generate_tfidf_embedding(self, movie_data: dict) -> Optional[List[float]]:
        from .embedding_service import semantic_embedding_service

        title = movie_data.get('title', '')
        overview = movie_data.get('overview', '')
        genres = movie_data.get('genres', [])
        if isinstance(genres, list):
            genre_names = []
            for g in genres:
                if isinstance(g, dict):
                    genre_names.append(g.get('name', ''))
                elif isinstance(g, str):
                    genre_names.append(g)
            genres_str = ' '.join(genre_names)
        else:
            genres_str = str(genres)

        text = f"{title} {title} {overview} {genres_str}"
        if not text.strip():
            return None

        try:
            items = [{'title': title, 'overview': f"{overview} {genres_str}", 'id': movie_data.get('tmdb_id', 0)}]
            embeddings = semantic_embedding_service.get_or_create_embeddings(items)
            if embeddings is not None and embeddings.shape[0] > 0:
                if hasattr(embeddings, 'toarray'):
                    return embeddings.toarray()[0].tolist()
                return embeddings[0].tolist()
        except Exception:
            pass
        return None

    def get_user_embedding(self, user) -> Optional[List[float]]:
        from movies.models import UserEmbedding

        try:
            ue = UserEmbedding.objects.get(user=user)
            return ue.embedding
        except UserEmbedding.DoesNotExist:
            return self.build_user_embedding(user)

    def compute_user_item_similarity(self, user_embedding: List[float],
                                      item_embedding: List[float]) -> float:
        if not user_embedding or not item_embedding:
            return 0.0
        u = np.array(user_embedding)
        i = np.array(item_embedding)
        if u.shape != i.shape:
            return 0.0
        dot = np.dot(u, i)
        nu = np.linalg.norm(u)
        ni = np.linalg.norm(i)
        if nu == 0 or ni == 0:
            return 0.0
        return float(dot / (nu * ni))


embedding_manager = EmbeddingManager()
