"""
Sentiment Analysis Module for User Reviews
Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) for sentiment analysis
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from django.db import transaction
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@dataclass
class SentimentResult:
    score: float
    classification: str
    compound: float
    positive: float
    negative: float
    neutral: float


class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.positive_threshold = 0.05
        self.negative_threshold = -0.05
    
    def analyze_text(self, text: str) -> SentimentResult:
        if not text or not text.strip():
            return SentimentResult(
                score=0.0,
                classification='neutral',
                compound=0.0,
                positive=0.0,
                negative=0.0,
                neutral=1.0
            )
        
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= self.positive_threshold:
            classification = 'positive'
        elif compound <= self.negative_threshold:
            classification = 'negative'
        else:
            classification = 'neutral'
        
        return SentimentResult(
            score=compound,
            classification=classification,
            compound=compound,
            positive=scores['pos'],
            negative=scores['neg'],
            neutral=scores['neu']
        )
    
    def analyze_review(self, review) -> SentimentResult:
        review_text = review.review_text if hasattr(review, 'review_text') else ''
        return self.analyze_text(review_text)
    
    @transaction.atomic
    def update_sentiment_analytics(self, tmdb_id: int, media_type: str) -> Dict[str, Any]:
        from movies.models import UserReview, SentimentAnalytics, ReviewSentimentCache
        
        all_reviews = UserReview.objects.filter(tmdb_id=tmdb_id, media_type=media_type)
        
        if not all_reviews.exists():
            analytics, created = SentimentAnalytics.objects.update_or_create(
                tmdb_id=tmdb_id,
                media_type=media_type,
                defaults={
                    'avg_sentiment_score': 0.0,
                    'total_reviews': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0
                }
            )
            return {
                'tmdb_id': tmdb_id,
                'media_type': media_type,
                'avg_sentiment_score': 0.0,
                'total_reviews': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'updated': True
            }
        
        from django.db.models import F, Subquery, OuterRef
        cached_map = dict(
            ReviewSentimentCache.objects.filter(
                review__in=all_reviews
            ).values_list('review_id', 'analyzed_at')
        )
        changed_ids = []
        for review in all_reviews.only('pk', 'updated_at'):
            cached_at = cached_map.get(review.pk)
            if cached_at is None or cached_at < review.updated_at:
                changed_ids.append(review.pk)
        
        if not changed_ids:
            existing = SentimentAnalytics.objects.filter(
                tmdb_id=tmdb_id, media_type=media_type
            ).first()
            if existing:
                return {
                    'tmdb_id': tmdb_id,
                    'media_type': media_type,
                    'avg_sentiment_score': round(existing.avg_sentiment_score, 4),
                    'total_reviews': existing.total_reviews,
                    'positive_count': existing.positive_count,
                    'negative_count': existing.negative_count,
                    'neutral_count': existing.neutral_count,
                    'updated': False
                }
        
        for review in all_reviews.filter(pk__in=changed_ids):
            result = self.analyze_review(review)
            ReviewSentimentCache.objects.update_or_create(
                review=review,
                defaults={
                    'score': result.score,
                    'classification': result.classification,
                }
            )
        
        caches = ReviewSentimentCache.objects.filter(
            review__tmdb_id=tmdb_id,
            review__media_type=media_type
        )
        total_score = 0.0
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        total_reviews = 0
        
        for c in caches:
            total_score += c.score
            total_reviews += 1
            if c.classification == 'positive':
                positive_count += 1
            elif c.classification == 'negative':
                negative_count += 1
            else:
                neutral_count += 1
        
        avg_score = total_score / total_reviews if total_reviews > 0 else 0.0
        
        analytics, created = SentimentAnalytics.objects.update_or_create(
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={
                'avg_sentiment_score': avg_score,
                'total_reviews': total_reviews,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count
            }
        )
        
        return {
            'tmdb_id': tmdb_id,
            'media_type': media_type,
            'avg_sentiment_score': round(avg_score, 4),
            'total_reviews': total_reviews,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count,
            'updated': True
        }
    
    def batch_analyze_all_reviews(self) -> Dict[str, Any]:
        from movies.models import UserReview
        from django.db.models import Count
        
        content_groups = UserReview.objects.values('tmdb_id', 'media_type').annotate(
            review_count=Count('id')
        )
        
        results = {
            'processed_content': 0,
            'total_reviews_analyzed': 0,
            'content_details': []
        }
        
        for group in content_groups:
            tmdb_id = group['tmdb_id']
            media_type = group['media_type']
            
            update_result = self.update_sentiment_analytics(tmdb_id, media_type)
            
            results['processed_content'] += 1
            results['total_reviews_analyzed'] += update_result['total_reviews']
            results['content_details'].append({
                'tmdb_id': tmdb_id,
                'media_type': media_type,
                'reviews_analyzed': update_result['total_reviews'],
                'avg_sentiment': update_result['avg_sentiment_score']
            })
        
        return results


sentiment_analyzer = SentimentAnalyzer()
