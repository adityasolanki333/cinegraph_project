"""
Python ML Recommendation Engine
Provides collaborative filtering and content-based recommendations using scikit-learn
With temporal decay, mean-centering, and implicit signal support.
"""
from __future__ import annotations

import logging
import math
import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
from django.db.models import Avg, Count
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)

DECAY_HALF_LIFE_DAYS = 180


def _time_decay_factor(created_at, half_life=DECAY_HALF_LIFE_DAYS):
    if created_at is None:
        return 0.5
    now = timezone.now()
    if timezone.is_naive(created_at):
        from django.utils.timezone import make_aware
        created_at = make_aware(created_at)
    age_days = (now - created_at).total_seconds() / 86400.0
    return math.exp(-0.693 * age_days / half_life)


class RecommendationEngine:
    """
    Hybrid recommendation engine combining:
    - Collaborative filtering (user-item interactions) with temporal decay + mean-centering
    - Content-based filtering (genre/metadata similarity)
    - Implicit signal integration
    """
    
    def __init__(self):
        self.user_item_matrix = None
        self.item_features = None
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None
        self.user_means = None
        self._last_build_count = 0
        
    def build_user_item_matrix(self, ratings_data):
        from movies.models import UserReview
        
        reviews = UserReview.objects.all().values('user_id', 'tmdb_id', 'rating', 'created_at')
        
        user_ids = set()
        item_ids = set()
        ratings = defaultdict(dict)
        
        for review in reviews:
            user_id = review['user_id']
            item_id = review['tmdb_id']
            rating = review['rating']
            decay = _time_decay_factor(review['created_at'])
            
            user_ids.add(user_id)
            item_ids.add(item_id)
            ratings[user_id][item_id] = rating * decay
        
        if not user_ids or not item_ids:
            return None

        self.user_id_to_idx = {uid: idx for idx, uid in enumerate(sorted(user_ids))}
        self.item_id_to_idx = {iid: idx for idx, iid in enumerate(sorted(item_ids))}
        self.idx_to_user_id = {idx: uid for uid, idx in self.user_id_to_idx.items()}
        self.idx_to_item_id = {idx: iid for iid, idx in self.item_id_to_idx.items()}
        
        n_users = len(user_ids)
        n_items = len(item_ids)
        
        mat = lil_matrix((n_users, n_items), dtype=np.float64)
        
        for user_id, items in ratings.items():
            if user_id in self.user_id_to_idx:
                user_idx = self.user_id_to_idx[user_id]
                for item_id, rating in items.items():
                    if item_id in self.item_id_to_idx:
                        item_idx = self.item_id_to_idx[item_id]
                        mat[user_idx, item_idx] = rating
        
        self.user_item_matrix = mat.tocsr()

        self.user_means = np.zeros(n_users)
        for u in range(n_users):
            row = self.user_item_matrix.getrow(u)
            data = row.data
            if len(data) > 0:
                positives = data[data > 0]
                if len(positives) > 0:
                    self.user_means[u] = positives.mean()

        self._last_build_count = len(list(reviews))
        
        return self.user_item_matrix

    def _mean_centered_matrix(self):
        if self.user_item_matrix is None:
            return None
        centered = self.user_item_matrix.copy().tolil()
        for u in range(centered.shape[0]):
            row = centered.getrowview(u)
            cols = row.rows[0]
            data = row.data[0]
            for j, idx in enumerate(cols):
                if data[j] > 0:
                    data[j] -= self.user_means[u]
        return centered.tocsr()
    
    def compute_user_similarity(self):
        if self.user_item_matrix is None:
            self.build_user_item_matrix(None)
        
        if self.user_item_matrix is None or self.user_item_matrix.shape[0] < 2:
            return np.array([[1.0]])
        
        centered = self._mean_centered_matrix()
        if centered is None:
            return np.array([[1.0]])
        self.user_similarity_matrix = cosine_similarity(centered)
        return self.user_similarity_matrix
    
    def compute_item_similarity(self):
        if self.user_item_matrix is None:
            self.build_user_item_matrix(None)
        
        if self.user_item_matrix is None or self.user_item_matrix.shape[1] < 2:
            return np.array([[1.0]])
        
        self.item_similarity_matrix = cosine_similarity(self.user_item_matrix.T)
        return self.item_similarity_matrix
    
    def get_collaborative_recommendations(self, user_id, n_recommendations=20):
        if self.user_similarity_matrix is None:
            self.compute_user_similarity()
        
        if self.user_similarity_matrix is None or self.user_item_matrix is None:
            return []
        
        if user_id not in self.user_id_to_idx:
            return []
        
        user_idx = self.user_id_to_idx[user_id]
        
        similarities = self.user_similarity_matrix[user_idx]
        
        k = min(10, len(similarities) - 1)
        if k <= 0:
            return []
        
        similar_user_indices = np.argsort(similarities)[::-1][1:k+1]
        
        user_ratings = self.user_item_matrix[user_idx].toarray().flatten()
        unrated_items = np.where(user_ratings == 0)[0]
        
        predictions = []
        for item_idx in unrated_items:
            numerator = 0
            denominator = 0
            
            for sim_user_idx in similar_user_indices:
                sim = similarities[sim_user_idx]
                rating = self.user_item_matrix[sim_user_idx, item_idx]
                
                if rating > 0 and sim > 0:
                    mean_centered = rating - self.user_means[sim_user_idx]
                    numerator += sim * mean_centered
                    denominator += abs(sim)
            
            if denominator > 0:
                predicted_rating = self.user_means[user_idx] + numerator / denominator
                item_id = self.idx_to_item_id[item_idx]
                predictions.append((item_id, predicted_rating))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions[:n_recommendations]

    def incremental_update(self, user_id, tmdb_id, rating, created_at=None):
        if self.user_item_matrix is None:
            return

        if user_id not in self.user_id_to_idx or tmdb_id not in self.item_id_to_idx:
            self.build_user_item_matrix(None)
            self.compute_user_similarity()
            return

        user_idx = self.user_id_to_idx[user_id]
        item_idx = self.item_id_to_idx[tmdb_id]
        decay = _time_decay_factor(created_at) if created_at else 1.0

        lil = self.user_item_matrix.tolil()
        lil[user_idx, item_idx] = rating * decay
        self.user_item_matrix = lil.tocsr()

        row_data = self.user_item_matrix.getrow(user_idx).data
        positives = row_data[row_data > 0]
        if len(positives) > 0:
            self.user_means[user_idx] = positives.mean()

        self.compute_user_similarity()
    
    def get_similar_items(self, tmdb_id, n_similar=10):
        if self.item_similarity_matrix is None:
            self.compute_item_similarity()
        
        if self.item_similarity_matrix is None:
            return []
        
        if tmdb_id not in self.item_id_to_idx:
            return []
        
        item_idx = self.item_id_to_idx[tmdb_id]
        
        similarities = self.item_similarity_matrix[item_idx]
        
        similar_indices = np.argsort(similarities)[::-1][1:n_similar+1]
        
        similar_items = []
        for idx in similar_indices:
            similar_item_id = self.idx_to_item_id[idx]
            similarity_score = similarities[idx]
            similar_items.append((similar_item_id, float(similarity_score)))
        
        return similar_items


