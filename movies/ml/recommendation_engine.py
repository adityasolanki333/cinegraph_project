"""
Python ML Recommendation Engine
Provides collaborative filtering and content-based recommendations using scikit-learn
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
from django.db.models import Avg, Count
from django.contrib.auth.models import User


class RecommendationEngine:
    """
    Hybrid recommendation engine combining:
    - Collaborative filtering (user-item interactions)
    - Content-based filtering (genre/metadata similarity)
    """
    
    def __init__(self):
        self.user_item_matrix = None
        self.item_features = None
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None
        
    def build_user_item_matrix(self, ratings_data):
        """
        Build user-item interaction matrix from ratings data
        
        Args:
            ratings_data: List of dicts with user_id, tmdb_id, rating
        """
        from movies.models import UserReview
        
        reviews = UserReview.objects.all().values('user_id', 'tmdb_id', 'rating')  # type: ignore[attr-defined]
        
        user_ids = set()
        item_ids = set()
        ratings = defaultdict(dict)
        
        for review in reviews:
            user_id = review['user_id']
            item_id = review['tmdb_id']
            rating = review['rating']
            
            user_ids.add(user_id)
            item_ids.add(item_id)
            ratings[user_id][item_id] = rating
        
        self.user_id_to_idx = {uid: idx for idx, uid in enumerate(sorted(user_ids))}
        self.item_id_to_idx = {iid: idx for idx, iid in enumerate(sorted(item_ids))}
        self.idx_to_user_id = {idx: uid for uid, idx in self.user_id_to_idx.items()}
        self.idx_to_item_id = {idx: iid for iid, idx in self.item_id_to_idx.items()}
        
        n_users = len(user_ids)
        n_items = len(item_ids)
        
        self.user_item_matrix = np.zeros((n_users, n_items))
        
        for user_id, items in ratings.items():
            if user_id in self.user_id_to_idx:
                user_idx = self.user_id_to_idx[user_id]
                for item_id, rating in items.items():
                    if item_id in self.item_id_to_idx:
                        item_idx = self.item_id_to_idx[item_id]
                        self.user_item_matrix[user_idx, item_idx] = rating
        
        return self.user_item_matrix
    
    def compute_user_similarity(self):
        """Compute user-user similarity matrix using cosine similarity"""
        if self.user_item_matrix is None:
            self.build_user_item_matrix(None)
        
        if self.user_item_matrix is None or self.user_item_matrix.shape[0] < 2:
            return np.array([[1.0]])
        
        self.user_similarity_matrix = cosine_similarity(self.user_item_matrix)
        return self.user_similarity_matrix
    
    def compute_item_similarity(self):
        """Compute item-item similarity matrix using cosine similarity"""
        if self.user_item_matrix is None:
            self.build_user_item_matrix(None)
        
        if self.user_item_matrix is None or self.user_item_matrix.shape[1] < 2:
            return np.array([[1.0]])
        
        self.item_similarity_matrix = cosine_similarity(self.user_item_matrix.T)
        return self.item_similarity_matrix
    
    def get_collaborative_recommendations(self, user_id, n_recommendations=20):
        """
        Get recommendations using user-based collaborative filtering
        
        Args:
            user_id: The user to get recommendations for
            n_recommendations: Number of recommendations to return
            
        Returns:
            List of (tmdb_id, predicted_rating) tuples
        """
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
        
        user_ratings = self.user_item_matrix[user_idx]
        unrated_items = np.where(user_ratings == 0)[0]
        
        predictions = []
        for item_idx in unrated_items:
            numerator = 0
            denominator = 0
            
            for sim_user_idx in similar_user_indices:
                sim = similarities[sim_user_idx]
                rating = self.user_item_matrix[sim_user_idx, item_idx]
                
                if rating > 0 and sim > 0:
                    numerator += sim * rating
                    denominator += abs(sim)
            
            if denominator > 0:
                predicted_rating = numerator / denominator
                item_id = self.idx_to_item_id[item_idx]
                predictions.append((item_id, predicted_rating))
        
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions[:n_recommendations]
    
    def get_similar_items(self, tmdb_id, n_similar=10):
        """
        Get similar items using item-based collaborative filtering
        
        Args:
            tmdb_id: The item to find similar items for
            n_similar: Number of similar items to return
            
        Returns:
            List of (tmdb_id, similarity_score) tuples
        """
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
        self.use_pinecone = self.pinecone_service.is_initialized()
        
    def build_content_features(self, content_data):
        """
        Build TF-IDF feature matrix from content metadata (Fallback mode)
        """
        if self.use_pinecone:
            return None # Pinecone doesn't need this rebuild
            
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
        """
        Get similar content based on Semantic (Chroma) or TF-IDF similarity
        """
        if self.use_pinecone:
            try:
                results = self.pinecone_service.get_nearest_neighbors(tmdb_id, k=n_similar)
                if results:
                    similar_items = []
                    for item in results:
                        # Extract the id and similarity score from Pinecone dictionary
                        similar_items.append((int(item['id']), float(item['similarity'])))
                    return similar_items
            except Exception as e:
                print(f"PineconeService query failed: {e}")
                
        # Fallback to TF-IDF
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
    """
    
    def __init__(self, collab_weight=0.6, content_weight=0.4):
        self.collaborative = RecommendationEngine()
        self.content_based = ContentBasedRecommender()
        self.collab_weight = collab_weight
        self.content_weight = content_weight
    
    def get_recommendations(self, user_id, n_recommendations=20):
        """
        Get hybrid recommendations combining collaborative and content-based
        
        Args:
            user_id: User to get recommendations for
            n_recommendations: Number of recommendations
            
        Returns:
            List of recommendation dicts with tmdb_id, score, type
        """
        # 1. Get Collaborative Recommendations
        collab_recs = self.collaborative.get_collaborative_recommendations(
            user_id, 
            n_recommendations * 2
        )
        
        recommendations = {}
        
        # Add Collaborative candidates
        for tmdb_id, score in collab_recs:
            recommendations[tmdb_id] = {
                'tmdb_id': tmdb_id,
                'score': score * self.collab_weight,
                'collaborative_score': score,
                'content_score': 0,
                'type': 'collaborative',
                'reason': 'Similar to users with your taste'
            }

        # 2. Get Content-Based Recommendations (from User History)
        # We need to access the user's history from the collaborative engine's matrix or DB
        from movies.models import UserReview
        user_history = UserReview.objects.filter(user_id=user_id, rating__gte=4.0).order_by('-created_at')[:5]
        
        seen_movies = set(UserReview.objects.filter(user_id=user_id).values_list('tmdb_id', flat=True))
        
        for review in user_history:
            similar_items = self.content_based.get_similar_content(review.tmdb_id, n_similar=5)
            
            for tmdb_id, similarity in similar_items:
                if tmdb_id in seen_movies:
                    continue
                    
                weighted_score = similarity * self.content_weight
                
                if tmdb_id in recommendations:
                    # Boost existing recommendation
                    recommendations[tmdb_id]['score'] += weighted_score
                    recommendations[tmdb_id]['content_score'] = similarity
                    recommendations[tmdb_id]['type'] = 'hybrid'
                    recommendations[tmdb_id]['reason'] = f"Because you liked {review.title}"
                else:
                    # Add new recommendation
                    recommendations[tmdb_id] = {
                        'tmdb_id': tmdb_id,
                        'score': weighted_score,
                        'collaborative_score': 0,
                        'content_score': similarity,
                        'type': 'content-based',
                        'reason': f"Because you liked {review.title}"
                    }
        
        # 3. Sort and Return
        sorted_recs = sorted(
            recommendations.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        return sorted_recs[:n_recommendations]


recommendation_engine = RecommendationEngine()
content_recommender = ContentBasedRecommender()
hybrid_recommender = HybridRecommender()
