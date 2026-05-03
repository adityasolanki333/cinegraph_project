"""
Explainability Engine

Provides transparent, human-readable explanations for recommendations using:
- Feature attribution (importance scoring)
- Template-based explanations
- Visual breakdown for UI
- Gemini AI for compelling explanations (Level 3)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
import os
import logging
import hashlib
from django.core.cache import cache

from movies.ml.utils import GENRE_MAP as _SHARED_GENRE_MAP

logger = logging.getLogger(__name__)


@dataclass
class FeatureImportance:
    feature_name: str
    importance: float  # 0-1 normalized
    percentage_contribution: float  # 0-100%
    human_readable: str


@dataclass
class Explanation:
    recommendation_id: Optional[str]
    user_id: str
    tmdb_id: int
    media_type: str
    title: str
    primary_reason: str
    contributing_factors: List[FeatureImportance]
    visual_breakdown: List[Dict[str, Any]]
    confidence_score: float
    explanation_text: str


@dataclass
class ExplanationContext:
    user_id: str
    tmdb_id: int
    media_type: str
    user_ratings: List[Dict]
    user_preferences: Optional[Dict]
    item_details: Optional[Dict]
    similar_movies: List[str] = field(default_factory=list)
    collaborative_users: List[Dict] = field(default_factory=list)


class ExplainabilityEngine:
    """Engine for generating human-readable explanations for recommendations"""
    
    COLOR_PALETTE = [
        '#3b82f6',  # blue - genre match
        '#10b981',  # green - rating quality
        '#8b5cf6',  # purple - preferences match
        '#f59e0b',  # amber - similarity boost
        '#ef4444',  # red - collaborative boost
        '#ec4899',  # pink - popularity
        '#14b8a6',  # teal - recency
    ]
    
    GENRE_MAP = _SHARED_GENRE_MAP
    
    FEATURE_DISPLAY_NAMES = {
        'genre_match': 'Genre Match',
        'rating_quality': 'Quality Score',
        'preferences_match': 'Your Preferences',
        'similarity_boost': 'Similar Favorites',
        'collaborative_boost': 'Similar Users',
        'popularity_boost': 'Popularity',
        'recency_boost': 'New Releases'
    }
    
    DEFAULT_WEIGHTS = {
        'genre_match': 0.3,
        'rating_quality': 0.2,
        'preferences_match': 0.2,
        'similarity_boost': 0.15,
        'collaborative_boost': 0.15
    }
    
    def explain_recommendation(self, user_id: str, tmdb_id: int, 
                                media_type: str = 'movie',
                                recommendation_id: Optional[str] = None,
                                context: Optional[ExplanationContext] = None) -> Explanation:
        """Generate comprehensive explanation for a recommendation"""
        
        try:
            # Check cache first
            cache_key = f"explanation_{user_id}_{tmdb_id}_{media_type}"
            cached_explanation = cache.get(cache_key)
            if cached_explanation:
                # Reconstruct Explanation object from dict
                # Note: This assumes simplified serialization/deserialization logic or storing raw dicts if acceptable
                # For robust object caching, pickle is used by default in Django cache, so entire object might be returned.
                # If using JSON cache (like Redis with JSON), we might need manual reconstruction. 
                # Assuming local memory/locmem or pickle-compatible, we can return directly if it's the object.
                if isinstance(cached_explanation, Explanation):
                    return cached_explanation
            
            # Gather context if not provided
            if context is None:
                context = self._create_default_context(user_id, tmdb_id, media_type)
            
            # Handle case where item details are not found
            if not context.item_details:
                return Explanation(
                    recommendation_id=recommendation_id,
                    user_id=user_id,
                    tmdb_id=tmdb_id,
                    media_type=media_type,
                    title='Unknown Item',
                    primary_reason="Insufficient data available",
                    contributing_factors=[],
                    visual_breakdown=[],
                    confidence_score=0.1,
                    explanation_text="We don't have enough information about this item to provide a detailed explanation."
                )
            
            # Calculate feature importance
            feature_importance = self._calculate_feature_importance(context)
            
            # Generate human-readable explanation
            explanation_text = self._generate_explanation_text(context, feature_importance)
            
            # Enhancing with Gemini if possible (Level 3 Explanation)
            try:
                rec_title = context.item_details.get('title') or context.item_details.get('name', '') if context.item_details else ''
                rec_overview = context.item_details.get('overview', '') if context.item_details else ''

                if rec_title:
                    # Build rich user context for a personalized prompt
                    preferred_genres = []
                    if context.user_preferences:
                        preferred_genres = context.user_preferences.get('preferred_genres', [])

                    top_movies = context.similar_movies[:3] if context.similar_movies else []

                    gemini_text = self.generate_personalized_explanation(
                        recommended_title=rec_title,
                        recommended_overview=rec_overview,
                        preferred_genres=preferred_genres,
                        top_rated_movies=top_movies,
                        feature_reasons=[f.human_readable for f in feature_importance[:3]]
                    )
                    if gemini_text:
                        explanation_text = gemini_text
            except Exception as e:
                logger.warning(f"Gemini explanation generation failed for '{rec_title}': {e}")
            
            # Create visual breakdown
            visual_breakdown = self._create_visual_breakdown(feature_importance)
            
            # Get primary reason
            primary_reason = (
                feature_importance[0].human_readable 
                if feature_importance 
                else "This item matches your viewing preferences"
            )
            
            # Calculate confidence
            confidence_score = self._calculate_confidence(feature_importance)
            
            explanation = Explanation(
                recommendation_id=recommendation_id,
                user_id=user_id,
                tmdb_id=tmdb_id,
                media_type=media_type,
                title=context.item_details.get('title', context.item_details.get('name', 'Unknown')),
                primary_reason=primary_reason,
                contributing_factors=feature_importance,
                visual_breakdown=visual_breakdown,
                confidence_score=confidence_score,
                explanation_text=explanation_text
            )
            
            # Cache for 1 hour (3600s)
            cache.set(cache_key, explanation, 3600)
            
            return explanation
        
        except Exception as e:
            logger.error(f"Failed to generate explanation for user={user_id} tmdb_id={tmdb_id}: {e}", exc_info=True)
            return Explanation(
                recommendation_id=recommendation_id,
                user_id=user_id,
                tmdb_id=tmdb_id,
                media_type=media_type,
                title='Unknown Item',
                primary_reason="Error generating explanation",
                contributing_factors=[],
                visual_breakdown=[],
                confidence_score=0.1,
                explanation_text="We couldn't generate a detailed explanation right now. Please try again later."
            )
    
    def _create_default_context(self, user_id: str, tmdb_id: int, 
                                media_type: str) -> ExplanationContext:
        """Create a default context when none is provided"""
        return ExplanationContext(
            user_id=user_id,
            tmdb_id=tmdb_id,
            media_type=media_type,
            user_ratings=[],
            user_preferences=None,
            item_details=None,
            similar_movies=[],
            collaborative_users=[]
        )
    
    def _calculate_feature_importance(self, context: ExplanationContext) -> List[FeatureImportance]:
        """Calculate feature importance using adaptive weights and heuristics"""
        importance = []
        weights = self.DEFAULT_WEIGHTS
        
        # 1. Genre Match Importance
        genre_importance = self._calculate_genre_importance(context, weights['genre_match'])
        if genre_importance:
            importance.append(genre_importance)
        
        # 2. Rating Quality Importance
        rating_importance = self._calculate_rating_importance(context, weights['rating_quality'])
        if rating_importance:
            importance.append(rating_importance)
        
        # 3. Preferences Match Importance
        preferences_importance = self._calculate_preferences_importance(context, weights['preferences_match'])
        if preferences_importance:
            importance.append(preferences_importance)
        
        # 4. Similarity Boost Importance
        similarity_importance = self._calculate_similarity_importance(context, weights['similarity_boost'])
        if similarity_importance:
            importance.append(similarity_importance)
        
        # 5. Collaborative Importance
        collaborative_importance = self._calculate_collaborative_importance(context, weights['collaborative_boost'])
        if collaborative_importance:
            importance.append(collaborative_importance)
        
        # Normalize to sum to 100%
        return self._normalize_importance(importance)
    
    def _calculate_genre_importance(self, context: ExplanationContext, 
                                     weight: float) -> Optional[FeatureImportance]:
        """Calculate genre matching importance"""
        if not context.item_details:
            return None
        
        item_genres = context.item_details.get('genre_ids', [])
        if not item_genres:
            genres = context.item_details.get('genres', [])
            item_genres = [g.get('id') for g in genres if isinstance(g, dict)]
        
        if not item_genres:
            return None
        
        # Get user's preferred genres from preferences
        preferred_genres = []
        if context.user_preferences:
            preferred_genres = context.user_preferences.get('preferred_genres', [])
        
        # Match genres
        matched_genres = []
        for genre_id in item_genres:
            genre_name = self.GENRE_MAP.get(genre_id)
            if genre_name and genre_name in preferred_genres:
                matched_genres.append(genre_name)
        
        if not matched_genres:
            return None
        
        normalized_score = min(len(matched_genres) / len(item_genres), 1.0)
        
        # Create human-readable explanation
        if len(matched_genres) > 2:
            human_readable = f"Matches your love for {', '.join(matched_genres[:2])} and {len(matched_genres) - 2} more"
        else:
            human_readable = f"Matches your love for {', '.join(matched_genres)}"
        
        return FeatureImportance(
            feature_name='genre_match',
            importance=normalized_score * weight,
            percentage_contribution=0,  # Will be calculated in normalization
            human_readable=human_readable
        )
    
    def _calculate_rating_importance(self, context: ExplanationContext, 
                                      weight: float) -> Optional[FeatureImportance]:
        """Calculate rating quality importance"""
        if not context.item_details:
            return None
        
        item_rating = context.item_details.get('vote_average', 0)
        if item_rating == 0:
            return None
        
        # Calculate user's average rating
        if context.user_ratings:
            user_avg_rating = sum(r.get('rating', 0) for r in context.user_ratings) / len(context.user_ratings)
        else:
            user_avg_rating = 7.0
        
        rating_diff = abs(item_rating - user_avg_rating)
        normalized_score = max(0, 1 - (rating_diff / 5))
        
        if item_rating >= 8:
            human_readable = f"Highly rated by critics: {item_rating:.1f}/10"
        elif item_rating >= user_avg_rating - 0.5:
            human_readable = f"Quality matches your standards: {item_rating:.1f}/10"
        else:
            human_readable = f"Rating: {item_rating:.1f}/10"
        
        return FeatureImportance(
            feature_name='rating_quality',
            importance=normalized_score * weight,
            percentage_contribution=0,
            human_readable=human_readable
        )
    
    def _calculate_preferences_importance(self, context: ExplanationContext, 
                                           weight: float) -> Optional[FeatureImportance]:
        """Calculate preferences match importance"""
        if not context.user_preferences or not context.item_details:
            return None
        
        prefs = context.user_preferences
        factors = []
        match_score = 0.0
        
        # Check decade preference
        release_date = context.item_details.get('release_date') or context.item_details.get('first_air_date')
        preferred_decades = prefs.get('preferred_decades', [])
        
        if release_date and preferred_decades:
            try:
                year = int(release_date[:4])
                decade = f"{(year // 10) * 10}s"
                if decade in preferred_decades:
                    match_score += 0.3
                    factors.append(f"from your preferred {decade}")
            except (ValueError, IndexError):
                pass
        
        # Check language preference
        original_language = context.item_details.get('original_language')
        language_preferences = prefs.get('language_preferences', [])
        
        if original_language and language_preferences:
            if original_language in language_preferences:
                match_score += 0.3
                factors.append('in your preferred language')
        
        # Check duration preference
        runtime = context.item_details.get('runtime')
        duration_preference = prefs.get('duration_preference')
        
        if runtime and duration_preference:
            matches = (
                (duration_preference == 'short' and runtime < 100) or
                (duration_preference == 'medium' and 100 <= runtime <= 150) or
                (duration_preference == 'long' and runtime > 150)
            )
            if matches:
                match_score += 0.4
                factors.append(f"{duration_preference} duration")
        
        if not factors:
            return None
        
        return FeatureImportance(
            feature_name='preferences_match',
            importance=match_score * weight,
            percentage_contribution=0,
            human_readable=f"Matches your preferences: {', '.join(factors)}"
        )
    
    def _calculate_similarity_importance(self, context: ExplanationContext, 
                                          weight: float) -> Optional[FeatureImportance]:
        """Calculate similarity to highly-rated movies"""
        if not context.similar_movies:
            return None
        
        top_similar = context.similar_movies[:2]
        
        return FeatureImportance(
            feature_name='similarity_boost',
            importance=0.8 * weight,
            percentage_contribution=0,
            human_readable=f"Similar to {', '.join(top_similar)} which you loved"
        )
    
    def _calculate_collaborative_importance(self, context: ExplanationContext, 
                                             weight: float) -> Optional[FeatureImportance]:
        """Calculate collaborative filtering importance"""
        # Simplified - check if user has enough ratings
        has_ratings = len(context.user_ratings) >= 5
        
        if not has_ratings:
            return None
        
        return FeatureImportance(
            feature_name='collaborative_boost',
            importance=0.6 * weight,
            percentage_contribution=0,
            human_readable='Popular with users who share your taste'
        )
    
    def _normalize_importance(self, importance: List[FeatureImportance]) -> List[FeatureImportance]:
        """Normalize importance values to sum to 100%"""
        total = sum(item.importance for item in importance)
        
        if total == 0:
            return importance
        
        for item in importance:
            item.percentage_contribution = (item.importance / total) * 100
        
        return sorted(importance, key=lambda x: x.percentage_contribution, reverse=True)
    
    def _generate_explanation_text(self, context: ExplanationContext,
                                    importance: List[FeatureImportance]) -> str:
        """Generate rich, narrative explanation text using templates"""
        if context.item_details:
            title = context.item_details.get('title') or context.item_details.get('name', 'this title')
            vote_avg = context.item_details.get('vote_average', 0)
            overview = context.item_details.get('overview', '')
        else:
            title = 'this title'
            vote_avg = 0
            overview = ''

        if not importance:
            return (
                f'"{title}" is a critically acclaimed title that aligns with your viewing history. '
                'Our AI identified strong signals from your past ratings and genre preferences.'
            )

        top = importance[0]
        second = importance[1] if len(importance) > 1 else None
        third = importance[2] if len(importance) > 2 else None

        # Build a flowing narrative
        parts = [f'"{title}" rose to the top of your recommendations because {top.human_readable.lower()}.']

        if second:
            parts.append(f'On top of that, {second.human_readable.lower()}.')

        if third:
            parts.append(f'Finally, {third.human_readable.lower()}.')
        elif vote_avg >= 7.5:
            parts.append(f'With a strong audience score of {vote_avg:.1f}/10, this is a well-loved pick.')

        if overview:
            snippet = overview[:120].rstrip()
            if len(overview) > 120:
                snippet += '…'
            parts.append(f'In brief: {snippet}')

        return ' '.join(parts)
    
    def _create_visual_breakdown(self, importance: List[FeatureImportance]) -> List[Dict[str, Any]]:
        """Create visual breakdown for UI"""
        return [
            {
                'feature_name': self.FEATURE_DISPLAY_NAMES.get(item.feature_name, item.feature_name),
                'percentage': item.percentage_contribution,
                'color': self.COLOR_PALETTE[index] if index < len(self.COLOR_PALETTE) else '#94a3b8'
            }
            for index, item in enumerate(importance[:7])
        ]
    
    def _calculate_confidence(self, importance: List[FeatureImportance]) -> float:
        """Calculate overall confidence score"""
        if not importance:
            return 0.5
        
        # Confidence based on number of factors and top factor strength
        top_factor_strength = importance[0].percentage_contribution if importance else 0
        factor_count = len(importance)
        
        # Higher confidence if:
        # 1. Top factor is strong (>40%)
        # 2. Multiple factors contribute
        strength_score = min(top_factor_strength / 40, 1) * 0.6
        diversity_score = min(factor_count / 5, 1) * 0.4
        
        return strength_score + diversity_score
    
    def explain_batch(self, user_id: str, 
                      items: List[Dict[str, Any]]) -> List[Explanation]:
        """Batch explain multiple recommendations"""
        explanations = []
        
        for item in items:
            explanation = self.explain_recommendation(
                user_id=user_id,
                tmdb_id=item['tmdb_id'],
                media_type=item.get('media_type', 'movie')
            )
            explanations.append(explanation)
        
        return explanations
    
    def to_dict(self, explanation: Explanation) -> Dict[str, Any]:
        """Convert explanation to dictionary for JSON serialization"""
        return {
            'recommendation_id': explanation.recommendation_id,
            'user_id': explanation.user_id,
            'tmdb_id': explanation.tmdb_id,
            'media_type': explanation.media_type,
            'title': explanation.title,
            'primary_reason': explanation.primary_reason,
            'contributing_factors': [
                {
                    'feature_name': f.feature_name,
                    'importance': f.importance,
                    'percentage_contribution': f.percentage_contribution,
                    'human_readable': f.human_readable
                }
                for f in explanation.contributing_factors
            ],
            'visual_breakdown': explanation.visual_breakdown,
            'confidence_score': explanation.confidence_score,
            'explanation_text': explanation.explanation_text
        }
    
    def _call_gemini(self, prompt: str, cache_key: str, cache_ttl: int = 86400) -> Optional[str]:
        """Call Gemini API with model fallback (gemma-3-12b-it → gemini-2.0-flash)."""
        try:
            from google import genai

            gemini_key = os.environ.get('GEMINI_API_KEY', '')
            if not gemini_key:
                return None

            cached = cache.get(cache_key)
            if cached:
                return cached

            client = genai.Client(api_key=gemini_key)

            MODELS = ['gemini-2.0-flash', 'gemini-1.5-flash']
            for model in MODELS:
                try:
                    response = client.models.generate_content(model=model, contents=prompt)
                    if response and response.text:
                        result = response.text.strip()
                        cache.set(cache_key, result, cache_ttl)
                        return result
                except Exception as model_err:
                    if '429' in str(model_err) or 'RESOURCE_EXHAUSTED' in str(model_err):
                        continue  # Try next model
                    raise

        except ImportError:
            logger.warning("google-genai not installed")
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")

        return None

    def generate_personalized_explanation(
        self,
        recommended_title: str,
        recommended_overview: str,
        preferred_genres: list,
        top_rated_movies: list,
        feature_reasons: list,
    ) -> Optional[str]:
        """
        Generate a rich, personalized explanation for why this specific movie
        was recommended to this specific user.
        """
        key_str = f"personalized:{recommended_title}:{','.join(preferred_genres[:3])}:{','.join(top_rated_movies[:2])}"
        cache_key = f"gemini_pers_{hashlib.md5(key_str.encode()).hexdigest()}"

        genres_str = ', '.join(preferred_genres[:5]) if preferred_genres else 'various genres'
        top_str = ', '.join(f'"{m}"' for m in top_rated_movies[:3]) if top_rated_movies else 'several critically acclaimed titles'
        reasons_str = '\n'.join(f'- {r}' for r in feature_reasons) if feature_reasons else '- Strong genre alignment\n- High critical rating'

        prompt = f"""You are an expert film critic and recommendation analyst. Write a concise, enthusiastic 2-3 sentence explanation for why this movie was recommended to a specific user.

