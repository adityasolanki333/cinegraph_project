"""
Pattern Recognition Module for CineGraph
Analyzes user viewing patterns to detect preferences and behaviors
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from django.db.models import Count, Avg
from django.db.models.functions import ExtractHour, ExtractWeekDay
from django.contrib.auth.models import User


@dataclass
class GenrePreference:
    genre_id: int
    genre_name: str
    watch_count: int
    avg_rating: float
    trend: str


@dataclass
class ViewingTimePattern:
    peak_hour: int
    peak_day: int
    morning_percentage: float
    afternoon_percentage: float
    evening_percentage: float
    night_percentage: float
    weekend_preference: float


@dataclass
class BingePattern:
    is_binge_watcher: bool
    avg_daily_watches: float
    max_daily_watches: int
    binge_sessions: int
    favorite_binge_genre: Optional[str]


@dataclass
class RatingTrend:
    trend_direction: str
    avg_early_rating: float
    avg_recent_rating: float
    rating_variance: float
    is_generous_rater: bool
    is_critical_rater: bool


@dataclass
class PatternSummary:
    user_id: int
    genre_preferences: List[GenrePreference]
    viewing_time_pattern: ViewingTimePattern
    binge_pattern: BingePattern
    rating_trend: RatingTrend
    insights: List[str]
    generated_at: datetime = field(default_factory=datetime.now)


class ViewingPatternAnalyzer:
    """
    Analyzes user viewing history to detect patterns and preferences
    """
    
    GENRE_MAP = {
        28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy",
        80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family",
        14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music",
        9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
        10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
    }
    
    def __init__(self):
        self.binge_threshold = 3
        self.recent_window_days = 30
    
    def _get_user_reviews(self, user_id: int):
        """Fetch user reviews from database"""
        from movies.models import UserReview
        return UserReview.objects.filter(user_id=user_id).order_by('-created_at')
    
    def _get_viewing_history(self, user_id: int):
        """Fetch viewing history from database"""
        from movies.models import ViewingHistory
        return ViewingHistory.objects.filter(user_id=user_id).order_by('-watched_at')
    
    def _get_user_watchlist(self, user_id: int):
        """Fetch user watchlist from database"""
        from movies.models import UserWatchlist
        return UserWatchlist.objects.filter(user_id=user_id)
    
    def analyze_genre_preferences(self, user_id: int) -> List[GenrePreference]:
        """
        Analyze genre preferences based on viewing history and ratings
        
        Returns list of genres sorted by preference strength
        """
        reviews = self._get_user_reviews(user_id)
        history = self._get_viewing_history(user_id)
        
        genre_stats = defaultdict(lambda: {'count': 0, 'ratings': [], 'recent_count': 0})
        
        cutoff_date = datetime.now() - timedelta(days=self.recent_window_days)
        
        for review in reviews:
            genres = getattr(review, 'genres', []) or []
            if isinstance(genres, str):
                try:
                    import json
                    genres = json.loads(genres)
                except:
                    genres = []
            
            for genre_id in genres:
                genre_stats[genre_id]['count'] += 1
                genre_stats[genre_id]['ratings'].append(review.rating)
                if review.created_at and review.created_at.replace(tzinfo=None) > cutoff_date:
                    genre_stats[genre_id]['recent_count'] += 1
        
        for item in history:
            genres = getattr(item, 'genres', []) or []
            if isinstance(genres, str):
                try:
                    import json
                    genres = json.loads(genres)
                except:
                    genres = []
            
            for genre_id in genres:
                genre_stats[genre_id]['count'] += 1
        
        preferences = []
        for genre_id, stats in genre_stats.items():
            if stats['count'] > 0:
                avg_rating = np.mean(stats['ratings']) if stats['ratings'] else 0.0
                
                recent_ratio = stats['recent_count'] / stats['count'] if stats['count'] > 0 else 0
                if recent_ratio > 0.5:
                    trend = 'increasing'
                elif recent_ratio < 0.2:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                preferences.append(GenrePreference(
                    genre_id=genre_id,
                    genre_name=self.GENRE_MAP.get(genre_id, f"Genre {genre_id}"),
                    watch_count=stats['count'],
                    avg_rating=round(float(avg_rating), 2),
                    trend=trend
                ))
        
        preferences.sort(key=lambda x: (x.watch_count, x.avg_rating), reverse=True)
        return preferences[:10]
    
    def analyze_viewing_time_patterns(self, user_id: int) -> ViewingTimePattern:
        """
        Analyze when the user typically watches content
        
        Returns viewing time pattern analysis
        """
        history = self._get_viewing_history(user_id)
        
        hour_counts = defaultdict(int)
        day_counts = defaultdict(int)
        
        time_periods = {'morning': 0, 'afternoon': 0, 'evening': 0, 'night': 0}
        weekend_count = 0
        weekday_count = 0
        
        for item in history:
            if item.watched_at:
                hour = item.watched_at.hour
                day = item.watched_at.weekday()
                
                hour_counts[hour] += 1
                day_counts[day] += 1
                
                if 5 <= hour < 12:
                    time_periods['morning'] += 1
                elif 12 <= hour < 17:
                    time_periods['afternoon'] += 1
                elif 17 <= hour < 21:
                    time_periods['evening'] += 1
                else:
                    time_periods['night'] += 1
                
                if day >= 5:
                    weekend_count += 1
                else:
                    weekday_count += 1
        
        total_watches = sum(time_periods.values())
        
        if total_watches == 0:
            return ViewingTimePattern(
                peak_hour=20,
                peak_day=5,
                morning_percentage=0.0,
                afternoon_percentage=0.0,
                evening_percentage=0.0,
                night_percentage=0.0,
                weekend_preference=0.5
            )
        
        peak_hour = max(hour_counts.keys(), default=20) if hour_counts else 20
        peak_day = max(day_counts.keys(), default=5) if day_counts else 5
        
        total_days = weekend_count + weekday_count
        weekend_preference = weekend_count / total_days if total_days > 0 else 0.5
        
        return ViewingTimePattern(
            peak_hour=peak_hour,
            peak_day=peak_day,
            morning_percentage=round(time_periods['morning'] / total_watches * 100, 1),
            afternoon_percentage=round(time_periods['afternoon'] / total_watches * 100, 1),
            evening_percentage=round(time_periods['evening'] / total_watches * 100, 1),
            night_percentage=round(time_periods['night'] / total_watches * 100, 1),
            weekend_preference=round(weekend_preference, 2)
        )
    
    def detect_binge_watching(self, user_id: int) -> BingePattern:
        """
        Detect binge-watching behavior patterns
        
        Returns binge watching pattern analysis
        """
        history = self._get_viewing_history(user_id)
        
        daily_watches = defaultdict(list)
        
        for item in history:
            if item.watched_at:
                date_key = item.watched_at.date()
                daily_watches[date_key].append({
                    'title': item.title,
                    'tmdb_id': item.tmdb_id,
                    'media_type': item.media_type
                })
        
        if not daily_watches:
            return BingePattern(
                is_binge_watcher=False,
                avg_daily_watches=0.0,
                max_daily_watches=0,
                binge_sessions=0,
                favorite_binge_genre=None
            )
        
        daily_counts = [len(watches) for watches in daily_watches.values()]
        avg_daily = np.mean(daily_counts)
        max_daily = max(daily_counts)
        
        binge_sessions = sum(1 for count in daily_counts if count >= self.binge_threshold)
        
        is_binge_watcher = binge_sessions >= 3 or avg_daily >= 2
        
        binge_genre_counts = Counter()
        for date, watches in daily_watches.items():
            if len(watches) >= self.binge_threshold:
                for watch in watches:
                    genres = watch.get('genres', []) if isinstance(watch, dict) else getattr(watch, 'genres', [])
                    if not genres:
                        continue
                    if isinstance(genres, str):
                        try:
                            import json
                            genres = json.loads(genres)
                        except:
                            genres = []
                    for genre_id in genres:
                        binge_genre_counts[genre_id] += 1
        
        favorite_binge_genre = None
        if binge_genre_counts:
            top_genre_id = binge_genre_counts.most_common(1)[0][0]
            favorite_binge_genre = self.GENRE_MAP.get(top_genre_id, f"Genre {top_genre_id}")
        
        return BingePattern(
            is_binge_watcher=is_binge_watcher,
            avg_daily_watches=round(float(avg_daily), 2),
            max_daily_watches=max_daily,
            binge_sessions=binge_sessions,
            favorite_binge_genre=favorite_binge_genre
        )
    
    def analyze_rating_trends(self, user_id: int) -> RatingTrend:
        """
        Analyze how user ratings have changed over time
        
        Returns rating trend analysis
        """
        reviews = list(self._get_user_reviews(user_id))
        
        if len(reviews) < 2:
            return RatingTrend(
                trend_direction='insufficient_data',
                avg_early_rating=0.0,
                avg_recent_rating=0.0,
                rating_variance=0.0,
                is_generous_rater=False,
                is_critical_rater=False
            )
        
        ratings = [r.rating for r in reviews]
        
        mid_point = len(reviews) // 2
        early_reviews = reviews[mid_point:]
        recent_reviews = reviews[:mid_point]
        
        early_ratings = [r.rating for r in early_reviews]
        recent_ratings = [r.rating for r in recent_reviews]
        
        avg_early = np.mean(early_ratings) if early_ratings else 0
        avg_recent = np.mean(recent_ratings) if recent_ratings else 0
        
        rating_variance = float(np.var(ratings))
        
        diff = avg_recent - avg_early
        if diff > 0.5:
            trend_direction = 'becoming_generous'
        elif diff < -0.5:
            trend_direction = 'becoming_critical'
        else:
            trend_direction = 'stable'
        
        overall_avg = np.mean(ratings)
        is_generous = overall_avg >= 7.0
        is_critical = overall_avg <= 5.0
        
        return RatingTrend(
            trend_direction=trend_direction,
            avg_early_rating=round(float(avg_early), 2),
            avg_recent_rating=round(float(avg_recent), 2),
            rating_variance=round(rating_variance, 2),
            is_generous_rater=is_generous,
            is_critical_rater=is_critical
        )
    
    def _generate_insights(self, genre_prefs: List[GenrePreference],
                          time_pattern: ViewingTimePattern,
                          binge_pattern: BingePattern,
                          rating_trend: RatingTrend) -> List[str]:
        """Generate human-readable insights from patterns"""
        insights = []
        
        if genre_prefs:
            top_genre = genre_prefs[0]
            insights.append(f"Your favorite genre is {top_genre.genre_name} "
                          f"with {top_genre.watch_count} watches")
            
            increasing_genres = [g for g in genre_prefs if g.trend == 'increasing']
            if increasing_genres:
                insights.append(f"You're watching more {increasing_genres[0].genre_name} lately")
        
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                     'Friday', 'Saturday', 'Sunday']
        peak_day_name = day_names[time_pattern.peak_day] if time_pattern.peak_day < 7 else 'Weekend'
        
        if time_pattern.evening_percentage > 40:
            insights.append("You're an evening viewer - most of your watching happens after 5 PM")
        elif time_pattern.night_percentage > 30:
            insights.append("Night owl alert! You often watch content late at night")
        
        if time_pattern.weekend_preference > 0.6:
            insights.append("You prefer weekend viewing sessions")
        
        insights.append(f"Your peak viewing day is {peak_day_name}")
        
        if binge_pattern.is_binge_watcher:
            insights.append(f"You're a binge watcher! You've had {binge_pattern.binge_sessions} "
                          f"binge sessions (3+ items in a day)")
            if binge_pattern.favorite_binge_genre:
                insights.append(f"You love binging {binge_pattern.favorite_binge_genre} content")
        
        if rating_trend.trend_direction == 'becoming_generous':
            insights.append("Your ratings have become more generous over time")
        elif rating_trend.trend_direction == 'becoming_critical':
            insights.append("You've become more critical in your ratings recently")
        
        if rating_trend.is_generous_rater:
            insights.append("You're a generous rater with an average above 7/10")
        elif rating_trend.is_critical_rater:
            insights.append("You're a critical viewer with high standards")
        
        return insights
    
    def get_pattern_summary(self, user_id: int) -> PatternSummary:
        """
        Get comprehensive pattern analysis for a user
        
        Args:
            user_id: The user to analyze
            
        Returns:
            PatternSummary with all detected patterns and insights
        """
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return PatternSummary(
                user_id=user_id,
                genre_preferences=[],
                viewing_time_pattern=ViewingTimePattern(
                    peak_hour=20, peak_day=5,
                    morning_percentage=0, afternoon_percentage=0,
                    evening_percentage=0, night_percentage=0,
                    weekend_preference=0.5
                ),
                binge_pattern=BingePattern(
                    is_binge_watcher=False, avg_daily_watches=0,
                    max_daily_watches=0, binge_sessions=0,
                    favorite_binge_genre=None
                ),
                rating_trend=RatingTrend(
                    trend_direction='no_data', avg_early_rating=0,
                    avg_recent_rating=0, rating_variance=0,
                    is_generous_rater=False, is_critical_rater=False
                ),
                insights=["User not found or no viewing history available"]
            )
        
        genre_preferences = self.analyze_genre_preferences(user_id)
        viewing_time_pattern = self.analyze_viewing_time_patterns(user_id)
        binge_pattern = self.detect_binge_watching(user_id)
        rating_trend = self.analyze_rating_trends(user_id)
        
        insights = self._generate_insights(
            genre_preferences, viewing_time_pattern,
            binge_pattern, rating_trend
        )
        
        return PatternSummary(
            user_id=user_id,
            genre_preferences=genre_preferences,
            viewing_time_pattern=viewing_time_pattern,
            binge_pattern=binge_pattern,
            rating_trend=rating_trend,
            insights=insights
        )
    
    def to_dict(self, summary: PatternSummary) -> Dict[str, Any]:
        """Convert PatternSummary to dictionary for JSON serialization"""
        return {
            'user_id': summary.user_id,
            'genre_preferences': [
                {
                    'genre_id': g.genre_id,
                    'genre_name': g.genre_name,
                    'watch_count': g.watch_count,
                    'avg_rating': g.avg_rating,
                    'trend': g.trend
                }
                for g in summary.genre_preferences
            ],
            'viewing_time_pattern': {
                'peak_hour': summary.viewing_time_pattern.peak_hour,
                'peak_day': summary.viewing_time_pattern.peak_day,
                'morning_percentage': summary.viewing_time_pattern.morning_percentage,
                'afternoon_percentage': summary.viewing_time_pattern.afternoon_percentage,
                'evening_percentage': summary.viewing_time_pattern.evening_percentage,
                'night_percentage': summary.viewing_time_pattern.night_percentage,
                'weekend_preference': summary.viewing_time_pattern.weekend_preference
            },
            'binge_pattern': {
                'is_binge_watcher': summary.binge_pattern.is_binge_watcher,
                'avg_daily_watches': summary.binge_pattern.avg_daily_watches,
                'max_daily_watches': summary.binge_pattern.max_daily_watches,
                'binge_sessions': summary.binge_pattern.binge_sessions,
                'favorite_binge_genre': summary.binge_pattern.favorite_binge_genre
            },
            'rating_trend': {
                'trend_direction': summary.rating_trend.trend_direction,
                'avg_early_rating': summary.rating_trend.avg_early_rating,
                'avg_recent_rating': summary.rating_trend.avg_recent_rating,
                'rating_variance': summary.rating_trend.rating_variance,
                'is_generous_rater': summary.rating_trend.is_generous_rater,
                'is_critical_rater': summary.rating_trend.is_critical_rater
            },
            'insights': summary.insights,
            'generated_at': summary.generated_at.isoformat()
        }


viewing_pattern_analyzer = ViewingPatternAnalyzer()
