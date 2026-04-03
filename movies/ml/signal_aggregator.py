"""
Unified Implicit+Explicit Signal Aggregator

Combines explicit ratings, watch duration, favorites, watchlist additions,
search clicks, and viewing history into a single per-user preference vector
with configurable signal weights.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.utils import timezone


SIGNAL_WEIGHTS = {
    'rating': 1.0,
    'favorite': 0.9,
    'watchlist': 0.6,
    'watch_duration': 0.5,
    'search_click': 0.3,
    'view': 0.2,
}

DECAY_HALF_LIFE_DAYS = 180


def _time_decay(dt, half_life_days=DECAY_HALF_LIFE_DAYS):
    if dt is None:
        return 0.5
    now = timezone.now()
    if timezone.is_naive(dt):
        from django.utils.timezone import make_aware
        dt = make_aware(dt)
    age_days = (now - dt).total_seconds() / 86400.0
    return math.exp(-0.693 * age_days / half_life_days)


class SignalAggregator:
    """
    Builds a per-user preference vector by combining all interaction signals.
    Each entry is (tmdb_id, aggregated_score) where score is in [0, 1].
    """

    def get_user_signals(self, user, max_items=200) -> Dict[int, float]:
        from movies.models import (
            UserReview, UserFavorites, UserWatchlist,
            ViewingHistory, SearchInteraction,
        )

        scores: Dict[int, float] = defaultdict(float)

        reviews = UserReview.objects.filter(user=user).order_by('-created_at').values(
            'tmdb_id', 'rating', 'created_at'
        )[:max_items]
        for r in reviews:
            normalized = r['rating'] / 10.0
            decay = _time_decay(r['created_at'])
            scores[r['tmdb_id']] += normalized * SIGNAL_WEIGHTS['rating'] * decay

        favorites = UserFavorites.objects.filter(user=user).order_by('-added_at').values(
            'tmdb_id', 'added_at'
        )[:max_items]
        for f in favorites:
            decay = _time_decay(f['added_at'])
            scores[f['tmdb_id']] += SIGNAL_WEIGHTS['favorite'] * decay

        watchlist = UserWatchlist.objects.filter(user=user).order_by('-added_at').values(
            'tmdb_id', 'added_at'
        )[:max_items]
        for w in watchlist:
            decay = _time_decay(w['added_at'])
            scores[w['tmdb_id']] += SIGNAL_WEIGHTS['watchlist'] * decay

        history = ViewingHistory.objects.filter(user=user).order_by('-watched_at').values(
            'tmdb_id', 'watched_at', 'watch_duration'
        )[:max_items]
        for h in history:
            decay = _time_decay(h['watched_at'])
            dur = h.get('watch_duration') or 0
            dur_norm = min(dur / 120.0, 1.0) if dur > 0 else 0.3
            scores[h['tmdb_id']] += dur_norm * SIGNAL_WEIGHTS['watch_duration'] * decay
            scores[h['tmdb_id']] += SIGNAL_WEIGHTS['view'] * decay

        clicks = SearchInteraction.objects.filter(user=user).order_by('-created_at').values(
            'tmdb_id', 'created_at'
        )[:max_items]
        for c in clicks:
            decay = _time_decay(c['created_at'])
            scores[c['tmdb_id']] += SIGNAL_WEIGHTS['search_click'] * decay

        if scores:
            max_score = max(scores.values())
            if max_score > 0:
                scores = {k: min(v / max_score, 1.0) for k, v in scores.items()}

        return dict(scores)

    def get_seed_ids(self, user, min_score=0.3, limit=30) -> List[int]:
        signals = self.get_user_signals(user)
        sorted_items = sorted(signals.items(), key=lambda x: x[1], reverse=True)
        return [tmdb_id for tmdb_id, score in sorted_items if score >= min_score][:limit]

    def get_interaction_count(self, user) -> int:
        from django.db.models import Count
        from django.contrib.auth.models import User
        result = User.objects.filter(pk=user.pk).aggregate(
            reviews=Count('reviews', distinct=True),
            favorites=Count('favorites', distinct=True),
            watchlist=Count('watchlist', distinct=True),
            viewing_history=Count('viewing_history', distinct=True),
        )
        return (
            (result['reviews'] or 0) +
            (result['favorites'] or 0) +
            (result['watchlist'] or 0) +
            (result['viewing_history'] or 0)
        )


signal_aggregator = SignalAggregator()