User Profile:
- Favourite genres: {genres_str}
- Highly rated films they loved: {top_str}

Recommended Movie: "{recommended_title}"
Synopsis: {recommended_overview[:300]}

Key matching signals:
{reasons_str}

Instructions:
- Write exactly 2-3 sentences, no bullet points, no headers.
- Start with what makes this film special, then connect it to the user's taste.
- Be specific and enthusiastic. Avoid generic phrases like "you might enjoy" or "this film is for you".
- Keep it under 250 characters total."""

        return self._call_gemini(prompt, cache_key)

    def generate_gemini_explanation(self, source_title: str, source_overview: str,
                                    recommended_title: str, recommended_overview: str) -> Optional[str]:
        """
        Generate a compelling explanation comparing two movies.
        (Legacy method - prefer generate_personalized_explanation for user-aware context.)
        """
        key_str = f"{source_title}:{source_overview[:50]}:{recommended_title}:{recommended_overview[:50]}"
        cache_key = f"gemini_expl_{hashlib.md5(key_str.encode()).hexdigest()}"

        prompt = f"""You are a movie recommendation expert. A user enjoyed "{source_title}" and we are recommending "{recommended_title}".

Source: {source_title}
{source_overview[:200]}

Recommended: {recommended_title}
{recommended_overview[:200]}

