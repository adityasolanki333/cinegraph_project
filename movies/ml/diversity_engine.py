"""
Diversity Engine

Advanced diversity algorithms to prevent filter bubbles and ensure serendipity:
- Maximal Marginal Relevance (MMR)
- Determinantal Point Processes (DPP)
- Genre/Category balancing
- Epsilon-greedy exploration
- Serendipity injection
"""

import numpy as np
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass
import random
import math


@dataclass
class DiversityCandidate:
    id: str
    tmdb_id: int
    media_type: str
    score: float
    genres: List[str]
    embeddings: Optional[List[float]] = None
    metadata: Optional[Dict] = None


@dataclass
class DiversityConfig:
    lambda_param: float = 0.7  # MMR balance: 0 = max diversity, 1 = max relevance
    epsilon_exploration: float = 0.1  # Exploration rate (0-1)
    max_consecutive_same_genre: int = 3
    serendipity_rate: float = 0.15  # Percentage of surprising recommendations
    diversity_metric: str = 'mmr'  # 'mmr', 'dpp', 'hybrid'


@dataclass
class DiversityMetrics:
    intra_diversity: float  # Average dissimilarity within results
    genre_balance: float    # Shannon entropy of genre distribution
    serendipity_score: float  # % of unexpected recommendations
    exploration_rate: float  # % from exploration vs exploitation
    coverage_score: float   # % of unique genres/categories covered


class MMRDiversifier:
    """
    Maximal Marginal Relevance (MMR) Implementation
    Balances relevance and diversity iteratively
    """
    
    def apply_mmr(self, candidates: List[DiversityCandidate], 
                  limit: int, lambda_param: float = 0.7) -> List[DiversityCandidate]:
        """Apply MMR algorithm to select diverse items"""
        if len(candidates) == 0:
            return []
        if len(candidates) <= limit:
            return candidates
        
        selected = []
        remaining = candidates.copy()
        
        # Select first item (highest relevance)
        selected.append(remaining.pop(0))
        
        # Iteratively select items maximizing MMR score
        while len(selected) < limit and len(remaining) > 0:
            best_mmr_score = float('-inf')
            best_index = 0
            
            for i, candidate in enumerate(remaining):
                # Calculate max similarity to already selected items
                max_similarity = max(
                    self._calculate_similarity(candidate, s) for s in selected
                )
                
                # MMR score: λ × relevance - (1-λ) × maxSimilarity
                mmr_score = lambda_param * candidate.score - (1 - lambda_param) * max_similarity
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_index = i
            
            selected.append(remaining.pop(best_index))
        
        return selected
    
    def _calculate_similarity(self, a: DiversityCandidate, b: DiversityCandidate) -> float:
        """Calculate similarity between two candidates using embeddings or genre overlap"""
        # If embeddings are available, use cosine similarity
        if a.embeddings and b.embeddings:
            return self._cosine_similarity(a.embeddings, b.embeddings)
        
        # Fallback to genre-based similarity (Jaccard)
        a_genres = set(a.genres)
        b_genres = set(b.genres)
        
        if len(a_genres) == 0 and len(b_genres) == 0:
            return 0.0
        
        intersection = len(a_genres & b_genres)
        union = len(a_genres | b_genres)
        
        return intersection / union if union > 0 else 0.0
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity for embeddings"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        
        dot_product = np.dot(a_arr, b_arr)
        norm_a = np.linalg.norm(a_arr)
        norm_b = np.linalg.norm(b_arr)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)


