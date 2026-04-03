import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Avg
from .models import (
    UserProfile, UserWatchlist, UserFavorites, ViewingHistory, 
    UserReview, UserFollow, UserList, ListItem, Notification, UserPreferences
)
from .decorators import owner_required, api_auth_required, rate_limit
from .validation import (
    error_response, parse_json_body, validate_rating, validate_tmdb_id,
    validate_media_type, validate_string_length,
    MAX_TITLE_LENGTH, MAX_REVIEW_TEXT_LENGTH, MAX_BIO_LENGTH, MAX_URL_LENGTH,
)

logger = logging.getLogger(__name__)


def get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


@require_GET
def get_profile(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
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


@rate_limit()
@require_http_methods(["PATCH"])
def update_profile(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    data, err = parse_json_body(request)
    if err:
        return err

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if 'bio' in data:
        bio, err = validate_string_length(data['bio'], 'bio', MAX_BIO_LENGTH)
        if err:
            return error_response(err, 'VALIDATION_ERROR')
        profile.bio = bio
    if 'profileImageUrl' in data:
        url, err = validate_string_length(data['profileImageUrl'], 'profileImageUrl', MAX_URL_LENGTH)
        if err:
            return error_response(err, 'VALIDATION_ERROR')
        profile.profile_image_url = url
    if 'firstName' in data:
        val, err = validate_string_length(data['firstName'], 'firstName', 150)
        if err:
            return error_response(err, 'VALIDATION_ERROR')
        request.user.first_name = val
    if 'lastName' in data:
        val, err = validate_string_length(data['lastName'], 'lastName', 150)
        if err:
            return error_response(err, 'VALIDATION_ERROR')
        request.user.last_name = val

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


@require_GET
def get_watchlist(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return error_response('Not authorized to view this watchlist', 'FORBIDDEN', 403)
    
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


@rate_limit()
@require_POST
def add_to_watchlist(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    data, err = parse_json_body(request)
    if err:
        return err

    tmdb_id, err = validate_tmdb_id(data.get('tmdbId'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    media_type, err = validate_media_type(data.get('mediaType'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    title, err = validate_string_length(data.get('title', ''), 'title', MAX_TITLE_LENGTH)
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    item, created = UserWatchlist.objects.get_or_create(
        user=request.user,
        tmdb_id=tmdb_id,
        media_type=media_type,
        defaults={'title': title, 'poster_path': data.get('posterPath', '')}
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


@rate_limit()
@require_http_methods(["DELETE"])
def remove_from_watchlist(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    deleted, _ = UserWatchlist.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_favorites(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return error_response('Not authorized to view favorites', 'FORBIDDEN', 403)
    
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


@rate_limit()
@require_POST
def add_to_favorites(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    data, err = parse_json_body(request)
    if err:
        return err

    tmdb_id, err = validate_tmdb_id(data.get('tmdbId'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    media_type, err = validate_media_type(data.get('mediaType'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    title, err = validate_string_length(data.get('title', ''), 'title', MAX_TITLE_LENGTH)
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    item, created = UserFavorites.objects.get_or_create(
        user=request.user,
        tmdb_id=tmdb_id,
        media_type=media_type,
        defaults={'title': title, 'poster_path': data.get('posterPath', '')}
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


@rate_limit()
@require_http_methods(["DELETE"])
def remove_from_favorites(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    deleted, _ = UserFavorites.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()
    
    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_viewing_history(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
    if not request.user.is_authenticated or str(request.user.id) != str(user_id):
        return error_response('Not authorized to view history', 'FORBIDDEN', 403)
    
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


@rate_limit()
@require_POST
def add_to_viewing_history(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    data, err = parse_json_body(request)
    if err:
        return err

    tmdb_id, err = validate_tmdb_id(data.get('tmdbId'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    media_type, err = validate_media_type(data.get('mediaType'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    title, err = validate_string_length(data.get('title', ''), 'title', MAX_TITLE_LENGTH)
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    item = ViewingHistory.objects.create(
        user=request.user,
        tmdb_id=tmdb_id,
        media_type=media_type,
        title=title,
        poster_path=data.get('posterPath', '')
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


@rate_limit()
@require_http_methods(["DELETE"])
def remove_from_viewing_history(request, user_id, tmdb_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)

    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)

    deleted, _ = ViewingHistory.objects.filter(
        user=request.user,
        tmdb_id=tmdb_id
    ).delete()

    return JsonResponse({'success': True, 'deleted': deleted > 0})


@require_GET
def get_user_reviews(request, user_id):
    user = get_user_or_404(user_id)
    if not user:
        return error_response('User not found', 'NOT_FOUND', 404)
    
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


@rate_limit()
@require_POST
def create_review(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    data, err = parse_json_body(request)
    if err:
        return err

    tmdb_id, err = validate_tmdb_id(data.get('tmdbId'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    rating, err = validate_rating(data.get('rating'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    media_type, err = validate_media_type(data.get('mediaType'))
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    title, err = validate_string_length(data.get('title', ''), 'title', MAX_TITLE_LENGTH)
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    review_text, err = validate_string_length(data.get('reviewText', ''), 'reviewText', MAX_REVIEW_TEXT_LENGTH)
    if err:
        return error_response(err, 'VALIDATION_ERROR')

    review, created = UserReview.objects.update_or_create(
        user=request.user,
        tmdb_id=tmdb_id,
        media_type=media_type,
        defaults={
            'title': title,
            'poster_path': data.get('posterPath', ''),
            'rating': rating,
            'review_text': review_text,
            'is_public': data.get('isPublic', True),
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


@rate_limit()
@require_http_methods(["DELETE"])
def delete_review(request, user_id, review_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
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
        return error_response('User not found', 'NOT_FOUND', 404)

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