class ContentBasedRecommender:
    """Content-based recommender using ChromaDB (BERT) and fallback to TF-IDF"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self.item_ids = []
        
        from .pinecone_service import pinecone_service
        self.pinecone_service = pinecone_service
        self.use_pinecone = bool(pinecone_service and self.pinecone_service.is_initialized())
        
    def build_content_features(self, content_data):
        if self.use_pinecone:
            return None
            
        self.item_ids = []
        documents = []
        
        for item in content_data:
            self.item_ids.append(item['tmdb_id'])
            genres = ' '.join(item.get('genres', []))
            overview = item.get('overview', '')
            combined = f"{genres} {overview}"
            documents.append(combined)
        
        if documents:
            self.tfidf_matrix = self.vectorizer.fit_transform(documents)
        
        return self.tfidf_matrix
    
    def get_similar_content(self, tmdb_id, n_similar=10):
        if self.use_pinecone:
            try:
                results = self.pinecone_service.get_nearest_neighbors(tmdb_id, k=n_similar)
                if results:
                    similar_items = []
                    for item in results:
                        similar_items.append((int(item['id']), float(item['similarity'])))
                    return similar_items
            except Exception as e:
                print(f"PineconeService query failed: {e}")
                
        if self.tfidf_matrix is None or tmdb_id not in self.item_ids:
            return []
        
        try:
            item_idx = self.item_ids.index(tmdb_id)
            item_vector = self.tfidf_matrix[item_idx]
            similarities = cosine_similarity(item_vector, self.tfidf_matrix).flatten()
            similar_indices = np.argsort(similarities)[::-1][1:n_similar+1]
            
            similar_items = []
            for idx in similar_indices:
                similar_item_id = self.item_ids[idx]
                similarity_score = similarities[idx]
                similar_items.append((similar_item_id, float(similarity_score)))
            return similar_items
        except ValueError:
            return []


class HybridRecommender:
    """
    Hybrid recommender combining collaborative and content-based approaches
    with per-user learned weights from the feedback loop.
    """
    
    def __init__(self, collab_weight=0.6, content_weight=0.4):
        self.collaborative = RecommendationEngine()
        self.content_based = ContentBasedRecommender()
        self.collab_weight = collab_weight
        self.content_weight = content_weight
    
    def get_recommendations(self, user_id, n_recommendations=20):
        from movies.models import UserReview

        user = None
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            pass

        collab_w = self.collab_weight
        content_w = self.content_weight

        if user:
            try:
                from .feedback_service import feedback_service
                weights = feedback_service.get_user_weights(user)
                collab_w = weights.get('collaborative', self.collab_weight)
                content_w = weights.get('content', self.content_weight)
            except Exception as e:
                logger.warning(f"Failed to load feedback weights for user_id={user_id}: {e}")

        collab_recs = self.collaborative.get_collaborative_recommendations(
            user_id, 
            n_recommendations * 2
        )
        
        recommendations = {}
        
        for tmdb_id, score in collab_recs:
            recommendations[tmdb_id] = {
                'tmdb_id': tmdb_id,
                'score': score * collab_w,
                'collaborative_score': score,
                'content_score': 0,
                'type': 'collaborative',
                'reason': 'Similar to users with your taste'
            }

        user_history = UserReview.objects.filter(user_id=user_id, rating__gte=4.0).order_by('-created_at')[:5]
        
        seen_movies = set(UserReview.objects.filter(user_id=user_id).values_list('tmdb_id', flat=True))
        
        for review in user_history:
            similar_items = self.content_based.get_similar_content(review.tmdb_id, n_similar=5)
            
            for tmdb_id, similarity in similar_items:
                if tmdb_id in seen_movies:
                    continue
                    
                weighted_score = similarity * content_w
                
                if tmdb_id in recommendations:
                    recommendations[tmdb_id]['score'] += weighted_score
                    recommendations[tmdb_id]['content_score'] = similarity
                    recommendations[tmdb_id]['type'] = 'hybrid'
                    recommendations[tmdb_id]['reason'] = f"Because you liked {review.title}"
                else:
                    recommendations[tmdb_id] = {
                        'tmdb_id': tmdb_id,
                        'score': weighted_score,
                        'collaborative_score': 0,
                        'content_score': similarity,
                        'type': 'content-based',
                        'reason': f"Because you liked {review.title}"
                    }
        
        sorted_recs = sorted(
            recommendations.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return sorted_recs[:n_recommendations]


recommendation_engine = RecommendationEngine()
content_recommender = ContentBasedRecommender()
hybrid_recommender = HybridRecommender()