class DPPDiversifier:
    """
    Determinantal Point Processes (DPP) Implementation
    Ensures diverse sets using kernel matrix determinants
    """
    
    def apply_dpp(self, candidates: List[DiversityCandidate], 
                  limit: int) -> List[DiversityCandidate]:
        """Apply greedy DPP algorithm for maximum diversity"""
        if len(candidates) == 0:
            return []
        if len(candidates) <= limit:
            return candidates
        
        # Limit for computational efficiency
        n = min(len(candidates), 50)
        candidates_subset = candidates[:n]
        
        # Build kernel matrix
        kernel_matrix = self._build_kernel_matrix(candidates_subset)
        
        # Greedy DPP: iteratively select items maximizing determinant
        selected = []
        selected_indices = []
        
        for _ in range(min(limit, n)):
            best_det = float('-inf')
            best_index = 0
            
            for j in range(n):
                if j in selected_indices:
                    continue
                
                test_indices = selected_indices + [j]
                det = self._calculate_submatrix_score(kernel_matrix, test_indices)
                
                if det > best_det:
                    best_det = det
                    best_index = j
            
            selected_indices.append(best_index)
            selected.append(candidates_subset[best_index])
        
        return selected
    
    def _build_kernel_matrix(self, candidates: List[DiversityCandidate]) -> np.ndarray:
        """Build kernel matrix from candidates"""
        n = len(candidates)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = candidates[i].score  # Quality on diagonal
                else:
                    # Similarity between items (scaled by quality)
                    sim = self._genre_similarity(candidates[i], candidates[j])
                    matrix[i][j] = np.sqrt(candidates[i].score * candidates[j].score) * (1 - sim)
        
        return matrix
    
    def _calculate_submatrix_score(self, matrix: np.ndarray, indices: List[int]) -> float:
        """Calculate DPP diversity score using log-determinant of the kernel submatrix.
        Returns values in log-space for consistent comparison across subset sizes."""
        if len(indices) == 0:
            return 0.0
        if len(indices) == 1:
            val = matrix[indices[0]][indices[0]]
            return math.log(max(val, 1e-12))
        
        sub_matrix = matrix[np.ix_(indices, indices)]
        
        sign, logdet = np.linalg.slogdet(sub_matrix)
        if sign <= 0 or not np.isfinite(logdet):
            sub_matrix = sub_matrix + np.eye(len(indices)) * 1e-6
            sign, logdet = np.linalg.slogdet(sub_matrix)
            if sign <= 0 or not np.isfinite(logdet):
                return -1e6
        
        return logdet
    
    def _genre_similarity(self, a: DiversityCandidate, b: DiversityCandidate) -> float:
        """Genre-based similarity (Jaccard)"""
        a_genres = set(a.genres)
        b_genres = set(b.genres)
        
        if len(a_genres) == 0 and len(b_genres) == 0:
            return 0.0
        
        intersection = len(a_genres & b_genres)
        union = len(a_genres | b_genres)
        
        return intersection / union if union > 0 else 0.0


class GenreBalancer:
    """
    Genre Balancer
    Prevents filter bubbles by limiting consecutive same-genre recommendations
    """
    
    def apply_genre_balancing(self, items: List[DiversityCandidate], 
                              max_consecutive: int = 3) -> List[DiversityCandidate]:
        """Apply genre balancing constraints"""
        result = []
        genre_count: Dict[str, int] = {}
        genre_last_position: Dict[str, int] = {}
        
        for i, item in enumerate(items):
            primary_genre = item.genres[0] if item.genres else 'unknown'
            
            last_pos = genre_last_position.get(primary_genre, -1)
            consecutive_count = (genre_count.get(primary_genre, 0) + 1) if last_pos == i - 1 else 1
            
            # Apply penalty if too many consecutive same genre
            if consecutive_count > max_consecutive:
                item.score *= 0.7  # 30% penalty
            
            result.append(item)
            genre_count[primary_genre] = consecutive_count
            genre_last_position[primary_genre] = i
        
        # Re-sort after penalties
        return sorted(result, key=lambda x: x.score, reverse=True)
    
    def calculate_genre_diversity(self, items: List[DiversityCandidate]) -> float:
        """Calculate genre diversity (Shannon entropy)"""
        genre_counts: Dict[str, int] = {}
        
        for item in items:
            for genre in item.genres:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        total = len(items)
        if total == 0:
            return 0.0
        
        entropy = 0.0
        for count in genre_counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        return entropy


class EpsilonGreedyExplorer:
    """
    Epsilon-Greedy Explorer
    Balances exploitation (best items) with exploration (random items)
    """
    
    def apply_exploration(self, items: List[DiversityCandidate], 
                          epsilon: float = 0.1) -> List[DiversityCandidate]:
        """Apply epsilon-greedy exploration"""
        exploration_count = int(len(items) * epsilon)
        
        if exploration_count == 0:
            return items
        
        # Split into exploitation and exploration
        exploitation_items = items[:len(items) - exploration_count]
        
        # Select random exploration items from lower ranks
        exploration_pool = items[int(len(items) * 0.3):]
        random.shuffle(exploration_pool)
        exploration_items = exploration_pool[:exploration_count]
        
        # Interleave exploration items
        result = []
        exploration_interval = len(exploitation_items) // exploration_count if exploration_count > 0 else len(exploitation_items)
        
        exploration_index = 0
        for i, item in enumerate(exploitation_items):
            result.append(item)
            
            if exploration_interval > 0 and (i + 1) % exploration_interval == 0 and exploration_index < len(exploration_items):
                result.append(exploration_items[exploration_index])
                exploration_index += 1
        
        # Add remaining exploration items
        while exploration_index < len(exploration_items):
            result.append(exploration_items[exploration_index])
            exploration_index += 1
        
        return result