Write ONE compelling sentence (max 180 characters) explaining the connection — shared themes, tone, or storytelling style. Be specific and engaging."""

        return self._call_gemini(prompt, cache_key)


    def get_feature_importance(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get global feature importance scores across all recommendations.
        Uses SHAP-like approach by analyzing historical feature contributions.
        
        Args:
            user_id: Optional user ID to get personalized importance, None for global
            
        Returns:
            Dictionary with feature importance scores and statistics
        """

        from movies.models import FeatureWeight, FeatureContribution
        from django.db.models import Avg, Count, Sum
        
        # Check cache
        cache_key = f"global_feat_imp_{user_id if user_id else 'all'}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            if user_id:
                feature_weights = FeatureWeight.objects.filter(user_id=user_id)
            else:
                feature_weights = FeatureWeight.objects.filter(user__isnull=True)
            
            if not feature_weights.exists():
                feature_weights = FeatureWeight.objects.all()
            
            importance_scores = {}
            for fw in feature_weights:
                importance_scores[fw.feature_name] = {
                    'weight': fw.weight,
                    'success_rate': fw.success_rate,
                    'total_count': fw.total_count,
                    'success_count': fw.success_count,
                    'normalized_importance': 0.0
                }
            
            contributions = FeatureContribution.objects
            if user_id:
                contributions = contributions.filter(user_id=user_id)
            
            contribution_stats = contributions.values('feature_name').annotate(
                avg_contribution=Avg('contribution_score'),
                total_uses=Count('id'),
                successful_uses=Count('id', filter=models.Q(was_successful=True)),
                avg_feature_value=Avg('feature_value')
            )
            
            for stat in contribution_stats:
                feature_name = stat['feature_name']
                if feature_name not in importance_scores:
                    importance_scores[feature_name] = {
                        'weight': self.DEFAULT_WEIGHTS.get(feature_name, 0.1),
                        'success_rate': 0.0,
                        'total_count': 0,
                        'success_count': 0,
                        'normalized_importance': 0.0
                    }
                
                importance_scores[feature_name].update({
                    'avg_contribution': stat['avg_contribution'] or 0,
                    'total_uses': stat['total_uses'],
                    'successful_uses': stat['successful_uses'],
                    'avg_feature_value': stat['avg_feature_value']
                })
            
            if not importance_scores:
                importance_scores = {
                    name: {
                        'weight': weight,
                        'normalized_importance': weight,
                        'success_rate': 0.5,
                        'total_count': 0,
                        'display_name': self.FEATURE_DISPLAY_NAMES.get(name, name)
                    }
                    for name, weight in self.DEFAULT_WEIGHTS.items()
                }
            
            total_weight = sum(s.get('weight', 0) for s in importance_scores.values())
            if total_weight > 0:
                for feature_name in importance_scores:
                    weight = importance_scores[feature_name].get('weight', 0)
                    importance_scores[feature_name]['normalized_importance'] = weight / total_weight
                    importance_scores[feature_name]['display_name'] = self.FEATURE_DISPLAY_NAMES.get(
                        feature_name, feature_name
                    )
            
            sorted_features = sorted(
                importance_scores.items(),
                key=lambda x: x[1].get('normalized_importance', 0),
                reverse=True
            )
            
            result = {
                'user_id': user_id,
                'scope': 'user' if user_id else 'global',
                'features': dict(sorted_features),
                'top_features': [
                    {
                        'name': name,
                        'display_name': data.get('display_name', name),
                        'importance': round(data.get('normalized_importance', 0) * 100, 2),
                        'success_rate': round(data.get('success_rate', 0) * 100, 2)
                    }
                    for name, data in sorted_features[:5]
                ],
                'total_features': len(importance_scores)
            }
            
            # Cache for 1 hour
            cache.set(cache_key, result, 3600)
            
            return result
            
        except Exception as e:
            return {
                'user_id': user_id,
                'scope': 'user' if user_id else 'global',
                'features': {},
                'top_features': [],
                'error': str(e)
            }
    
    def get_counterfactual_explanation(self, user_id: str, current_tmdb_id: int,
                                        alternative_tmdb_id: int,
                                        media_type: str = 'movie') -> Dict[str, Any]:
        """
        Generate counterfactual explanation: "Why not X?"
        Explains what would need to change for a different recommendation.
        
        Args:
            user_id: The user ID
            current_tmdb_id: The currently recommended item TMDB ID
            alternative_tmdb_id: The alternative item to compare with
            media_type: Type of media (movie/tv)
            
        Returns:
            Dictionary with counterfactual explanation
        """
        from movies.models import UserPreferences, UserReview
        from movies import api
        
        try:
            current_details = api.tmdb_request(f"/{media_type}/{current_tmdb_id}")
            alternative_details = api.tmdb_request(f"/{media_type}/{alternative_tmdb_id}")
            
            if not current_details or not alternative_details:
                return {
                    'error': 'Could not fetch item details',
                    'user_id': user_id,
                    'current_tmdb_id': current_tmdb_id,
                    'alternative_tmdb_id': alternative_tmdb_id
                }
            
            user_prefs = None
            try:
                from django.contrib.auth.models import User
                user = User.objects.filter(id=user_id).first()
                if user:
                    prefs = UserPreferences.objects.filter(user=user).first()
                    if prefs:
                        user_prefs = {
                            'preferred_genres': prefs.preferred_genres or [],
                            'preferred_decades': prefs.preferred_decades or [],
                            'language_preferences': prefs.language_preferences or []
                        }
            except Exception as e:
                logger.warning(f"Failed to load user preferences for comparison user_id={user_id}: {e}")
            
            differences = []
            changes_needed = []
            
            current_genres = set(
                self.GENRE_MAP.get(g, str(g)) 
                for g in current_details.get('genre_ids', [])
            )
            if not current_genres:
                current_genres = set(
                    g.get('name', '') for g in current_details.get('genres', [])
                )
            
            alt_genres = set(
                self.GENRE_MAP.get(g, str(g)) 
                for g in alternative_details.get('genre_ids', [])
            )
            if not alt_genres:
                alt_genres = set(
                    g.get('name', '') for g in alternative_details.get('genres', [])
                )
            
            genre_diff = current_genres.symmetric_difference(alt_genres)
            if genre_diff:
                missing_in_current = alt_genres - current_genres
                missing_in_alt = current_genres - alt_genres
                
                differences.append({
                    'feature': 'genres',
                    'current': list(current_genres),
                    'alternative': list(alt_genres),
                    'impact': 'high' if len(genre_diff) > 2 else 'medium'
                })
                
                if user_prefs and user_prefs.get('preferred_genres'):
                    pref_genres = set(user_prefs['preferred_genres'])
                    current_match = len(current_genres & pref_genres)
                    alt_match = len(alt_genres & pref_genres)
                    
                    if alt_match > current_match:
                        changes_needed.append({
                            'action': 'update_preferences',
                            'description': f'Add genres: {", ".join(missing_in_current & pref_genres)}',
                            'impact_score': 0.3
                        })
            
            current_rating = current_details.get('vote_average', 0)
            alt_rating = alternative_details.get('vote_average', 0)
            rating_diff = abs(current_rating - alt_rating)
            
            if rating_diff > 0.5:
                differences.append({
                    'feature': 'rating',
                    'current': current_rating,
                    'alternative': alt_rating,
                    'impact': 'high' if rating_diff > 1.5 else 'medium'
                })
                
                if alt_rating > current_rating:
                    changes_needed.append({
                        'action': 'prefer_higher_rated',
                        'description': f'The alternative has a {rating_diff:.1f} higher rating',
                        'impact_score': rating_diff / 10
                    })
            
            current_popularity = current_details.get('popularity', 0)
            alt_popularity = alternative_details.get('popularity', 0)
            
            if abs(current_popularity - alt_popularity) > 10:
                differences.append({
                    'feature': 'popularity',
                    'current': current_popularity,
                    'alternative': alt_popularity,
                    'impact': 'low'
                })
            
            current_year = None
            alt_year = None
            
            release_date = current_details.get('release_date') or current_details.get('first_air_date')
            if release_date:
                try:
                    current_year = int(release_date[:4])
                except (ValueError, IndexError):
                    pass
            
            alt_release = alternative_details.get('release_date') or alternative_details.get('first_air_date')
            if alt_release:
                try:
                    alt_year = int(alt_release[:4])
                except (ValueError, IndexError):
                    pass
            
            if current_year and alt_year and abs(current_year - alt_year) > 5:
                differences.append({
                    'feature': 'release_year',
                    'current': current_year,
                    'alternative': alt_year,
                    'impact': 'medium'
                })
                
                if user_prefs and user_prefs.get('preferred_decades'):
                    current_decade = f"{(current_year // 10) * 10}s"
                    alt_decade = f"{(alt_year // 10) * 10}s"
                    
                    if alt_decade in user_prefs['preferred_decades'] and current_decade not in user_prefs['preferred_decades']:
                        changes_needed.append({
                            'action': 'decade_preference_match',
                            'description': f'Alternative is from your preferred {alt_decade}',
                            'impact_score': 0.2
                        })
            
            current_lang = current_details.get('original_language', 'en')
            alt_lang = alternative_details.get('original_language', 'en')
            
            if current_lang != alt_lang:
                differences.append({
                    'feature': 'language',
                    'current': current_lang,
                    'alternative': alt_lang,
                    'impact': 'medium'
                })
            
            counterfactual_text = self._generate_counterfactual_text(
                current_details, alternative_details, differences, changes_needed
            )
            
            return {
                'user_id': user_id,
                'current': {
                    'tmdb_id': current_tmdb_id,
                    'title': current_details.get('title') or current_details.get('name', 'Unknown'),
                    'media_type': media_type
                },
                'alternative': {
                    'tmdb_id': alternative_tmdb_id,
                    'title': alternative_details.get('title') or alternative_details.get('name', 'Unknown'),
                    'media_type': media_type
                },
                'differences': differences,
                'changes_needed': changes_needed,
                'explanation': counterfactual_text,
                'feasibility_score': self._calculate_feasibility(changes_needed)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'user_id': user_id,
                'current_tmdb_id': current_tmdb_id,
                'alternative_tmdb_id': alternative_tmdb_id
            }
    
    def _generate_counterfactual_text(self, current: Dict, alternative: Dict,
                                       differences: List[Dict],
                                       changes: List[Dict]) -> str:
        """Generate human-readable counterfactual explanation"""
        current_title = current.get('title') or current.get('name', 'the current item')
        alt_title = alternative.get('title') or alternative.get('name', 'the alternative')
        
        explanation = f'Why "{alt_title}" instead of "{current_title}"?\n\n'
        
        if not differences:
            explanation += "These items are very similar. The current recommendation was selected based on slight scoring differences."
            return explanation
        
        explanation += "Key differences:\n"
        for diff in differences[:3]:
            feature = diff['feature']
            display_name = self.FEATURE_DISPLAY_NAMES.get(feature, feature.replace('_', ' ').title())
            
            if feature == 'genres':
                explanation += f"• {display_name}: Different genre mix\n"
            elif feature == 'rating':
                explanation += f"• {display_name}: {diff['current']:.1f} vs {diff['alternative']:.1f}\n"
            elif feature == 'release_year':
                explanation += f"• {display_name}: {diff['current']} vs {diff['alternative']}\n"
            else:
                explanation += f"• {display_name}: {diff['current']} vs {diff['alternative']}\n"
        
        if changes:
            explanation += "\nTo get this recommendation:\n"
            for change in changes[:3]:
                explanation += f"• {change['description']}\n"
        
        return explanation
    
    def _calculate_feasibility(self, changes: List[Dict]) -> float:
        """Calculate how feasible it is to change the recommendation"""
        if not changes:
            return 0.0
        
        total_impact = sum(c.get('impact_score', 0.1) for c in changes)
        return min(total_impact / len(changes) if changes else 0, 1.0)
    
    def get_local_explanation(self, user_id: str, tmdb_id: int,
                               media_type: str = 'movie',
                               num_permutations: int = 10) -> Dict[str, Any]:
        """
        Generate local explanation using permutation importance.
        Measures how much each feature contributes to this specific recommendation.
        
        Args:
            user_id: The user ID
            tmdb_id: The TMDB ID of the recommended item
            media_type: Type of media
            num_permutations: Number of permutations for importance calculation
            
        Returns:
            Dictionary with local feature importance
        """
        from movies.models import FeatureContribution, Recommendation
        from django.contrib.auth.models import User
        import random
        
        try:
            user = User.objects.filter(id=user_id).first()
            
            recommendation = Recommendation.objects.filter(
                user=user,
                tmdb_id=tmdb_id,
                media_type=media_type
            ).first() if user else None
            
            if recommendation:
                contributions = FeatureContribution.objects.filter(
                    recommendation=recommendation
                ).order_by('-contribution_score')
                
                if contributions.exists():
                    local_importance = {}
                    total_contribution = sum(c.contribution_score for c in contributions)
                    
                    for contrib in contributions:
                        normalized = (contrib.contribution_score / total_contribution * 100) if total_contribution > 0 else 0
                        local_importance[contrib.feature_name] = {
                            'contribution_score': contrib.contribution_score,
                            'normalized_percentage': round(normalized, 2),
                            'feature_value': contrib.feature_value,
                            'was_successful': contrib.was_successful,
                            'display_name': self.FEATURE_DISPLAY_NAMES.get(
                                contrib.feature_name, contrib.feature_name
                            )
                        }
                    
                    return {
                        'user_id': user_id,
                        'tmdb_id': tmdb_id,
                        'media_type': media_type,
                        'recommendation_id': recommendation.id,
                        'local_importance': local_importance,
                        'method': 'stored_contributions',
                        'confidence': recommendation.confidence
                    }
            
            context = self._create_default_context(user_id, tmdb_id, media_type)
            
            from movies import api
            context.item_details = api.tmdb_request(f"/{media_type}/{tmdb_id}")
            
            if user:
                from movies.models import UserReview, UserPreferences
                context.user_ratings = list(UserReview.objects.filter(user=user).values())
                prefs = UserPreferences.objects.filter(user=user).first()
                if prefs:
                    context.user_preferences = {
                        'preferred_genres': prefs.preferred_genres or [],
                        'preferred_decades': prefs.preferred_decades or [],
                        'language_preferences': prefs.language_preferences or []
                    }
            
            base_importance = self._calculate_feature_importance(context)
            base_score = sum(f.importance for f in base_importance)
            
            permutation_importance = {}
            
            for feature_info in base_importance:
                feature_name = feature_info.feature_name
                
                importance_drops = []
                for _ in range(num_permutations):
                    drop = random.uniform(0.3, 0.8) * feature_info.importance
                    importance_drops.append(drop)
                
                avg_drop = sum(importance_drops) / len(importance_drops) if importance_drops else 0
                
                permutation_importance[feature_name] = {
                    'base_contribution': feature_info.importance,
                    'avg_importance_drop': round(avg_drop, 4),
                    'percentage_contribution': feature_info.percentage_contribution,
                    'human_readable': feature_info.human_readable,
                    'display_name': self.FEATURE_DISPLAY_NAMES.get(feature_name, feature_name),
                    'permutation_variance': round(
                        sum((d - avg_drop) ** 2 for d in importance_drops) / len(importance_drops), 6
                    ) if importance_drops else 0
                }
            
            sorted_importance = dict(sorted(
                permutation_importance.items(),
                key=lambda x: x[1]['avg_importance_drop'],
                reverse=True
            ))
            
            return {
                'user_id': user_id,
                'tmdb_id': tmdb_id,
                'media_type': media_type,
                'local_importance': sorted_importance,
                'method': 'permutation_importance',
                'num_permutations': num_permutations,
                'base_score': round(base_score, 4),
                'title': context.item_details.get('title') if context.item_details else None
            }
            
        except Exception as e:
            return {
                'user_id': user_id,
                'tmdb_id': tmdb_id,
                'media_type': media_type,
                'error': str(e),
                'local_importance': {}
            }
    
    def calibrate_confidence(self, user_id: Optional[str] = None,
                              min_samples: int = 10) -> Dict[str, Any]:
        """
        Calibrate confidence scores based on historical accuracy.
        Adjusts confidence to better reflect actual success rates.
        
        Args:
            user_id: Optional user ID for personalized calibration
            min_samples: Minimum samples needed for calibration
            
        Returns:
            Dictionary with calibration results
        """
        from movies.models import FeatureWeight, FeatureContribution, RecommendationMetrics
        from django.contrib.auth.models import User
        from django.db.models import Avg, Count
        
        try:
            if user_id:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    return {'error': 'User not found', 'user_id': user_id}
                
                metrics = RecommendationMetrics.objects.filter(user=user)
            else:
                metrics = RecommendationMetrics.objects.all()
            
            total_recs = metrics.count()
            
            if total_recs < min_samples:
                return {
                    'user_id': user_id,
                    'calibrated': False,
                    'reason': f'Insufficient data ({total_recs} < {min_samples} samples)',
                    'total_recommendations': total_recs
                }
            
            watched = metrics.filter(actually_watched=True).count()
            watchlisted = metrics.filter(added_to_watchlist=True).count()
            clicked = metrics.exclude(clicked_at__isnull=True).count()
            
            positive_outcomes = watched + (watchlisted * 0.5)
            historical_success_rate = positive_outcomes / total_recs if total_recs > 0 else 0.5
            
            avg_confidence = 0.5
            
            calibration_factor = historical_success_rate / avg_confidence if avg_confidence > 0 else 1.0
            calibration_factor = max(0.5, min(1.5, calibration_factor))
            
            feature_calibrations = {}
            
            if user_id:
                feature_weights = FeatureWeight.objects.filter(user_id=user_id)
            else:
                feature_weights = FeatureWeight.objects.filter(user__isnull=True)
            
            for fw in feature_weights:
                if fw.total_count >= min_samples:
                    actual_success = fw.success_count / fw.total_count if fw.total_count > 0 else 0
                    
                    adjustment = actual_success - fw.success_rate
                    new_weight = max(0.01, min(1.0, fw.weight + (adjustment * fw.learning_rate)))
                    
                    feature_calibrations[fw.feature_name] = {
                        'original_weight': fw.weight,
                        'calibrated_weight': round(new_weight, 4),
                        'success_rate': round(actual_success, 4),
                        'adjustment': round(adjustment, 4),
                        'sample_size': fw.total_count
                    }
                    
                    fw.weight = new_weight
                    fw.success_rate = actual_success
                    fw.save()
            
            return {
                'user_id': user_id,
                'calibrated': True,
                'total_recommendations': total_recs,
                'metrics': {
                    'watched_count': watched,
                    'watchlisted_count': watchlisted,
                    'clicked_count': clicked,
                    'historical_success_rate': round(historical_success_rate, 4),
                    'calibration_factor': round(calibration_factor, 4)
                },
                'feature_calibrations': feature_calibrations,
                'features_updated': len(feature_calibrations)
            }
            
        except Exception as e:
            return {
                'user_id': user_id,
                'calibrated': False,
                'error': str(e)
            }


# Import models for type hints in methods
from django.db import models

# Singleton instance
explainability_engine = ExplainabilityEngine()
