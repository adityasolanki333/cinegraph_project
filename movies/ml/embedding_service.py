"""
Semantic Embedding Service for CineGraph
Provides TF-IDF based text embeddings for movies and TV shows
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass
import hashlib


@dataclass
class EmbeddingResult:
    tmdb_id: int
    media_type: str
    embedding: np.ndarray
    text_hash: str


class SemanticEmbeddingService:
    """
    Service for creating and managing semantic embeddings using TF-IDF
    Provides methods for encoding queries and computing similarity scores
    """
    
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
    
    def _create_text_hash(self, text: str) -> str:
        """Create a hash for caching purposes"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]
    
    def _extract_text(self, item: Dict[str, Any]) -> str:
        """Extract searchable text from a TMDB item"""
        title = item.get('title') or item.get('name') or ''
        overview = item.get('overview') or ''
        combined = f"{title} {title} {overview}"
        return combined.strip()
    
    def fit_corpus(self, items: List[Dict[str, Any]]) -> None:
        """
        Fit the TF-IDF vectorizer on a corpus of items
        
        Args:
            items: List of TMDB result items with title/name and overview
        """
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
            self.corpus_embeddings = self.vectorizer.fit_transform(self.corpus_texts)
            self.is_fitted = True
    
    def encode_query(self, text: str) -> np.ndarray:
        """
        Encode a search query into an embedding vector
        
        Args:
            text: The search query text
            
        Returns:
            numpy array representing the query embedding
        """
        if not self.is_fitted:
            return np.array([])
        
        query_embedding = self.vectorizer.transform([text])
        return query_embedding
    
    def compute_similarity(self, query_embedding: np.ndarray, 
                          item_embeddings: np.ndarray) -> np.ndarray:
        """
        Compute cosine similarity between query and item embeddings
        
        Args:
            query_embedding: The query embedding vector
            item_embeddings: Matrix of item embeddings
            
        Returns:
            numpy array of similarity scores
        """
        if query_embedding.size == 0 or item_embeddings.size == 0:
            return np.array([])
        
        similarities = cosine_similarity(query_embedding, item_embeddings)
        return similarities.flatten()
    
    def get_or_create_embeddings(self, items_list: List[Dict[str, Any]]) -> np.ndarray:
        """
        Get or create embeddings for a list of TMDB items
        Uses caching to avoid recomputation
        
        Args:
            items_list: List of TMDB result items
            
        Returns:
            numpy matrix of embeddings (one row per item)
        """
        if not items_list:
            return np.array([])
        
        texts = []
        cache_keys = []
        cached_results = []
        uncached_indices = []
        
        for idx, item in enumerate(items_list):
            text = self._extract_text(item)
            text_hash = self._create_text_hash(text)
            cache_key = f"{item.get('id', idx)}_{text_hash}"
            cache_keys.append(cache_key)
            texts.append(text)
            
            if cache_key in self.embedding_cache:
                cached_results.append((idx, self.embedding_cache[cache_key].embedding))
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
                               top_k: Optional[int] = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search items and return them ranked by similarity to query
        
        Args:
            query: The search query
            items: List of items to search through
            top_k: Optional limit on number of results
            
        Returns:
            List of (item, similarity_score) tuples sorted by similarity
        """
        if not items or not query:
            return [(item, 0.0) for item in items]
        
        item_embeddings = self.get_or_create_embeddings(items)
        
        if not self.is_fitted:
            return [(item, 0.0) for item in items]
        
        query_embedding = self.encode_query(query)
        
        if query_embedding.size == 0:
            return [(item, 0.0) for item in items]
        
        similarities = self.compute_similarity(query_embedding, item_embeddings)
        
        results = list(zip(items, similarities.tolist()))
        results.sort(key=lambda x: x[1], reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        return results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the embedding cache"""
        return {
            'cache_size': len(self.embedding_cache),
            'corpus_size': len(self.corpus_texts),
            'is_fitted': self.is_fitted,
            'vocabulary_size': len(self.vectorizer.vocabulary_) if self.is_fitted else 0
        }
    
    def clear_cache(self) -> None:
        """Clear the embedding cache"""
        self.embedding_cache.clear()
        self.corpus_texts = []
        self.corpus_ids = []
        self.is_fitted = False
        self.corpus_embeddings = None


semantic_embedding_service = SemanticEmbeddingService()
