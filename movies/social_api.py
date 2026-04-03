import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q
from .models import (
    UserFollow, UserList, ListItem, Notification, UserProfile,
    ReviewComment, ReviewAward, ReviewInteraction, ListFollow,
    UserActivityStats, UserReview, UserRecommendation, RecommendationVote,
    RecommendationComment, NotificationSettings, ListCollaborator, UserBadge
)


def get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


@require_GET
def get_followers(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    followers = UserFollow.objects.filter(following=user).select_related('follower')
    return JsonResponse({
        'followers': [{
            'id': str(f.follower.id),
            'email': f.follower.email,
            'firstName': f.follower.first_name,
            'lastName': f.follower.last_name,
            'followedAt': f.created_at.isoformat(),
        } for f in followers]
    })


@require_GET
def get_following(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    following = UserFollow.objects.filter(follower=user).select_related('following')
    return JsonResponse({
        'following': [{
            'id': str(f.following.id),
            'email': f.following.email,
            'firstName': f.following.first_name,
            'lastName': f.following.last_name,
            'followedAt': f.created_at.isoformat(),
        } for f in following]
    })


@csrf_exempt
@require_POST
def follow_user(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        target_user_id = data.get('targetUserId')
        
        if not target_user_id:
            return JsonResponse({'error': 'targetUserId is required'}, status=400)
        
        target_user = get_user_or_404(target_user_id)
        if not target_user:
            return JsonResponse({'error': 'Target user not found'}, status=404)
        
        if request.user.id == target_user.id:
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        
        follow, created = UserFollow.objects.get_or_create(
            follower=request.user,
            following=target_user
        )
        
        if created:
            Notification.objects.create(
                user=target_user,
                notification_type='follow',
                message=f'{request.user.first_name or request.user.email} started following you',
                related_user_id=request.user.id
            )
        
        return JsonResponse({'success': True, 'created': created})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def unfollow_user(request, user_id, target_user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    deleted, _ = UserFollow.objects.filter(
        follower=request.user,
        following_id=target_user_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def is_following(request, user_id, target_user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'isFollowing': False})
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'isFollowing': False})
    
    exists = UserFollow.objects.filter(
        follower=request.user,
        following_id=target_user_id
    ).exists()
    
    return JsonResponse({'isFollowing': exists})


@require_GET
def get_user_lists(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    lists = UserList.objects.filter(user=user)
    if not request.user.is_authenticated or request.user.id != user.id:
        lists = lists.filter(is_public=True)
    
    return JsonResponse({
        'lists': [{
            'id': lst.id,
            'title': lst.title,
            'description': lst.description,
            'isPublic': lst.is_public,
            'followerCount': lst.follower_count,
            'itemCount': lst.items.count(),
            'createdAt': lst.created_at.isoformat(),
            'updatedAt': lst.updated_at.isoformat(),
            'user': {
                'id': str(user.id),
                'firstName': user.first_name,
                'lastName': user.last_name,
            }
        } for lst in lists]
    })


@require_GET
def get_public_lists(request):
    """Return all public curated lists, ordered by follower count."""
    from django.db.models import Count
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'popular')
    offset = int(request.GET.get('offset', 0))
    limit = min(int(request.GET.get('limit', 24)), 50)

    lists = UserList.objects.filter(is_public=True).select_related('user')
    if q:
        lists = lists.filter(Q(title__icontains=q) | Q(description__icontains=q))

    if sort == 'newest':
        lists = lists.order_by('-created_at')
    elif sort == 'most_items':
        lists = lists.annotate(item_cnt=Count('items')).order_by('-item_cnt')
    else:
        lists = lists.order_by('-follower_count', '-created_at')

    total = lists.count()
    lists = lists[offset:offset + limit]

    return JsonResponse({
        'lists': [{
            'id': lst.id,
            'title': lst.title,
            'description': lst.description,
            'followerCount': lst.follower_count,
            'itemCount': lst.items.count(),
            'createdAt': lst.created_at.isoformat(),
            'user': {
                'id': str(lst.user.id),
                'firstName': lst.user.first_name or lst.user.username,
                'lastName': lst.user.last_name,
            }
        } for lst in lists],
        'total': total,
        'offset': offset,
        'hasMore': offset + limit < total,
    })


@require_GET
def get_list_detail(request, list_id):
    try:
        lst = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    if not lst.is_public:
        if not request.user.is_authenticated or request.user.id != lst.user.id:
            return JsonResponse({'error': 'Not authorized'}, status=403)
    
    items = ListItem.objects.filter(list=lst)
    
    return JsonResponse({
        'list': {
            'id': lst.id,
            'title': lst.title,
            'description': lst.description,
            'isPublic': lst.is_public,
            'followerCount': lst.follower_count,
            'createdAt': lst.created_at.isoformat(),
            'updatedAt': lst.updated_at.isoformat(),
            'user': {
                'id': str(lst.user.id),
                'firstName': lst.user.first_name,
                'lastName': lst.user.last_name,
            },
            'items': [{
                'id': item.id,
                'tmdbId': item.tmdb_id,
                'mediaType': item.media_type,
                'title': item.title,
                'posterPath': item.poster_path,
                'note': item.note,
                'position': item.position,
                'addedAt': item.added_at.isoformat(),
            } for item in items]
        }
    })


@csrf_exempt
@require_POST
def create_list(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        description = data.get('description', '')
        is_public = data.get('isPublic', True)
        
        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)
        
        lst = UserList.objects.create(
            user=request.user,
            title=title,
            description=description,
            is_public=is_public
        )
        
        return JsonResponse({
            'success': True,
            'list': {
                'id': lst.id,
                'title': lst.title,
                'description': lst.description,
                'isPublic': lst.is_public,
                'createdAt': lst.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def update_list(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        lst = UserList.objects.get(id=list_id, user=request.user)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found or not authorized'}, status=404)
    
    try:
        data = json.loads(request.body)
        if 'title' in data:
            lst.title = data['title']
        if 'description' in data:
            lst.description = data['description']
        if 'isPublic' in data:
            lst.is_public = data['isPublic']
        lst.save()
        
        return JsonResponse({
            'success': True,
            'list': {
                'id': lst.id,
                'title': lst.title,
                'description': lst.description,
                'isPublic': lst.is_public,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_list(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    deleted, _ = UserList.objects.filter(
        id=list_id,
        user=request.user
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@csrf_exempt
@require_POST
def add_list_item(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        lst = UserList.objects.get(id=list_id, user=request.user)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found or not authorized'}, status=404)
    
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        note = data.get('note', '')
        
        if not tmdb_id:
            return JsonResponse({'error': 'tmdbId is required'}, status=400)
        
        max_position = ListItem.objects.filter(list=lst).count()
        
        item, created = ListItem.objects.get_or_create(
            list=lst,
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={
                'title': title,
                'poster_path': poster_path,
                'note': note,
                'position': max_position
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'item': {
                'id': item.id,
                'tmdbId': item.tmdb_id,
                'mediaType': item.media_type,
                'title': item.title,
                'posterPath': item.poster_path,
                'note': item.note,
                'position': item.position,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_list_item(request, list_id, item_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        lst = UserList.objects.get(id=list_id, user=request.user)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found or not authorized'}, status=404)
    
    deleted, _ = ListItem.objects.filter(
        list=lst,
        id=item_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_notifications(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    notifications = Notification.objects.filter(user=request.user)[:50]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    return JsonResponse({
        'notifications': [{
            'id': n.id,
            'type': n.notification_type,
            'message': n.message,
            'relatedUserId': n.related_user_id,
            'relatedTmdbId': n.related_tmdb_id,
            'relatedMediaType': n.related_media_type,
            'isRead': n.is_read,
            'createdAt': n.created_at.isoformat(),
        } for n in notifications],
        'unreadCount': unread_count
    })


@csrf_exempt
@require_POST
def mark_notifications_read(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        notification_ids = data.get('notificationIds', [])
        
        if notification_ids:
            Notification.objects.filter(
                user=request.user,
                id__in=notification_ids
            ).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user).update(is_read=True)
        
        return JsonResponse({'success': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def notifications_unread_count(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})
    
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@require_GET
def lists_containing_content(request, tmdb_id, media_type):
    lists_with_content = ListItem.objects.filter(
        tmdb_id=tmdb_id,
        media_type=media_type,
        list__is_public=True
    ).select_related('list', 'list__user')[:10]
    
    return JsonResponse({
        'lists': [{
            'id': item.list.id,
            'title': item.list.title,
            'description': item.list.description,
            'itemCount': item.list.items.count(),
            'user': {
                'id': str(item.list.user.id),
                'firstName': item.list.user.first_name,
                'lastName': item.list.user.last_name,
            }
        } for item in lists_with_content]
    })


@require_GET
def get_sentiment(request, tmdb_id, media_type):
    from .models import UserReview
    from django.db.models import Avg, Count
    
    reviews = UserReview.objects.filter(
        tmdb_id=tmdb_id,
        media_type=media_type,
        is_public=True
    )
    
    stats = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_reviews=Count('id')
    )
    
    positive = reviews.filter(rating__gte=7).count()
    negative = reviews.filter(rating__lte=4).count()
    neutral = reviews.filter(rating__gt=4, rating__lt=7).count()
    
    avg_rating = stats['avg_rating'] or 0
    sentiment_score = (avg_rating - 5) / 5 if avg_rating else 0
    
    return JsonResponse({
        'tmdbId': tmdb_id,
        'mediaType': media_type,
        'avgSentimentScore': round(sentiment_score, 2),
        'totalReviews': stats['total_reviews'],
        'positiveCount': positive,
        'negativeCount': negative,
        'neutralCount': neutral,
        'avgRating': round(avg_rating, 1) if avg_rating else None
    })


@csrf_exempt
def get_ratings(request):
    """Handle GET for retrieving ratings and POST for creating ratings"""
    if request.method == 'POST':
        return create_rating(request)
    
    # GET request - retrieve ratings
    tmdb_id = request.GET.get('tmdbId')
    media_type = request.GET.get('mediaType', 'movie')
    
    if not tmdb_id:
        return JsonResponse({'error': 'tmdbId required'}, status=400)
    
    reviews = UserReview.objects.filter(
        tmdb_id=tmdb_id,
        media_type=media_type,
        is_public=True
    ).select_related('user').order_by('-created_at')
    
    reviews_list = []
    for review in reviews:
        reviews_list.append({
            'id': review.id,
            'userId': review.user.id,
            'username': review.user.first_name or review.user.email.split('@')[0],
            'tmdbId': review.tmdb_id,
            'mediaType': review.media_type,
            'title': review.title,
            'rating': review.rating,
            'review': review.review_text,
            'helpfulCount': review.helpful_count,
            'createdAt': review.created_at.isoformat()
        })
    
    return JsonResponse(reviews_list, safe=False)


@csrf_exempt
@require_POST
def create_rating(request):
    """Create or update a rating/review for a movie or TV show"""
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        rating = data.get('rating')
        review_text = data.get('reviewText', '')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        
        if not tmdb_id or rating is None:
            return JsonResponse({'error': 'tmdbId and rating are required'}, status=400)
        
        # For demo mode, use demo user
        if not request.user.is_authenticated:
            try:
                demo_user = User.objects.get(username='demo_user')
            except User.DoesNotExist:
                demo_user = User.objects.create_user(
                    username='demo_user',
                    email='demo@cinesuggest.com',
                    password='demo123'
                )
            user = demo_user
        else:
            user = request.user
        
        # Create or update the review
        review, created = UserReview.objects.update_or_create(
            user=user,
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={
                'rating': rating,
                'review_text': review_text,
                'title': title,
                'poster_path': poster_path,
                'is_public': True
            }
        )
        
        return JsonResponse({
            'id': review.id,
            'tmdbId': review.tmdb_id,
            'mediaType': review.media_type,
            'rating': review.rating,
            'review': review.review_text,
            'title': review.title,
            'createdAt': review.created_at.isoformat(),
            'created': created
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
def manage_rating(request, review_id):
    """Get, update or delete a specific rating/review by its ID."""
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Rating not found'}, status=404)

    if request.method == "GET":
        return JsonResponse({
            'id': review.id,
            'tmdbId': review.tmdb_id,
            'mediaType': review.media_type,
            'title': review.title,
            'rating': review.rating,
            'review': review.review_text,
            'isPublic': review.is_public,
            'helpfulCount': review.helpful_count,
            'createdAt': review.created_at.isoformat(),
            'user': {
                'id': str(review.user.id),
                'firstName': review.user.first_name,
                'lastName': review.user.last_name,
            }
        })

    # Mutations require ownership
    if not request.user.is_authenticated:
        try:
            acting_user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        acting_user = request.user

    if review.user != acting_user:
        return JsonResponse({'error': 'Not authorized'}, status=403)

    if request.method == "DELETE":
        review.delete()
        return JsonResponse({'success': True, 'deleted': True})

    # PATCH / PUT — update rating and/or review text
    try:
        data = json.loads(request.body)
        if 'rating' in data:
            review.rating = data['rating']
        if 'reviewText' in data:
            review.review_text = data['reviewText']
        if 'isPublic' in data:
            review.is_public = data['isPublic']
        review.save()
        return JsonResponse({
            'success': True,
            'id': review.id,
            'rating': review.rating,
            'review': review.review_text,
            'isPublic': review.is_public,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def get_review_comments(request, review_id):
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    if request.method == "GET":
        comments = ReviewComment.objects.filter(review=review, parent_comment__isnull=True).select_related('user')
        
        def serialize_comment(comment):
            replies = ReviewComment.objects.filter(parent_comment=comment).select_related('user')
            return {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
                'replies': [serialize_comment(r) for r in replies]
            }
        
        return JsonResponse({
            'comments': [serialize_comment(c) for c in comments]
        })
    
    # POST - add a new comment
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        data = json.loads(request.body)
        comment_text = (data.get('comment') or data.get('content') or '').strip()
        parent_id = data.get('parentCommentId')
        
        if not comment_text:
            return JsonResponse({'error': 'Comment is required'}, status=400)
        
        parent_comment = None
        if parent_id:
            try:
                parent_comment = ReviewComment.objects.get(id=parent_id)
            except ReviewComment.DoesNotExist:
                pass
        
        comment = ReviewComment.objects.create(
            user=user,
            review=review,
            comment=comment_text,
            parent_comment=parent_comment
        )
        
        if review.user != user:
            Notification.objects.create(
                user=review.user,
                notification_type='comment',
                message=f'{user.first_name or user.email} commented on your review',
                related_user_id=user.id,
                related_tmdb_id=review.tmdb_id,
                related_media_type=review.media_type
            )
        
        stats, _ = UserActivityStats.objects.get_or_create(user=user)
        stats.total_comments += 1
        stats.experience_points += 5
        stats.user_level = stats.calculate_level()
        stats.save()
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_POST
def add_review_comment(request, review_id):
    # Support demo user for unauthenticated requests
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        comment_text = (data.get('comment') or data.get('content') or '').strip()
        parent_id = data.get('parentCommentId')
        
        if not comment_text:
            return JsonResponse({'error': 'Comment is required'}, status=400)
        
        parent_comment = None
        if parent_id:
            try:
                parent_comment = ReviewComment.objects.get(id=parent_id)
            except ReviewComment.DoesNotExist:
                pass
        
        comment = ReviewComment.objects.create(
            user=user,
            review=review,
            comment=comment_text,
            parent_comment=parent_comment
        )
        
        if review.user != user:
            Notification.objects.create(
                user=review.user,
                notification_type='comment',
                message=f'{user.first_name or user.email} commented on your review',
                related_user_id=user.id,
                related_tmdb_id=review.tmdb_id,
                related_media_type=review.media_type
            )
        
        stats, _ = UserActivityStats.objects.get_or_create(user=user)
        stats.total_comments += 1
        stats.experience_points += 5
        stats.user_level = stats.calculate_level()
        stats.save()
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def get_review_awards(request, review_id):
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    if request.method == "GET":
        awards = ReviewAward.objects.filter(review=review).select_related('user')
        award_counts = awards.values('award_type').annotate(count=Count('id'))
        
        return JsonResponse({
            'awards': [{
                'id': a.id,
                'awardType': a.award_type,
                'userId': str(a.user.id),
                'userName': f"{a.user.first_name} {a.user.last_name}".strip() or a.user.email,
                'createdAt': a.created_at.isoformat(),
            } for a in awards],
            'counts': {item['award_type']: item['count'] for item in award_counts}
        })
    
    # POST - give a new award
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    if review.user == user:
        return JsonResponse({'error': 'Cannot give awards to your own review'}, status=400)
    
    try:
        data = json.loads(request.body)
        award_type = data.get('awardType', '').lower()
        
        valid_types = ['outstanding', 'perfect', 'great', 'helpful', 'insightful', 'funny']
        if award_type not in valid_types:
            return JsonResponse({'error': f'Invalid award type. Must be one of: {", ".join(valid_types)}'}, status=400)
        
        award, created = ReviewAward.objects.get_or_create(
            user=user,
            review=review,
            award_type=award_type
        )
        
        if created and review.user != user:
            Notification.objects.create(
                user=review.user,
                notification_type='like',
                message=f'{user.first_name or user.email} gave your review a "{award_type}" award',
                related_user_id=user.id,
                related_tmdb_id=review.tmdb_id,
                related_media_type=review.media_type
            )
            
            giver_stats, _ = UserActivityStats.objects.get_or_create(user=user)
            giver_stats.total_awards_given += 1
            giver_stats.experience_points += 2
            giver_stats.save()
            
            receiver_stats, _ = UserActivityStats.objects.get_or_create(user=review.user)
            receiver_stats.total_awards_received += 1
            receiver_stats.experience_points += 10
            receiver_stats.user_level = receiver_stats.calculate_level()
            receiver_stats.save()
        
        return JsonResponse({
            'success': True,
            'created': created,
            'award': {
                'id': award.id,
                'awardType': award.award_type,
                'createdAt': award.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_user_awards_for_review(request, review_id):
    """Get awards the current user has given to a specific review"""
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    # For demo mode, use demo user
    if not request.user.is_authenticated:
        try:
            demo_user = User.objects.get(username='demo_user')
            user = demo_user
        except User.DoesNotExist:
            return JsonResponse({'userAwards': []})
    else:
        user = request.user
    
    user_awards = ReviewAward.objects.filter(review=review, user=user)
    
    return JsonResponse({
        'userAwards': [a.award_type for a in user_awards]
    })


@csrf_exempt
@require_POST
def give_review_award(request, review_id):
    # Support demo user for unauthenticated requests
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    if review.user == user:
        return JsonResponse({'error': 'Cannot give awards to your own review'}, status=400)
    
    try:
        data = json.loads(request.body)
        award_type = data.get('awardType', '').lower()
        
        valid_types = ['outstanding', 'perfect', 'great', 'helpful', 'insightful', 'funny']
        if award_type not in valid_types:
            return JsonResponse({'error': f'Invalid award type. Must be one of: {", ".join(valid_types)}'}, status=400)
        
        award, created = ReviewAward.objects.get_or_create(
            user=user,
            review=review,
            award_type=award_type
        )
        
        if created and review.user != user:
            Notification.objects.create(
                user=review.user,
                notification_type='like',
                message=f'{user.first_name or user.email} gave your review a "{award_type}" award',
                related_user_id=user.id,
                related_tmdb_id=review.tmdb_id,
                related_media_type=review.media_type
            )
            
            giver_stats, _ = UserActivityStats.objects.get_or_create(user=user)
            giver_stats.total_awards_given += 1
            giver_stats.experience_points += 2
            giver_stats.save()
            
            receiver_stats, _ = UserActivityStats.objects.get_or_create(user=review.user)
            receiver_stats.total_awards_received += 1
            receiver_stats.experience_points += 10
            receiver_stats.user_level = receiver_stats.calculate_level()
            receiver_stats.save()
        
        return JsonResponse({
            'success': True,
            'created': created,
            'award': {
                'id': award.id,
                'awardType': award.award_type,
                'createdAt': award.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_POST
def mark_review_helpful(request, review_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return JsonResponse({'error': 'Review not found'}, status=404)
    
    if review.user == request.user:
        return JsonResponse({'error': 'Cannot vote on your own review'}, status=400)
    
    try:
        data = json.loads(request.body)
        is_helpful = data.get('isHelpful', True)
        interaction_type = 'helpful' if is_helpful else 'not_helpful'
        opposite_type = 'not_helpful' if is_helpful else 'helpful'
        
        existing = ReviewInteraction.objects.filter(user=request.user, review=review).first()
        
        if existing:
            if existing.interaction_type == interaction_type:
                existing.delete()
                if interaction_type == 'helpful':
                    review.helpful_count = max(0, review.helpful_count - 1)
                    review.save()
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'helpfulCount': review.helpful_count
                })
            else:
                if existing.interaction_type == 'helpful':
                    review.helpful_count = max(0, review.helpful_count - 1)
                existing.interaction_type = interaction_type
                existing.save()
                if interaction_type == 'helpful':
                    review.helpful_count += 1
                review.save()
                return JsonResponse({
                    'success': True,
                    'action': 'changed',
                    'helpfulCount': review.helpful_count
                })
        else:
            ReviewInteraction.objects.create(
                user=request.user,
                review=review,
                interaction_type=interaction_type
            )
            if is_helpful:
                review.helpful_count += 1
                review.save()
            return JsonResponse({
                'success': True,
                'action': 'created',
                'helpfulCount': review.helpful_count
            })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_POST
def follow_list(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_list = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    if not user_list.is_public and user_list.user != request.user:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    if user_list.user == request.user:
        return JsonResponse({'error': 'Cannot follow your own list'}, status=400)
    
    follow, created = ListFollow.objects.get_or_create(
        user=request.user,
        list=user_list
    )
    
    if created:
        actual_count = ListFollow.objects.filter(list=user_list).count()
        user_list.follower_count = actual_count
        user_list.save()
        
        Notification.objects.create(
            user=user_list.user,
            notification_type='list_follow',
            message=f'{request.user.first_name or request.user.email} started following your list "{user_list.title}"',
            related_user_id=request.user.id
        )
    
    return JsonResponse({
        'success': True,
        'created': created,
        'followerCount': user_list.follower_count
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def unfollow_list(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        user_list = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    deleted, _ = ListFollow.objects.filter(
        user=request.user,
        list=user_list
    ).delete()
    
    if deleted:
        actual_count = ListFollow.objects.filter(list=user_list).count()
        user_list.follower_count = actual_count
        user_list.save()
    
    return JsonResponse({
        'success': True,
        'deleted': deleted > 0,
        'followerCount': user_list.follower_count
    })


@require_GET
def get_list_followers(request, list_id):
    try:
        user_list = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    followers = ListFollow.objects.filter(list=user_list).select_related('user')
    
    return JsonResponse({
        'followers': [{
            'id': str(f.user.id),
            'email': f.user.email,
            'firstName': f.user.first_name,
            'lastName': f.user.last_name,
            'followedAt': f.created_at.isoformat(),
        } for f in followers]
    })


@require_GET
def get_activity_stats(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    stats, _ = UserActivityStats.objects.get_or_create(user=user)
    
    stats.total_reviews = UserReview.objects.filter(user=user).count()
    stats.total_lists = UserList.objects.filter(user=user).count()
    stats.total_followers = user.followers.count()
    stats.total_following = user.following.count()
    stats.total_awards_received = ReviewAward.objects.filter(review__user=user).count()
    stats.total_comments = ReviewComment.objects.filter(user=user).count()
    stats.save()
    
    return JsonResponse({
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


@csrf_exempt
@require_POST
def submit_user_recommendation(request, user_id=None):
    # Support demo user for unauthenticated requests
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        data = json.loads(request.body)
        for_tmdb_id = data.get('forTmdbId')
        for_media_type = data.get('forMediaType', 'movie')
        recommended_tmdb_id = data.get('recommendedTmdbId')
        recommended_media_type = data.get('recommendedMediaType', 'movie')
        recommended_title = data.get('recommendedTitle', '')
        recommended_poster_path = data.get('recommendedPosterPath', '')
        reason = data.get('reason', '')
        
        if not for_tmdb_id or not recommended_tmdb_id:
            return JsonResponse({'error': 'forTmdbId and recommendedTmdbId are required'}, status=400)
        
        rec = UserRecommendation.objects.create(
            user=user,
            for_tmdb_id=for_tmdb_id,
            for_media_type=for_media_type,
            recommended_tmdb_id=recommended_tmdb_id,
            recommended_media_type=recommended_media_type,
            recommended_title=recommended_title,
            recommended_poster_path=recommended_poster_path,
            reason=reason
        )
        
        stats, _ = UserActivityStats.objects.get_or_create(user=user)
        stats.experience_points += 15
        stats.user_level = stats.calculate_level()
        stats.save()
        
        return JsonResponse({
            'success': True,
            'recommendation': {
                'id': rec.id,
                'forTmdbId': rec.for_tmdb_id,
                'recommendedTmdbId': rec.recommended_tmdb_id,
                'recommendedTitle': rec.recommended_title,
                'reason': rec.reason,
                'createdAt': rec.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_user_recommendations_for_content(request, tmdb_id, media_type):
    # Get current user for checking their votes
    current_user = None
    user_id = request.GET.get('userId')
    if request.user.is_authenticated:
        current_user = request.user
    elif user_id:
        try:
            current_user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            pass
    
    from django.db.models import Count, Q
    
    recs = UserRecommendation.objects.filter(
        for_tmdb_id=tmdb_id,
        for_media_type=media_type
    ).select_related('user').annotate(
        like_count_db=Count('votes', filter=Q(votes__vote_type='like')),
        dislike_count_db=Count('votes', filter=Q(votes__vote_type='dislike'))
    ).order_by('-like_count_db', 'dislike_count_db', '-created_at')[:20]
    
    result = []
    for r in recs:
        user_vote = None
        if current_user:
            try:
                vote = RecommendationVote.objects.get(recommendation=r, user=current_user)
                user_vote = vote.vote_type
            except RecommendationVote.DoesNotExist:
                pass
        
        result.append({
            'id': r.id,
            'userId': str(r.user.id),
            'userName': f"{r.user.first_name} {r.user.last_name}".strip() or r.user.email,
            'recommendedTmdbId': r.recommended_tmdb_id,
            'recommendedMediaType': r.recommended_media_type,
            'recommendedTitle': r.recommended_title,
            'recommendedPosterPath': r.recommended_poster_path,
            'reason': r.reason,
            'likeCount': r.votes.filter(vote_type='like').count(),
            'dislikeCount': r.votes.filter(vote_type='dislike').count(),
            'userVote': user_vote,
            'createdAt': r.created_at.isoformat(),
        })
    
    return JsonResponse({'recommendations': result})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_user_recommendation(request, user_id, recommendation_id):
    """Delete a user recommendation"""
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id, user=user)
        rec.delete()
        return JsonResponse({'success': True})
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def user_recommendation_comments(request, user_id, recommendation_id):
    """Get or add comments for a recommendation"""
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id)
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    if request.method == "GET":
        comments = RecommendationComment.objects.filter(recommendation=rec).select_related('user')
        return JsonResponse({
            'comments': [{
                'id': c.id,
                'userId': str(c.user.id),
                'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
                'comment': c.comment,
                'createdAt': c.created_at.isoformat(),
            } for c in comments]
        })
    
    # POST - add comment
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        data = json.loads(request.body)
        comment_text = (data.get('comment') or data.get('content') or '').strip()
        
        if not comment_text:
            return JsonResponse({'error': 'Comment is required'}, status=400)
        
        comment = RecommendationComment.objects.create(
            user=user,
            recommendation=rec,
            comment=comment_text
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_POST
def user_recommendation_vote(request, user_id, recommendation_id):
    """Vote on a recommendation"""
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id)
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        vote_type = data.get('voteType', '').lower()
        
        if vote_type not in ['like', 'dislike']:
            return JsonResponse({'error': 'voteType must be "like" or "dislike"'}, status=400)
        
        vote, created = RecommendationVote.objects.update_or_create(
            user=user,
            recommendation=rec,
            defaults={'vote_type': vote_type}
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'voteType': vote.vote_type
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_review_comment(request, review_id, comment_id):
    """Delete a review comment"""
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        comment = ReviewComment.objects.get(id=comment_id, review_id=review_id, user=user)
        comment.delete()
        return JsonResponse({'success': True})
    except ReviewComment.DoesNotExist:
        return JsonResponse({'error': 'Comment not found'}, status=404)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_review_award(request, review_id, award_id):
    """Delete a review award"""
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
    else:
        user = request.user
    
    try:
        award = ReviewAward.objects.get(id=award_id, review_id=review_id, user=user)
        award.delete()
        return JsonResponse({'success': True})
    except ReviewAward.DoesNotExist:
        return JsonResponse({'error': 'Award not found'}, status=404)


@csrf_exempt
@require_POST
def vote_on_recommendation(request, recommendation_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id)
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        vote_type = data.get('voteType', '').lower()
        
        if vote_type not in ['like', 'dislike']:
            return JsonResponse({'error': 'voteType must be "like" or "dislike"'}, status=400)
        
        vote, created = RecommendationVote.objects.update_or_create(
            user=request.user,
            recommendation=rec,
            defaults={'vote_type': vote_type}
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'voteType': vote.vote_type
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_recommendation_comments(request, recommendation_id):
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id)
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    comments = RecommendationComment.objects.filter(recommendation=rec).select_related('user')
    
    return JsonResponse({
        'comments': [{
            'id': c.id,
            'userId': str(c.user.id),
            'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
            'comment': c.comment,
            'createdAt': c.created_at.isoformat(),
        } for c in comments]
    })


@csrf_exempt
@require_POST
def add_recommendation_comment(request, recommendation_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        rec = UserRecommendation.objects.get(id=recommendation_id)
    except UserRecommendation.DoesNotExist:
        return JsonResponse({'error': 'Recommendation not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        comment_text = (data.get('comment') or data.get('content') or '').strip()
        
        if not comment_text:
            return JsonResponse({'error': 'Comment is required'}, status=400)
        
        comment = RecommendationComment.objects.create(
            user=request.user,
            recommendation=rec,
            comment=comment_text
        )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_notification_settings(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    settings, _ = NotificationSettings.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        'settings': {
            'emailNotifications': settings.email_notifications,
            'pushNotifications': settings.push_notifications,
            'followNotifications': settings.follow_notifications,
            'likeNotifications': settings.like_notifications,
            'commentNotifications': settings.comment_notifications,
            'recommendationNotifications': settings.recommendation_notifications,
            'listNotifications': settings.list_notifications,
        }
    })


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_notification_settings(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    settings, _ = NotificationSettings.objects.get_or_create(user=request.user)
    
    try:
        data = json.loads(request.body)
        
        if 'emailNotifications' in data:
            settings.email_notifications = data['emailNotifications']
        if 'pushNotifications' in data:
            settings.push_notifications = data['pushNotifications']
        if 'followNotifications' in data:
            settings.follow_notifications = data['followNotifications']
        if 'likeNotifications' in data:
            settings.like_notifications = data['likeNotifications']
        if 'commentNotifications' in data:
            settings.comment_notifications = data['commentNotifications']
        if 'recommendationNotifications' in data:
            settings.recommendation_notifications = data['recommendationNotifications']
        if 'listNotifications' in data:
            settings.list_notifications = data['listNotifications']
        
        settings.save()
        
        return JsonResponse({
            'success': True,
            'settings': {
                'emailNotifications': settings.email_notifications,
                'pushNotifications': settings.push_notifications,
                'followNotifications': settings.follow_notifications,
                'likeNotifications': settings.like_notifications,
                'commentNotifications': settings.comment_notifications,
                'recommendationNotifications': settings.recommendation_notifications,
                'listNotifications': settings.list_notifications,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_list_collaborators(request, list_id):
    try:
        lst = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)
    
    collaborators = ListCollaborator.objects.filter(list=lst).select_related('user')
    
    return JsonResponse({
        'collaborators': [{
            'id': c.id,
            'userId': str(c.user.id),
            'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
            'email': c.user.email,
            'permission': c.permission,
            'accepted': c.accepted,
            'invitedAt': c.invited_at.isoformat(),
        } for c in collaborators]
    })


@csrf_exempt
@require_POST
def invite_list_collaborator(request, list_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        lst = UserList.objects.get(id=list_id, user=request.user)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found or not authorized'}, status=404)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        permission = data.get('permission', 'view')
        
        if not user_id:
            return JsonResponse({'error': 'userId is required'}, status=400)
        
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
        
        if target_user == request.user:
            return JsonResponse({'error': 'Cannot invite yourself'}, status=400)
        
        collaborator, created = ListCollaborator.objects.get_or_create(
            list=lst,
            user=target_user,
            defaults={'permission': permission}
        )
        
        if not created:
            collaborator.permission = permission
            collaborator.save()
        
        Notification.objects.create(
            user=target_user,
            notification_type='list_follow',
            message=f'{request.user.first_name or request.user.email} invited you to collaborate on "{lst.title}"',
            related_user_id=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'collaborator': {
                'id': collaborator.id,
                'userId': str(collaborator.user.id),
                'permission': collaborator.permission,
                'accepted': collaborator.accepted,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_list_collaborator(request, list_id, collaborator_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        lst = UserList.objects.get(id=list_id, user=request.user)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found or not authorized'}, status=404)
    
    deleted, _ = ListCollaborator.objects.filter(
        list=lst,
        id=collaborator_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_user_badges(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    badges = UserBadge.objects.filter(user=user)
    
    return JsonResponse({
        'badges': [{
            'id': b.id,
            'badgeType': b.badge_type,
            'earnedAt': b.earned_at.isoformat(),
        } for b in badges]
    })


@csrf_exempt
@require_POST
def award_badge(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if not request.user.is_staff:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    try:
        data = json.loads(request.body)
        badge_type = data.get('badgeType', '')
        
        valid_types = ['first_review', 'review_master', 'list_creator', 'social_butterfly', 
                      'movie_buff', 'tv_addict', 'critic', 'curator', 'trendsetter', 'influencer']
        if badge_type not in valid_types:
            return JsonResponse({'error': f'Invalid badge type'}, status=400)
        
        badge, created = UserBadge.objects.get_or_create(
            user=user,
            badge_type=badge_type
        )
        
        if created:
            stats, _ = UserActivityStats.objects.get_or_create(user=user)
            stats.experience_points += 50
            stats.user_level = stats.calculate_level()
            stats.save()
        
        return JsonResponse({
            'success': True,
            'created': created,
            'badge': {
                'id': badge.id,
                'badgeType': badge.badge_type,
                'earnedAt': badge.earned_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


def check_and_award_badges(user):
    stats, _ = UserActivityStats.objects.get_or_create(user=user)
    
    if stats.total_reviews >= 1:
        UserBadge.objects.get_or_create(user=user, badge_type='first_review')
    
    if stats.total_reviews >= 50:
        UserBadge.objects.get_or_create(user=user, badge_type='review_master')
    
    if stats.total_lists >= 5:
        UserBadge.objects.get_or_create(user=user, badge_type='list_creator')
    
    if stats.total_followers >= 10:
        UserBadge.objects.get_or_create(user=user, badge_type='social_butterfly')
    
    if stats.total_followers >= 100:
        UserBadge.objects.get_or_create(user=user, badge_type='influencer')


@require_GET
def get_top_reviews(request):
    time_filter = request.GET.get('timeFilter', 'weekly')
    sort_by = request.GET.get('sortBy', 'awards')
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 20))
    
    reviews = UserReview.objects.filter(is_public=True).select_related('user')
    
    if sort_by == 'awards':
        reviews = reviews.annotate(award_count=Count('awards')).order_by('-award_count', '-created_at')
    elif sort_by == 'helpful':
        reviews = reviews.order_by('-helpful_count', '-created_at')
    else:
        reviews = reviews.order_by('-created_at')
    
    reviews = reviews[offset:offset + limit]
    
    return JsonResponse({
        'reviews': [{
            'id': r.id,
            'userId': str(r.user.id),
            'userName': r.user.first_name or r.user.email,
            'tmdbId': r.tmdb_id,
            'mediaType': r.media_type,
            'title': r.title,
            'posterPath': r.poster_path,
            'rating': r.rating,
            'review': r.review_text,
            'helpfulCount': r.helpful_count,
            'awardCount': getattr(r, 'award_count', r.awards.count()),
            'createdAt': r.created_at.isoformat(),
        } for r in reviews],
        'offset': offset,
        'hasMore': len(reviews) == limit
    })


@require_GET
def get_community_feed(request):
    time_filter = request.GET.get('timeFilter', 'weekly')
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 20))
    
    reviews = UserReview.objects.filter(is_public=True).select_related('user').order_by('-created_at')[offset:offset + limit]
    
    activities = []
    for r in reviews:
        activities.append({
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
        })
    
    return JsonResponse({
        'activities': activities,
        'offset': offset,
        'hasMore': len(reviews) == limit
    })


@require_GET
def get_leaderboards(request):
    top_reviewers = UserActivityStats.objects.order_by('-total_reviews')[:10]
    top_followers = UserActivityStats.objects.order_by('-total_followers')[:10]
    top_lists = UserActivityStats.objects.order_by('-total_lists')[:10]
    top_awards_received = UserActivityStats.objects.order_by('-total_awards_received')[:10]
    
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

    return JsonResponse({
        'topReviewers': [format_user(s, 'totalReviews', s.total_reviews) for s in top_reviewers],
        'topListCreators': [format_user(s, 'totalLists', s.total_lists) for s in top_lists],
        'mostFollowed': [format_user(s, 'totalFollowers', s.total_followers) for s in top_followers],
        'mostAwarded': [format_user(s, 'totalAwardsReceived', s.total_awards_received) for s in top_awards_received],
    })


@require_GET
def get_trending_content(request):
    time_filter = request.GET.get('timeFilter', 'weekly')
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 20))
    
    from django.db.models import Count, Avg as DbAvg
    trending = UserReview.objects.values('tmdb_id', 'media_type', 'title', 'poster_path').annotate(
        review_count=Count('id'),
        avg_rating=DbAvg('rating'),
    ).order_by('-review_count')[offset:offset + limit + 1]
    
    has_more = len(trending) > limit
    results = list(trending[:limit])
    
    return JsonResponse({
        'data': [{
            'tmdbId': t['tmdb_id'],
            'mediaType': t['media_type'],
            'title': t['title'],
            'posterPath': t['poster_path'],
            'ratingCount': t['review_count'],
            'avgRating': round(t['avg_rating'], 1) if t['avg_rating'] else None,
        } for t in results],
        'offset': offset,
        'nextOffset': offset + limit if has_more else None,
        'hasMore': has_more
    })


@require_GET
def get_activity_prompts(request, user_id):
    prompts = [
        {'type': 'review', 'message': 'Share your thoughts on a movie you recently watched!'},
        {'type': 'list', 'message': 'Create a themed movie list to share with others.'},
        {'type': 'follow', 'message': 'Discover and follow other movie enthusiasts.'},
    ]
    return JsonResponse({'prompts': prompts, 'userId': user_id})


@require_GET
def get_recommended_lists(request, user_id):
    lists = UserList.objects.filter(is_public=True).order_by('-follower_count')[:10]
    
    return JsonResponse({
        'lists': [{
            'id': lst.id,
            'title': lst.title,
            'description': lst.description[:100] if lst.description else '',
            'userId': str(lst.user.id),
            'userName': lst.user.first_name or lst.user.email,
            'followerCount': lst.follower_count,
            'itemCount': lst.items.count(),
        } for lst in lists]
    })


@require_GET
def get_similar_users(request, user_id):
    from .models import UserSimilarity
    
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            return JsonResponse({'similarUsers': []})
    
    similarities = UserSimilarity.objects.filter(user1=user).select_related('user2').order_by('-similarity_score')[:10]
    
    if not similarities:
        similar = User.objects.exclude(id=user.id).order_by('?')[:5]
        return JsonResponse({
            'similarUsers': [{
                'userId': str(u.id),
                'userName': u.first_name or u.email,
                'similarity': 0.5,
            } for u in similar]
        })
    
    return JsonResponse({
        'similarUsers': [{
            'userId': str(s.user2.id),
            'userName': s.user2.first_name or s.user2.email,
            'similarity': s.similarity_score,
            'commonMovies': s.common_movies,
        } for s in similarities]
    })


@require_GET
def get_personalized_feed(request, user_id):
    time_filter = request.GET.get('timeFilter', 'weekly')
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 20))
    
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            return JsonResponse({'activities': [], 'offset': offset, 'hasMore': False})
    
    following_ids = UserFollow.objects.filter(follower=user).values_list('following_id', flat=True)
    
    if following_ids:
        reviews = UserReview.objects.filter(
            user_id__in=following_ids,
            is_public=True
        ).select_related('user').order_by('-created_at')[offset:offset + limit]
    else:
        reviews = UserReview.objects.filter(is_public=True).select_related('user').order_by('-created_at')[offset:offset + limit]
    
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
    
    return JsonResponse({
        'activities': activities,
        'offset': offset,
        'hasMore': len(reviews) == limit
    })


def get_or_create_demo_user():
    demo_user, _ = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@cinesuggest.com',
            'first_name': 'Demo',
            'last_name': 'User',
        }
    )
    return demo_user


@require_GET
def demo_user_stats(request):
    """Get demo user activity stats"""
    demo_user = get_or_create_demo_user()
    stats, _ = UserActivityStats.objects.get_or_create(
        user=demo_user,
        defaults={
            'total_reviews': 0,
            'total_lists': 0,
            'total_followers': 0,
            'total_following': 0,
            'user_level': 1,
            'experience_points': 0,
        }
    )
    
    stats.total_reviews = UserReview.objects.filter(user=demo_user).count()
    stats.total_lists = UserList.objects.filter(user=demo_user).count()
    stats.total_followers = UserFollow.objects.filter(following=demo_user).count()
    stats.total_following = UserFollow.objects.filter(follower=demo_user).count()
    stats.save()
    
    return JsonResponse({
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
            'lastActivityAt': stats.last_activity_at.isoformat() if stats.last_activity_at else None,
        }
    })


@require_GET
def demo_user_lists(request):
    """Get demo user lists"""
    demo_user = get_or_create_demo_user()
    lists = UserList.objects.filter(user=demo_user)
    
    return JsonResponse({
        'lists': [{
            'id': lst.id,
            'title': lst.title,
            'description': lst.description,
            'isPublic': lst.is_public,
            'followerCount': lst.follower_count,
            'itemCount': lst.items.count(),
            'createdAt': lst.created_at.isoformat(),
            'updatedAt': lst.updated_at.isoformat(),
            'user': {
                'id': str(demo_user.id),
                'firstName': demo_user.first_name,
                'lastName': demo_user.last_name,
            }
        } for lst in lists]
    })


@require_GET
def demo_user_badge_progress(request):
    """Get demo user badge progress"""
    demo_user = get_or_create_demo_user()
    badges = UserBadge.objects.filter(user=demo_user)
    earned_badge_types = set(b.badge_type for b in badges)
    
    reviews_count = UserReview.objects.filter(user=demo_user).count()
    lists_count = UserList.objects.filter(user=demo_user).count()
    followers_count = UserFollow.objects.filter(following=demo_user).count()
    
    badge_definitions = [
        {
            'badgeType': 'first_review',
            'name': 'First Review',
            'description': 'Write your first review',
            'icon': '⭐',
            'requiredValue': 1,
            'currentValue': min(reviews_count, 1),
        },
        {
            'badgeType': 'review_master',
            'name': 'Review Master',
            'description': 'Write 50 reviews',
            'icon': '🏆',
            'requiredValue': 50,
            'currentValue': min(reviews_count, 50),
        },
        {
            'badgeType': 'list_creator',
            'name': 'List Creator',
            'description': 'Create your first list',
            'icon': '📝',
            'requiredValue': 1,
            'currentValue': min(lists_count, 1),
        },
        {
            'badgeType': 'social_butterfly',
            'name': 'Social Butterfly',
            'description': 'Get 10 followers',
            'icon': '🦋',
            'requiredValue': 10,
            'currentValue': min(followers_count, 10),
        },
        {
            'badgeType': 'movie_buff',
            'name': 'Movie Buff',
            'description': 'Write 100 reviews',
            'icon': '🎬',
            'requiredValue': 100,
            'currentValue': min(reviews_count, 100),
        },
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
    
    return JsonResponse(badge_progress, safe=False)


@require_GET
def demo_user_impact(request):
    """Get demo user impact stats"""
    demo_user = get_or_create_demo_user()
    
    reviews_count = UserReview.objects.filter(user=demo_user).count()
    avg_rating = UserReview.objects.filter(user=demo_user).aggregate(avg=Avg('rating'))['avg'] or 0
    total_helpful = sum(r.helpful_count for r in UserReview.objects.filter(user=demo_user))
    awards_received = ReviewAward.objects.filter(review__user=demo_user).count()
    comments_received = ReviewComment.objects.filter(review__user=demo_user).count()
    lists_created = UserList.objects.filter(user=demo_user).count()
    list_items = ListItem.objects.filter(list__user=demo_user).count()
    list_followers = sum(l.follower_count for l in UserList.objects.filter(user=demo_user))
    followers_count = UserFollow.objects.filter(following=demo_user).count()
    following_count = UserFollow.objects.filter(follower=demo_user).count()
    
    engagement_score = reviews_count * 2 + lists_created * 5 + awards_received + followers_count * 3
    
    if engagement_score >= 100:
        rank = "Legend"
        next_rank_score = 100
        progress = 100
    elif engagement_score >= 50:
        rank = "Expert"
        next_rank_score = 100
        progress = int((engagement_score - 50) / 50 * 100)
    elif engagement_score >= 20:
        rank = "Active Member"
        next_rank_score = 50
        progress = int((engagement_score - 20) / 30 * 100)
    elif engagement_score >= 5:
        rank = "Contributor"
        next_rank_score = 20
        progress = int((engagement_score - 5) / 15 * 100)
    else:
        rank = "Newcomer"
        next_rank_score = 5
        progress = int(engagement_score / 5 * 100)
    
    return JsonResponse({
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
            'profileViews': 0,
        },
        'engagementReceived': {
            'totalAwardsReceived': awards_received,
            'totalCommentsReceived': comments_received,
            'totalReviewLikes': total_helpful,
        },
        'communityRank': {
            'rank': rank,
            'engagementScore': engagement_score,
            'progressToNextRank': min(progress, 100),
            'nextRankScore': next_rank_score,
        }
    })


@csrf_exempt
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def manage_community_list(request, list_id):
    """GET/update/delete a community list by ID."""
    try:
        lst = UserList.objects.get(id=list_id)
    except UserList.DoesNotExist:
        return JsonResponse({'error': 'List not found'}, status=404)

    if request.method == "GET":
        if not lst.is_public:
            if not request.user.is_authenticated or request.user.id != lst.user.id:
                return JsonResponse({'error': 'Not authorized'}, status=403)
        items = ListItem.objects.filter(list=lst)
        return JsonResponse({
            'list': {
                'id': lst.id,
                'title': lst.title,
                'description': lst.description,
                'isPublic': lst.is_public,
                'followerCount': lst.follower_count,
                'createdAt': lst.created_at.isoformat(),
                'updatedAt': lst.updated_at.isoformat(),
                'user': {
                    'id': str(lst.user.id),
                    'firstName': lst.user.first_name,
                    'lastName': lst.user.last_name,
                },
                'items': [{
                    'id': item.id,
                    'tmdbId': item.tmdb_id,
                    'mediaType': item.media_type,
                    'title': item.title,
                    'posterPath': item.poster_path,
                    'note': item.note,
                    'position': item.position,
                    'addedAt': item.added_at.isoformat(),
                } for item in items]
            }
        })

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    if lst.user != request.user:
        return JsonResponse({'error': 'Not authorized'}, status=403)

    if request.method == "DELETE":
        lst.delete()
        return JsonResponse({'success': True})

    try:
        data = json.loads(request.body)
        if 'title' in data:
            lst.title = data['title']
        if 'description' in data:
            lst.description = data['description']
        if 'isPublic' in data:
            lst.is_public = data['isPublic']
        lst.save()
        return JsonResponse({
            'success': True,
            'list': {'id': lst.id, 'title': lst.title, 'description': lst.description, 'isPublic': lst.is_public}
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def is_following_list(request, list_id):
    """Check if the current user is following a specific list."""
    if not request.user.is_authenticated:
        return JsonResponse({'isFollowing': False})
    exists = ListFollow.objects.filter(user=request.user, list_id=list_id).exists()
    return JsonResponse({'isFollowing': exists})


@require_GET
def get_user_badge_progress(request, user_id):
    """Get badge progress for a real user (not just demo)."""
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

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

    return JsonResponse(badge_progress, safe=False)


@require_GET
def get_user_impact(request, user_id):
    """Get impact stats for a real user."""
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError):
        try:
            user = User.objects.get(username=user_id)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

    reviews_count = UserReview.objects.filter(user=user).count()
    avg_rating = UserReview.objects.filter(user=user).aggregate(avg=Avg('rating'))['avg'] or 0
    total_helpful = sum(r.helpful_count for r in UserReview.objects.filter(user=user))
    awards_received = ReviewAward.objects.filter(review__user=user).count()
    comments_received = ReviewComment.objects.filter(review__user=user).count()
    lists_created = UserList.objects.filter(user=user).count()
    list_items = ListItem.objects.filter(list__user=user).count()
    list_followers = sum(l.follower_count for l in UserList.objects.filter(user=user))
    followers_count = UserFollow.objects.filter(following=user).count()
    following_count = UserFollow.objects.filter(follower=user).count()

    engagement_score = reviews_count * 2 + lists_created * 5 + awards_received + followers_count * 3

    if engagement_score >= 100:
        rank, next_rank_score, progress = "Legend", 100, 100
    elif engagement_score >= 50:
        rank, next_rank_score = "Expert", 100
        progress = int((engagement_score - 50) / 50 * 100)
    elif engagement_score >= 20:
        rank, next_rank_score = "Active Member", 50
        progress = int((engagement_score - 20) / 30 * 100)
    elif engagement_score >= 5:
        rank, next_rank_score = "Contributor", 20
        progress = int((engagement_score - 5) / 15 * 100)
    else:
        rank, next_rank_score = "Newcomer", 5
        progress = int(engagement_score / 5 * 100) if engagement_score > 0 else 0

    return JsonResponse({
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
            'profileViews': 0,
        },
        'engagementReceived': {
            'totalAwardsReceived': awards_received,
            'totalCommentsReceived': comments_received,
            'totalReviewLikes': total_helpful,
        },
        'communityRank': {
            'rank': rank,
            'engagementScore': engagement_score,
            'progressToNextRank': min(progress, 100),
            'nextRankScore': next_rank_score,
        }
    })