class SerendipityInjector:
    """
    Serendipity Injector
    Adds surprising, out-of-comfort-zone recommendations
    """
    
    def inject_serendipity(self, items: List[DiversityCandidate], 
                           user_genre_preferences: List[str],
                           serendipity_rate: float = 0.15) -> List[DiversityCandidate]:
        """Inject serendipitous recommendations"""
        serendipity_count = int(len(items) * serendipity_rate)
        
        if serendipity_count == 0:
            return items
        
        user_genre_set = set(user_genre_preferences)
        
        # Find items with low genre overlap (surprising)
        serendipitous_candidates = [
            item for item in items
            if len([g for g in item.genres if g in user_genre_set]) <= 1
        ]
        
        # Select top serendipitous items by score
        serendipity_items = sorted(
            serendipitous_candidates, 
            key=lambda x: x.score, 
            reverse=True
        )[:serendipity_count]
        
        # Remove from main list and add back strategically
        main_items = [item for item in items if item not in serendipity_items]
        
        # Interleave serendipity items
        result = []
        interval = len(main_items) // serendipity_count if serendipity_count > 0 else len(main_items)
        
        serendipity_index = 0
        for i, item in enumerate(main_items):
            result.append(item)
            
            if interval > 0 and (i + 1) % interval == 0 and serendipity_index < len(serendipity_items):
                result.append(serendipity_items[serendipity_index])
                serendipity_index += 1
        
        return result


class DiversityEngine:
    """
    Main Diversity Engine
    Orchestrates all diversity algorithms
    """
    
    def __init__(self):
        self.mmr = MMRDiversifier()
        self.dpp = DPPDiversifier()
        self.genre_balancer = GenreBalancer()
        self.explorer = EpsilonGreedyExplorer()
        self.serendipity = SerendipityInjector()
    
    def apply_diversity(self, candidates: List[DiversityCandidate], 
                        config: DiversityConfig,
                        user_genre_preferences: Optional[List[str]] = None) -> List[DiversityCandidate]:
        """Apply comprehensive diversity optimization"""
        if user_genre_preferences is None:
            user_genre_preferences = []
        
        results = candidates.copy()
        
        # Step 1: Apply primary diversity algorithm
        if config.diversity_metric == 'mmr':
            results = self.mmr.apply_mmr(results, len(results), config.lambda_param)
        elif config.diversity_metric == 'dpp':
            results = self.dpp.apply_dpp(results, len(results))
        else:
            # Hybrid: Apply both
            results = self.mmr.apply_mmr(results, len(results), config.lambda_param)
            results = self.dpp.apply_dpp(results, min(len(results), 30))
        
        # Step 2: Genre balancing
        results = self.genre_balancer.apply_genre_balancing(
            results, 
            config.max_consecutive_same_genre
        )
        
        # Step 3: Exploration
        results = self.explorer.apply_exploration(results, config.epsilon_exploration)
        
        # Step 4: Serendipity injection
        if user_genre_preferences:
            results = self.serendipity.inject_serendipity(
                results, 
                user_genre_preferences, 
                config.serendipity_rate
            )
        
        return results
    
    def calculate_metrics(self, items: List[DiversityCandidate], 
                         user_genre_preferences: List[str]) -> DiversityMetrics:
        """Calculate diversity metrics for monitoring"""
        # Intra-diversity: average pairwise dissimilarity
        total_dissimilarity = 0.0
        pair_count = 0
        
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                sim = self._calculate_genre_similarity(items[i], items[j])
                total_dissimilarity += (1 - sim)
                pair_count += 1
        
        intra_diversity = total_dissimilarity / pair_count if pair_count > 0 else 0
        
        # Genre balance (Shannon entropy)
        genre_balance = self.genre_balancer.calculate_genre_diversity(items)
        
        # Serendipity score: % of items with no user genre overlap
        user_genre_set = set(user_genre_preferences)
        serendipitous_count = sum(
            1 for item in items
            if all(g not in user_genre_set for g in item.genres)
        )
        serendipity_score = serendipitous_count / len(items) if items else 0
        
        # Coverage score: % of unique genres
        all_genres = set()
        for item in items:
            all_genres.update(item.genres)
        coverage_score = len(all_genres) / max(len(user_genre_preferences), 1)
        
        return DiversityMetrics(
            intra_diversity=intra_diversity,
            genre_balance=genre_balance,
            serendipity_score=serendipity_score,
            exploration_rate=0.1,  # From config
            coverage_score=min(coverage_score, 1.0)
        )
    
    def _calculate_genre_similarity(self, a: DiversityCandidate, b: DiversityCandidate) -> float:
        """Genre similarity helper"""
        a_genres = set(a.genres)
        b_genres = set(b.genres)
        
        if len(a_genres) == 0 and len(b_genres) == 0:
            return 0.0
        
        intersection = len(a_genres & b_genres)
        union = len(a_genres | b_genres)
        
        return intersection / union if union > 0 else 0.0


# Export singleton
diversity_engine = DiversityEngine()
