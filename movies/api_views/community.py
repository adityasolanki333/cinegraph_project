import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.db.models import Count, Avg
from movies.models import (
    UserBadge, UserActivityStats, UserReview, UserList,
    UserFollow, ReviewAward, ReviewComment, ListItem,
    UserSimilarity,
)
from movies.pagination import paginate_queryset

logger = logging.getLogger(__name__)


def _get_user_flexible(user_id):
    try:
        return User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        try:
            return User.objects.get(username=user_id)
        except User.DoesNotExist:
            return None


class UserBadgeProgressView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = _get_user_flexible(user_id)
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        badges = UserBadge.objects.filter(user=user)
        earned_badge_types = set(b.badge_type for b in badges)

        reviews_count = UserReview.objects.filter(user=user).count()
        lists_count = UserList.objects.filter(user=user).count()
        followers_count = UserFollow.objects.filter(following=user).count()

        badge_definitions = [
            {'badgeType': 'first_review', 'name': 'First Review', 'description': 'Write your first review',
             'icon': '⭐', 'requiredValue': 1, 'currentValue': min(reviews_count, 1)},
            {'badgeType': 'review_master', 'name': 'Review Master', 'description': 'Write 50 reviews',
             'icon': '🏆', 'requiredValue': 50, 'currentValue': min(reviews_count, 50)},
            {'badgeType': 'list_creator', 'name': 'List Creator', 'description': 'Create your first list',
             'icon': '📝', 'requiredValue': 1, 'currentValue': min(lists_count, 1)},
            {'badgeType': 'social_butterfly', 'name': 'Social Butterfly', 'description': 'Get 10 followers',
             'icon': '🦋', 'requiredValue': 10, 'currentValue': min(followers_count, 10)},
            {'badgeType': 'movie_buff', 'name': 'Movie Buff', 'description': 'Write 100 reviews',
             'icon': '🎬', 'requiredValue': 100, 'currentValue': min(reviews_count, 100)},
        ]

        badge_progress = []
        for badge in badge_definitions:
            earned = badge['badgeType'] in earned_badge_types or badge['currentValue'] >= badge['requiredValue']
            progress_pct = min(100, int((badge['currentValue'] / badge['requiredValue']) * 100)) if badge['requiredValue'] > 0 else 0
            badge_progress.append({
                'badgeType': badge['badgeType'],
                'name': badge['name'],
                'description': badge['description'],
                'icon': badge['icon'],
                'earned': earned,
                'currentValue': badge['currentValue'],
                'requiredValue': badge['requiredValue'],
                'progressPercentage': progress_pct,
            })

        return Response(badge_progress)


class UserImpactView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = _get_user_flexible(user_id)
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        reviews_count = UserReview.objects.filter(user=user).count()
        avg_rating = UserReview.objects.filter(user=user).aggregate(avg=Avg('rating'))['avg'] or 0
        total_helpful = sum(r.helpful_count for r in UserReview.objects.filter(user=user))
        awards_received = ReviewAward.objects.filter(review__user=user).count()
        comments_received = ReviewComment.objects.filter(review__user=user).count()
        lists_created = UserList.objects.filter(user=user).count()
        list_items = ListItem.objects.filter(list__user=user).count()
        list_followers = sum(lst.follower_count for lst in UserList.objects.filter(user=user))
        followers_count = UserFollow.objects.filter(following=user).count()
        following_count = UserFollow.objects.filter(follower=user).count()

        stats, _ = UserActivityStats.objects.get_or_create(user=user)

        return Response({
            'experiencePoints': stats.experience_points,
            'reviewStats': {
                'totalReviews': reviews_count,
                'averageRatingGiven': round(avg_rating, 1),
                'mostActiveGenre': 'Action',
            },
            'listStats': {
                'totalLists': lists_created,
                'totalListFollowers': list_followers,
                'totalItemsInLists': list_items,
            },
            'socialStats': {
                'followerCount': followers_count,
                'followingCount': following_count,
            },
            'engagementReceived': {
                'totalAwardsReceived': awards_received,
                'totalCommentsReceived': comments_received,
                'totalReviewLikes': total_helpful,
            },
        })


class ActivityStatsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        stats, _ = UserActivityStats.objects.get_or_create(user=user)
        stats.total_reviews = UserReview.objects.filter(user=user).count()
        stats.total_lists = UserList.objects.filter(user=user).count()
        stats.total_followers = user.followers.count()
        stats.total_following = user.following.count()
        stats.total_awards_received = ReviewAward.objects.filter(review__user=user).count()
        stats.total_comments = ReviewComment.objects.filter(user=user).count()
        stats.save()

        return Response({
            'stats': {
                'totalReviews': stats.total_reviews,
                'totalLists': stats.total_lists,
                'totalFollowers': stats.total_followers,
                'totalFollowing': stats.total_following,
                'totalAwardsGiven': stats.total_awards_given,
                'totalAwardsReceived': stats.total_awards_received,
                'totalComments': stats.total_comments,
                'userLevel': stats.user_level,
                'experiencePoints': stats.experience_points,
                'lastActivityAt': stats.last_activity_at.isoformat(),
            }
        })


class UserBadgesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        badges = UserBadge.objects.filter(user=user)
        return Response({
            'badges': [{
                'id': b.id,
                'badgeType': b.badge_type,
                'earnedAt': b.earned_at.isoformat(),
            } for b in badges]
        })


class AwardBadgeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if not request.user.is_staff:
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        try:
            user = User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        badge_type = request.data.get('badgeType', '')
        valid_types = ['first_review', 'review_master', 'list_creator', 'social_butterfly',
                       'movie_buff', 'tv_addict', 'critic', 'curator', 'trendsetter', 'influencer']
        if badge_type not in valid_types:
            return Response({'error': 'Invalid badge type', 'code': 'VALIDATION_ERROR'}, status=400)

        badge, created = UserBadge.objects.get_or_create(user=user, badge_type=badge_type)

        if created:
            stats, _ = UserActivityStats.objects.get_or_create(user=user)
            stats.experience_points += 50
            stats.user_level = stats.calculate_level()
            stats.save()

        return Response({
            'success': True,
            'created': created,
            'badge': {
                'id': badge.id,
                'badgeType': badge.badge_type,
                'earnedAt': badge.earned_at.isoformat(),
            }
        })


class CommunityFeedView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        qs = UserReview.objects.filter(is_public=True).select_related('user').order_by('-created_at')
        reviews, pagination = paginate_queryset(request, qs)

        activities = [{
            'id': r.id,
            'type': 'review',
            'userId': str(r.user.id),
            'userName': r.user.first_name or r.user.email,
            'tmdbId': r.tmdb_id,
            'mediaType': r.media_type,
            'title': r.title,
            'posterPath': r.poster_path,
            'rating': r.rating,
            'review': r.review_text[:200] if r.review_text else '',
            'createdAt': r.created_at.isoformat(),
        } for r in reviews]

        return Response({'activities': activities, **pagination})


class LeaderboardsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        top_reviewers = UserActivityStats.objects.select_related('user', 'user__profile').order_by('-total_reviews')[:10]
        top_followers = UserActivityStats.objects.select_related('user', 'user__profile').order_by('-total_followers')[:10]
        top_lists = UserActivityStats.objects.select_related('user', 'user__profile').order_by('-total_lists')[:10]
        top_awards = UserActivityStats.objects.select_related('user', 'user__profile').order_by('-total_awards_received')[:10]

        def format_user(s, stat_key, stat_val):
            return {
                'userId': str(s.user.id),
                'userLevel': s.user_level,
                stat_key: stat_val,
                'user': {
                    'firstName': s.user.first_name or s.user.username,
                    'lastName': s.user.last_name,
                    'profileImageUrl': s.user.profile.profile_image_url if hasattr(s.user, 'profile') else None
                }
            }

        return Response({
            'topReviewers': [format_user(s, 'totalReviews', s.total_reviews) for s in top_reviewers],
            'topListCreators': [format_user(s, 'totalLists', s.total_lists) for s in top_lists],
            'mostFollowed': [format_user(s, 'totalFollowers', s.total_followers) for s in top_followers],
            'mostAwarded': [format_user(s, 'totalAwardsReceived', s.total_awards_received) for s in top_awards],
        })


class TrendingContentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        trending = UserReview.objects.values('tmdb_id', 'media_type', 'title', 'poster_path').annotate(
            review_count=Count('id'),
            avg_rating=Avg('rating'),
        ).order_by('-review_count')

        paginated_trending, pagination = paginate_queryset(request, trending)

        return Response({
            'data': [{
                'tmdbId': t['tmdb_id'],
                'mediaType': t['media_type'],
                'title': t['title'],
                'posterPath': t['poster_path'],
                'ratingCount': t['review_count'],
                'avgRating': round(t['avg_rating'], 1) if t['avg_rating'] else None,
            } for t in paginated_trending],
            **pagination
        })


class ActivityPromptsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        prompts = [
            {'type': 'review', 'message': 'Share your thoughts on a movie you recently watched!'},
            {'type': 'list', 'message': 'Create a themed movie list to share with others.'},
            {'type': 'follow', 'message': 'Discover and follow other movie enthusiasts.'},
        ]
        return Response({'prompts': prompts, 'userId': user_id})


class SimilarUsersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = _get_user_flexible(user_id)
        if not user:
            return Response({'similarUsers': []})

        similarities = UserSimilarity.objects.filter(user1=user).select_related('user2').order_by('-similarity_score')[:10]

        if not similarities:
            similar = User.objects.exclude(id=user.id).order_by('?')[:5]
            return Response({
                'similarUsers': [{
                    'userId': str(u.id),
                    'userName': u.first_name or u.email,
                    'similarity': 0.5,
                } for u in similar]
            })

        return Response({
            'similarUsers': [{
                'userId': str(s.user2.id),
                'userName': s.user2.first_name or s.user2.email,
                'similarity': s.similarity_score,
                'commonMovies': s.common_movies,
            } for s in similarities]
        })


class PersonalizedFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        user = _get_user_flexible(user_id)
        if not user:
            return Response({'activities': [], 'page': 1, 'limit': 20, 'total': 0, 'totalPages': 1, 'hasMore': False})

        following_ids = UserFollow.objects.filter(follower=user).values_list('following_id', flat=True)

        if following_ids:
            qs = UserReview.objects.filter(
                user_id__in=following_ids, is_public=True
            ).select_related('user').order_by('-created_at')
        else:
            qs = UserReview.objects.filter(is_public=True).select_related('user').order_by('-created_at')

        reviews, pagination = paginate_queryset(request, qs)

        activities = [{
            'id': r.id,
            'type': 'review',
            'userId': str(r.user.id),
            'userName': r.user.first_name or r.user.email,
            'tmdbId': r.tmdb_id,
            'mediaType': r.media_type,
            'title': r.title,
            'posterPath': r.poster_path,
            'rating': r.rating,
            'review': r.review_text[:200] if r.review_text else '',
            'createdAt': r.created_at.isoformat(),
        } for r in reviews]

        return Response({'activities': activities, **pagination})
