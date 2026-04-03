import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg
from .models import (
    UserProfile, UserWatchlist, UserFavorites, ViewingHistory, 
    UserReview, UserFollow, UserList, ListItem, Notification, UserPreferences
)
from .decorators import owner_required, api_auth_required


def get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


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
def get_profile(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    watchlist_count = UserWatchlist.objects.filter(user=user).count()
    favorites_count = UserFavorites.objects.filter(user=user).count()
    reviews_count = UserReview.objects.filter(user=user).count()
    watched_count = ViewingHistory.objects.filter(user=user).count()
    followers_count = UserFollow.objects.filter(following=user).count()
    following_count = UserFollow.objects.filter(follower=user).count()
    lists_count = UserList.objects.filter(user=user).count()
    
    avg_rating = UserReview.objects.filter(user=user).aggregate(avg=Avg('rating'))['avg'] or 0
    
    is_own_profile = request.user.is_authenticated and request.user.id == user.id

    return JsonResponse({
        'user': {
            'id': str(user.id),
            'email': user.email if is_own_profile else '',
            'firstName': user.first_name,
            'lastName': user.last_name,
            'bio': profile.bio,
            'profileImageUrl': profile.profile_image_url,
            'createdAt': user.date_joined.isoformat(),
        },
        'statistics': {
            'totalWatched': watched_count,
            'watchlistCount': watchlist_count,
            'favoritesCount': favorites_count,
            'reviewsCount': reviews_count,
            'followersCount': followers_count,
            'followingCount': following_count,
            'listsCount': lists_count,
            'avgRating': round(avg_rating, 1),
        }
    })


@csrf_exempt
@require_http_methods(["PATCH"])
def update_profile(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        
        if 'bio' in data:
            profile.bio = data['bio']
        if 'profileImageUrl' in data:
            profile.profile_image_url = data['profileImageUrl']
        if 'firstName' in data:
            request.user.first_name = data['firstName']
        if 'lastName' in data:
            request.user.last_name = data['lastName']
        
        profile.save()
        request.user.save()
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(request.user.id),
                'email': request.user.email,
                'firstName': request.user.first_name,
                'lastName': request.user.last_name,
                'bio': profile.bio,
                'profileImageUrl': profile.profile_image_url,
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_watchlist(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized to view this watchlist'}, status=403)
    
    items = UserWatchlist.objects.filter(user=user)
    return JsonResponse({
        'items': [{
            'id': item.id,
            'tmdbId': item.tmdb_id,
            'mediaType': item.media_type,
            'title': item.title,
            'posterPath': item.poster_path,
            'addedAt': item.added_at.isoformat(),
        } for item in items]
    })


@csrf_exempt
@require_POST
def add_to_watchlist(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        
        if not tmdb_id:
            return JsonResponse({'error': 'tmdbId is required'}, status=400)
        
        item, created = UserWatchlist.objects.get_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={'title': title, 'poster_path': poster_path}
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
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_from_watchlist(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    deleted, _ = UserWatchlist.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_favorites(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized to view favorites'}, status=403)
    
    items = UserFavorites.objects.filter(user=user)
    return JsonResponse({
        'items': [{
            'id': item.id,
            'tmdbId': item.tmdb_id,
            'mediaType': item.media_type,
            'title': item.title,
            'posterPath': item.poster_path,
            'addedAt': item.added_at.isoformat(),
        } for item in items]
    })


@csrf_exempt
@require_POST
def add_to_favorites(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        
        if not tmdb_id:
            return JsonResponse({'error': 'tmdbId is required'}, status=400)
        
        item, created = UserFavorites.objects.get_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={'title': title, 'poster_path': poster_path}
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
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_from_favorites(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    deleted, _ = UserFavorites.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_viewing_history(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized to view history'}, status=403)
    
    items = ViewingHistory.objects.filter(user=user)[:50]
    return JsonResponse({
        'items': [{
            'id': item.id,
            'tmdbId': item.tmdb_id,
            'mediaType': item.media_type,
            'title': item.title,
            'posterPath': item.poster_path,
            'watchedAt': item.watched_at.isoformat(),
        } for item in items]
    })


@csrf_exempt
@require_POST
def add_to_viewing_history(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        
        if not tmdb_id:
            return JsonResponse({'error': 'tmdbId is required'}, status=400)
        
        item = ViewingHistory.objects.create(
            user=request.user,
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=title,
            poster_path=poster_path
        )
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'tmdbId': item.tmdb_id,
                'mediaType': item.media_type,
                'title': item.title,
                'posterPath': item.poster_path,
                'watchedAt': item.watched_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_from_viewing_history(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)

    deleted, _ = ViewingHistory.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()

    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_user_reviews(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    reviews = UserReview.objects.filter(user=user)
    if not request.user.is_authenticated or request.user.id != user.id:
        reviews = reviews.filter(is_public=True)
    
    return JsonResponse({
        'reviews': [{
            'id': review.id,
            'tmdbId': review.tmdb_id,
            'mediaType': review.media_type,
            'title': review.title,
            'posterPath': review.poster_path,
            'rating': review.rating,
            'reviewText': review.review_text,
            'isPublic': review.is_public,
            'helpfulCount': review.helpful_count,
            'createdAt': review.created_at.isoformat(),
            'updatedAt': review.updated_at.isoformat(),
            'user': {
                'id': str(user.id),
                'firstName': user.first_name,
                'lastName': user.last_name,
            }
        } for review in reviews]
    })


@csrf_exempt
@require_POST
def create_review(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        tmdb_id = data.get('tmdbId')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        poster_path = data.get('posterPath', '')
        rating = data.get('rating')
        review_text = data.get('reviewText', '')
        is_public = data.get('isPublic', True)
        
        if not tmdb_id or rating is None:
            return JsonResponse({'error': 'tmdbId and rating are required'}, status=400)
        
        review, created = UserReview.objects.update_or_create(
            user=request.user,
            tmdb_id=tmdb_id,
            media_type=media_type,
            defaults={
                'title': title,
                'poster_path': poster_path,
                'rating': rating,
                'review_text': review_text,
                'is_public': is_public,
            }
        )
        
        return JsonResponse({
            'success': True,
            'created': created,
            'review': {
                'id': review.id,
                'tmdbId': review.tmdb_id,
                'mediaType': review.media_type,
                'title': review.title,
                'rating': review.rating,
                'reviewText': review.review_text,
                'isPublic': review.is_public,
                'createdAt': review.created_at.isoformat(),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_review(request, user_id, review_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    deleted, _ = UserReview.objects.filter(
        user=request.user,
        id=review_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_reviews_for_content(request, tmdb_id):
    media_type = request.GET.get('mediaType', 'movie')
    reviews = UserReview.objects.filter(
        tmdb_id=tmdb_id,
        media_type=media_type,
        is_public=True
    ).select_related('user')
    
    return JsonResponse({
        'reviews': [{
            'id': review.id,
            'tmdbId': review.tmdb_id,
            'mediaType': review.media_type,
            'title': review.title,
            'rating': review.rating,
            'reviewText': review.review_text,
            'helpfulCount': review.helpful_count,
            'createdAt': review.created_at.isoformat(),
            'user': {
                'id': str(review.user.id),
                'firstName': review.user.first_name,
                'lastName': review.user.last_name,
            }
        } for review in reviews]
    })


@require_GET
def check_watchlist(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return JsonResponse({'inWatchlist': False})
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'inWatchlist': False})
    
    exists = UserWatchlist.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).exists()
    
    return JsonResponse({'inWatchlist': exists})


@require_GET
def check_favorites(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return JsonResponse({'inFavorites': False})
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'inFavorites': False})
    
    exists = UserFavorites.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).exists()
    
    return JsonResponse({'inFavorites': exists})


@require_GET
def get_user_by_username(request, username):
    """Get a user's public profile by username"""
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    profile, _ = UserProfile.objects.get_or_create(user=user)

    is_own_profile = request.user.is_authenticated and request.user.id == user.id

    return JsonResponse({
        'id': str(user.id),
        'username': user.username,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'email': user.email if is_own_profile else '',
        'profileImageUrl': profile.profile_image_url or '',
        'bio': profile.bio or '',
        'followersCount': UserFollow.objects.filter(following=user).count(),
        'followingCount': UserFollow.objects.filter(follower=user).count(),
        'reviewsCount': UserReview.objects.filter(user=user).count(),
        'createdAt': user.date_joined.isoformat(),
    })
