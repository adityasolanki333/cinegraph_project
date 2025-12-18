import json
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import (
    UserReview, UserWatchlist, UserFavorites, ViewingHistory,
    UserActivityStats, UserFollow, UserList, ReviewInteraction,
    SentimentAnalytics, Recommendation, RecommendationMetrics
)


@require_GET
def get_user_engagement(request, user_id):
    """Get comprehensive user engagement metrics"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        
        reviews_count = UserReview.objects.filter(user=user).count()
        reviews_7d = UserReview.objects.filter(user=user, created_at__gte=last_7_days).count()
        reviews_30d = UserReview.objects.filter(user=user, created_at__gte=last_30_days).count()
        
        watchlist_count = UserWatchlist.objects.filter(user=user).count()
        favorites_count = UserFavorites.objects.filter(user=user).count()
        watched_count = ViewingHistory.objects.filter(user=user).count()
        watched_7d = ViewingHistory.objects.filter(user=user, watched_at__gte=last_7_days).count()
        
        followers_count = UserFollow.objects.filter(following=user).count()
        following_count = UserFollow.objects.filter(follower=user).count()
        
        lists_count = UserList.objects.filter(user=user).count()
        
        avg_rating = UserReview.objects.filter(user=user).aggregate(avg=Avg('rating'))['avg']
        
        helpful_votes = ReviewInteraction.objects.filter(
            review__user=user, 
            interaction_type='helpful'
        ).count()
        
        activity_stats = UserActivityStats.objects.filter(user=user).first()
        
        engagement = {
            "user_id": user_id,
            "username": user.username,
            "content_engagement": {
                "total_reviews": reviews_count,
                "reviews_last_7_days": reviews_7d,
                "reviews_last_30_days": reviews_30d,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "watchlist_items": watchlist_count,
                "favorite_items": favorites_count,
                "watched_items": watched_count,
                "watched_last_7_days": watched_7d,
            },
            "social_engagement": {
                "followers": followers_count,
                "following": following_count,
                "lists_created": lists_count,
                "helpful_votes_received": helpful_votes,
            },
            "gamification": {
                "level": activity_stats.user_level if activity_stats else 1,
                "experience_points": activity_stats.experience_points if activity_stats else 0,
                "total_awards_received": activity_stats.total_awards_received if activity_stats else 0,
                "total_awards_given": activity_stats.total_awards_given if activity_stats else 0,
            },
            "last_activity": activity_stats.last_activity_at.isoformat() if activity_stats and activity_stats.last_activity_at else None
        }
        
        return JsonResponse(engagement)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_content_stats(request, tmdb_id):
    """Get aggregated statistics for a piece of content"""
    try:
        media_type = request.GET.get('media_type', 'movie')
        
        reviews = UserReview.objects.filter(tmdb_id=tmdb_id, media_type=media_type)
        review_count = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        
        rating_distribution = {}
        for i in range(1, 11):
            rating_distribution[str(i)] = reviews.filter(rating=i).count()
        
        watchlist_count = UserWatchlist.objects.filter(
            tmdb_id=tmdb_id, 
            media_type=media_type
        ).count()
        
        favorites_count = UserFavorites.objects.filter(
            tmdb_id=tmdb_id, 
            media_type=media_type
        ).count()
        
        watched_count = ViewingHistory.objects.filter(
            tmdb_id=tmdb_id, 
            media_type=media_type
        ).count()
        
        sentiment = SentimentAnalytics.objects.filter(
            tmdb_id=tmdb_id, 
            media_type=media_type
        ).first()
        
        stats = {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "reviews": {
                "total": review_count,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "rating_distribution": rating_distribution,
            },
            "engagement": {
                "watchlist_count": watchlist_count,
                "favorites_count": favorites_count,
                "watched_count": watched_count,
                "total_engagement": watchlist_count + favorites_count + watched_count,
            },
            "sentiment": {
                "average_score": sentiment.avg_sentiment_score if sentiment else None,
                "positive_count": sentiment.positive_count if sentiment else 0,
                "negative_count": sentiment.negative_count if sentiment else 0,
                "neutral_count": sentiment.neutral_count if sentiment else 0,
            } if sentiment else None
        }
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_popular_content(request):
    """Get popular content based on user engagement"""
    try:
        media_type = request.GET.get('media_type', 'all')
        time_period = request.GET.get('period', '7d')
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        now = timezone.now()
        if time_period == '24h':
            start_date = now - timedelta(hours=24)
        elif time_period == '7d':
            start_date = now - timedelta(days=7)
        elif time_period == '30d':
            start_date = now - timedelta(days=30)
        else:
            start_date = now - timedelta(days=7)
        
        watched = ViewingHistory.objects.filter(watched_at__gte=start_date)
        if media_type != 'all':
            watched = watched.filter(media_type=media_type)
        
        popular = watched.values('tmdb_id', 'media_type', 'title', 'poster_path').annotate(
            watch_count=Count('id')
        ).order_by('-watch_count')[:limit]
        
        favorites = UserFavorites.objects.filter(added_at__gte=start_date)
        if media_type != 'all':
            favorites = favorites.filter(media_type=media_type)
        
        trending_favorites = favorites.values('tmdb_id', 'media_type', 'title', 'poster_path').annotate(
            favorite_count=Count('id')
        ).order_by('-favorite_count')[:limit]
        
        return JsonResponse({
            "period": time_period,
            "media_type": media_type,
            "most_watched": list(popular),
            "most_favorited": list(trending_favorites)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def track_event(request):
    """Track a user analytics event"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        event_type = body.get('event_type')
        user_id = body.get('user_id')
        tmdb_id = body.get('tmdb_id')
        media_type = body.get('media_type', 'movie')
        metadata = body.get('metadata', {})
        
        if not event_type:
            return JsonResponse({"error": "event_type is required"}, status=400)
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                stats, created = UserActivityStats.objects.get_or_create(
                    user=user,
                    defaults={
                        'total_reviews': 0,
                        'total_lists': 0,
                        'total_followers': 0,
                        'total_following': 0,
                        'total_awards_given': 0,
                        'total_awards_received': 0,
                        'total_comments': 0,
                        'user_level': 1,
                        'experience_points': 0,
                    }
                )
                
                xp_rewards = {
                    'view': 1,
                    'watchlist_add': 2,
                    'favorite_add': 3,
                    'review_submit': 10,
                    'comment_add': 5,
                    'list_create': 15,
                    'share': 5,
                }
                
                xp_gain = xp_rewards.get(event_type, 1)
                stats.experience_points += xp_gain
                
                new_level = 1 + (stats.experience_points // 100)
                if new_level > stats.user_level:
                    stats.user_level = new_level
                
                stats.last_activity_at = timezone.now()
                stats.save()
                
            except User.DoesNotExist:
                pass
        
        return JsonResponse({
            "success": True,
            "event_type": event_type,
            "tracked_at": timezone.now().isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_recommendation_metrics(request, user_id):
    """Get recommendation performance metrics for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        recommendations = Recommendation.objects.filter(user=user)
        total_recs = recommendations.count()
        
        interacted = recommendations.filter(user_interacted=True).count()
        positive_feedback = recommendations.filter(user_feedback='positive').count()
        negative_feedback = recommendations.filter(user_feedback='negative').count()
        
        metrics = RecommendationMetrics.objects.filter(user=user)
        
        clicked = metrics.filter(clicked_at__isnull=False).count()
        added_to_watchlist = metrics.filter(added_to_watchlist=True).count()
        actually_watched = metrics.filter(actually_watched=True).count()
        
        avg_effectiveness = metrics.aggregate(avg=Avg('effectiveness_score'))['avg']
        
        by_type = {}
        for rec_type in ['ai', 'collaborative', 'content_based', 'trending', 'similar']:
            type_recs = recommendations.filter(recommendation_type=rec_type)
            type_count = type_recs.count()
            if type_count > 0:
                type_interacted = type_recs.filter(user_interacted=True).count()
                by_type[rec_type] = {
                    "total": type_count,
                    "interacted": type_interacted,
                    "interaction_rate": round(type_interacted / type_count * 100, 1)
                }
        
        return JsonResponse({
            "user_id": user_id,
            "overview": {
                "total_recommendations": total_recs,
                "interacted": interacted,
                "interaction_rate": round(interacted / total_recs * 100, 1) if total_recs > 0 else 0,
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
            },
            "funnel": {
                "recommended": total_recs,
                "clicked": clicked,
                "added_to_watchlist": added_to_watchlist,
                "actually_watched": actually_watched,
            },
            "effectiveness": {
                "average_score": round(avg_effectiveness, 3) if avg_effectiveness else None,
            },
            "by_type": by_type
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET 
def get_platform_stats(request):
    """Get overall platform statistics (admin/dashboard)"""
    try:
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        total_users = User.objects.count()
        active_users_24h = UserActivityStats.objects.filter(
            last_activity_at__gte=last_24h
        ).count()
        active_users_7d = UserActivityStats.objects.filter(
            last_activity_at__gte=last_7d
        ).count()
        
        total_reviews = UserReview.objects.count()
        reviews_24h = UserReview.objects.filter(created_at__gte=last_24h).count()
        
        total_watchlist = UserWatchlist.objects.count()
        total_favorites = UserFavorites.objects.count()
        total_watched = ViewingHistory.objects.count()
        
        total_lists = UserList.objects.count()
        public_lists = UserList.objects.filter(is_public=True).count()
        
        total_follows = UserFollow.objects.count()
        
        avg_user_level = UserActivityStats.objects.aggregate(
            avg=Avg('user_level')
        )['avg']
        
        return JsonResponse({
            "users": {
                "total": total_users,
                "active_24h": active_users_24h,
                "active_7d": active_users_7d,
            },
            "content": {
                "total_reviews": total_reviews,
                "reviews_24h": reviews_24h,
                "watchlist_items": total_watchlist,
                "favorite_items": total_favorites,
                "watched_items": total_watched,
            },
            "social": {
                "total_lists": total_lists,
                "public_lists": public_lists,
                "total_follows": total_follows,
            },
            "gamification": {
                "average_user_level": round(avg_user_level, 1) if avg_user_level else 1,
            },
            "generated_at": now.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
