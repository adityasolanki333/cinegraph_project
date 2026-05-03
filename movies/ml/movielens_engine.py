"""
MovieLens-powered item-item collaborative filtering engine.

Downloads ml-latest-small on first use, builds a sparse item-item cosine
similarity matrix (ratings.csv + links.csv → TMDB IDs), caches top-K
neighbours per movie to disk, and exposes fast lookup helpers.

No fake users are inserted into the application database.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity

ML_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'ml-latest-small')
ML_DATA_DIR = os.path.normpath(ML_DATA_DIR)
SIMILARITY_CACHE = os.path.join(ML_DATA_DIR, 'similarity_cache.json')
ML_DOWNLOAD_URL = 'https://files.grouplens.org/datasets/movielens/ml-latest-small.zip'
TOP_K = 25  # how many similar movies to keep per movie

logger = logging.getLogger(__name__)


def _download_movielens():
    """Download and unzip the MovieLens small dataset."""
    import urllib.request
    logger.info('MovieLens: downloading ml-latest-small.zip …')
    os.makedirs(os.path.dirname(ML_DATA_DIR), exist_ok=True)
    zip_path = ML_DATA_DIR + '.zip'
    urllib.request.urlretrieve(ML_DOWNLOAD_URL, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(os.path.dirname(ML_DATA_DIR))
    os.remove(zip_path)
    logger.info('MovieLens: download complete.')


def _build_similarity_cache():
    """
    Build item-item cosine similarity from ratings and cache top-K neighbours.
    Returns the cache dict: {tmdb_id_str: [(tmdb_id, score), ...]}
    """
    ratings_file = os.path.join(ML_DATA_DIR, 'ratings.csv')
    links_file = os.path.join(ML_DATA_DIR, 'links.csv')

    logger.info('MovieLens: loading links …')
    movie_to_tmdb: Dict[str, int] = {}
    with open(links_file, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            tmdb_raw = row.get('tmdbId', '').strip()
            if tmdb_raw:
                try:
                    movie_to_tmdb[row['movieId']] = int(float(tmdb_raw))
                except ValueError:
                    pass
    logger.info('MovieLens: %d movieId→tmdbId mappings', len(movie_to_tmdb))

    logger.info('MovieLens: loading ratings …')
    user_ids: Dict[str, int] = {}
    item_ids: Dict[str, int] = {}
    rows, cols, data = [], [], []

    with open(ratings_file, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            movie_id = row['movieId']
            if movie_id not in movie_to_tmdb:
                continue
            uid = row['userId']
            rating = float(row['rating'])

            if uid not in user_ids:
                user_ids[uid] = len(user_ids)
            if movie_id not in item_ids:
                item_ids[movie_id] = len(item_ids)

            rows.append(user_ids[uid])
            cols.append(item_ids[movie_id])
            data.append(rating)

    idx_to_movie = {v: k for k, v in item_ids.items()}
    n_users = len(user_ids)
    n_items = len(item_ids)
    logger.info('MovieLens: %d ratings | %d users | %d items', len(data), n_users, n_items)

    mat = csr_matrix((data, (rows, cols)), shape=(n_users, n_items), dtype=np.float32)
    item_mat = mat.T  # shape: (n_items, n_users)

    logger.info('MovieLens: computing item-item cosine similarity (batch) …')
    BATCH = 500
    cache: Dict[str, List] = {}

    for start in range(0, n_items, BATCH):
        end = min(start + BATCH, n_items)
        batch = item_mat[start:end]
        sims = cosine_similarity(batch, item_mat)  # (batch_size, n_items)

        for local_i, global_i in enumerate(range(start, end)):
            movie_id_i = idx_to_movie[global_i]
            tmdb_i = movie_to_tmdb[movie_id_i]

            sim_row = sims[local_i]
            sim_row[global_i] = 0.0  # exclude self
            top_indices = np.argpartition(sim_row, -TOP_K)[-TOP_K:]
            top_indices = top_indices[np.argsort(sim_row[top_indices])[::-1]]

            neighbours = []
            for idx in top_indices:
                score = float(sim_row[idx])
                if score <= 0:
                    continue
                movie_id_j = idx_to_movie[idx]
                tmdb_j = movie_to_tmdb[movie_id_j]
                neighbours.append([tmdb_j, round(score, 4)])

            if neighbours:
                cache[str(tmdb_i)] = neighbours

        if (start // BATCH) % 5 == 0:
            logger.info('  … processed %d/%d items', end, n_items)

    logger.info('MovieLens: similarity cache built (%d entries)', len(cache))
    with open(SIMILARITY_CACHE, 'w') as f:
        json.dump(cache, f)
    logger.info('MovieLens: cache saved to %s', SIMILARITY_CACHE)
    return cache


class MovieLensEngine:
    """
    Lazy-loading singleton for MovieLens item-item similarity.
    Call MovieLensEngine() anywhere — it auto-downloads & builds on first use.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: Dict[str, List] = {}
            cls._instance._loaded = False
            cls._instance._failed = False
            cls._instance._loading_in_progress = False
        return cls._instance

    def _ensure_loaded(self):
        if self._loaded or self._failed or self._loading_in_progress:
            return
            
        self._loading_in_progress = True

        import threading
        def _load_bg():
            try:
                if not os.path.exists(os.path.join(ML_DATA_DIR, 'ratings.csv')):
                    _download_movielens()

                if os.path.exists(SIMILARITY_CACHE):
                    with open(SIMILARITY_CACHE) as f:
                        self._cache = json.load(f)
                    logger.info('MovieLens: loaded similarity cache (%d movies)', len(self._cache))
                else:
                    self._cache = _build_similarity_cache()

                self._loaded = True
            except Exception as e:
                logger.error('MovieLens engine failed to load: %s', e)
                self._failed = True
            finally:
                self._loading_in_progress = False
                
        threading.Thread(target=_load_bg, daemon=True).start()

    def is_ready(self) -> bool:
        self._ensure_loaded()
        return self._loaded and bool(self._cache)

    def get_similar(self, tmdb_id: int, k: int = 20) -> List[Tuple[int, float]]:
        """Return top-k similar TMDB IDs with similarity scores."""
        if not self._loaded:
            return []
        neighbours = self._cache.get(str(tmdb_id), [])
        return [(int(n[0]), float(n[1])) for n in neighbours[:k]]

    def get_recommendations(
        self,
        liked_tmdb_ids: List[int],
        excluded_tmdb_ids: set,
        k: int = 40,
    ) -> List[Tuple[int, float]]:
        """
        Aggregate similar items across all liked movies.
        Scores are weighted by position in liked list (first = most recently liked).
        Returns list of (tmdb_id, score) sorted by score desc.
        """
        self._ensure_loaded()
        if not liked_tmdb_ids:
            return []

        scores: Dict[int, float] = defaultdict(float)
        n = len(liked_tmdb_ids)

        for rank, seed_id in enumerate(liked_tmdb_ids):
            weight = 1.0 - (rank / (n + 1))  # higher weight for more recent/higher-rated
            for tmdb_id, sim in self.get_similar(seed_id, k=20):
                if tmdb_id not in excluded_tmdb_ids and tmdb_id != seed_id:
                    scores[tmdb_id] += sim * weight

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:k]

    def rebuild(self):
        """Force rebuild the similarity cache (e.g. after re-download)."""
        self._loaded = False
        self._failed = False
        self._cache = {}
        if os.path.exists(SIMILARITY_CACHE):
            os.remove(SIMILARITY_CACHE)
        self._ensure_loaded()


movielens_engine = MovieLensEngine()
