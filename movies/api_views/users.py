import logging
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.db.models import Avg
from movies.models import (
    UserProfile, UserWatchlist, UserFavorites, ViewingHistory,
    UserReview, UserFollow, UserList, UserPreferences,
)
from movies.serializers.user import (
    UserWatchlistSerializer, UserFavoritesSerializer, ViewingHistorySerializer,
    CreateWatchlistSerializer, CreateFavoritesSerializer, CreateViewingHistorySerializer,
    UpdateProfileSerializer,
)
from movies.serializers.social import UserReviewSerializer, CreateReviewSerializer

logger = logging.getLogger(__name__)


def _get_user_or_none(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


class UserByUsernameView(RetrieveAPIView):
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        identifier = self.kwargs['username']
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            if identifier.isdigit():
                try:
                    user = User.objects.get(id=int(identifier))
                except User.DoesNotExist:
                    return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)
            else:
                return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        profile, _ = UserProfile.objects.get_or_create(user=user)
        is_own = request.user.is_authenticated and request.user.id == user.id

        return Response({
            'id': str(user.id),
            'username': user.username,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'email': user.email if is_own else '',
            'profileImageUrl': profile.profile_image_url or '',
            'bio': profile.bio or '',
            'followersCount': UserFollow.objects.filter(following=user).count(),
            'followingCount': UserFollow.objects.filter(follower=user).count(),
            'reviewsCount': UserReview.objects.filter(user=user).count(),
            'createdAt': user.date_joined.isoformat(),
        })


class UserProfileView(RetrieveAPIView):
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        user = _get_user_or_none(self.kwargs['user_id'])
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        profile, _ = UserProfile.objects.get_or_create(user=user)
        is_own = request.user.is_authenticated and request.user.id == user.id

        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email if is_own else '',
                'firstName': user.first_name,
                'lastName': user.last_name,
                'bio': profile.bio,
                'profileImageUrl': profile.profile_image_url,
                'createdAt': user.date_joined.isoformat(),
            },
            'statistics': {
                'totalWatched': ViewingHistory.objects.filter(user=user).count(),
                'watchlistCount': UserWatchlist.objects.filter(user=user).count(),
                'favoritesCount': UserFavorites.objects.filter(user=user).count(),
                'reviewsCount': UserReview.objects.filter(user=user).count(),
                'followersCount': UserFollow.objects.filter(following=user).count(),
                'followingCount': UserFollow.objects.filter(follower=user).count(),
                'listsCount': UserList.objects.filter(user=user).count(),
                'avgRating': round(UserReview.objects.filter(user=user).aggregate(avg=Avg('rating'))['avg'] or 0, 1),
            }
        })


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        serializer = UpdateProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        data = serializer.validated_data
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

        return Response({
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


class WatchlistView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserWatchlistSerializer

    def list(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized to view this watchlist', 'code': 'FORBIDDEN'}, status=403)
        items = UserWatchlist.objects.filter(user=request.user)
        serializer = self.get_serializer(items, many=True)
        return Response({'items': serializer.data})


class WatchlistAddView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateWatchlistSerializer

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        item, created = UserWatchlist.objects.get_or_create(
            user=request.user, tmdb_id=data['tmdbId'], media_type=data['mediaType'],
            defaults={'title': data.get('title', ''), 'poster_path': data.get('posterPath', '')}
        )
        return Response({
            'success': True, 'created': created,
            'item': UserWatchlistSerializer(item).data,
        })


class WatchlistRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, tmdb_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        deleted, _ = UserWatchlist.objects.filter(user=request.user, tmdb_id=tmdb_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class WatchlistCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id, tmdb_id):
        if not request.user.is_authenticated or str(request.user.id) != str(user_id):
            return Response({'inWatchlist': False})
        exists = UserWatchlist.objects.filter(user=request.user, tmdb_id=tmdb_id).exists()
        return Response({'inWatchlist': exists})


class FavoritesView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserFavoritesSerializer

    def list(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized to view favorites', 'code': 'FORBIDDEN'}, status=403)
        items = UserFavorites.objects.filter(user=request.user)
        serializer = self.get_serializer(items, many=True)
        return Response({'items': serializer.data})


class FavoritesAddView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateFavoritesSerializer

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        item, created = UserFavorites.objects.get_or_create(
            user=request.user, tmdb_id=data['tmdbId'], media_type=data['mediaType'],
            defaults={'title': data.get('title', ''), 'poster_path': data.get('posterPath', '')}
        )
        return Response({
            'success': True, 'created': created,
            'item': UserFavoritesSerializer(item).data,
        })


class FavoritesRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, tmdb_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        deleted, _ = UserFavorites.objects.filter(user=request.user, tmdb_id=tmdb_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class FavoritesCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id, tmdb_id):
        if not request.user.is_authenticated or str(request.user.id) != str(user_id):
            return Response({'inFavorites': False})
        exists = UserFavorites.objects.filter(user=request.user, tmdb_id=tmdb_id).exists()
        return Response({'inFavorites': exists})


class ViewingHistoryView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ViewingHistorySerializer

    def list(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized to view history', 'code': 'FORBIDDEN'}, status=403)
        items = ViewingHistory.objects.filter(user=request.user)[:50]
        serializer = self.get_serializer(items, many=True)
        return Response({'items': serializer.data})


class ViewingHistoryAddView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateViewingHistorySerializer

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        item = ViewingHistory.objects.create(
            user=request.user, tmdb_id=data['tmdbId'], media_type=data['mediaType'],
            title=data.get('title', ''), poster_path=data.get('posterPath', '')
        )
        return Response({
            'success': True,
            'item': ViewingHistorySerializer(item).data,
        })


class ViewingHistoryRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, tmdb_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        deleted, _ = ViewingHistory.objects.filter(user=request.user, tmdb_id=tmdb_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class UserReviewsView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserReviewSerializer

    def list(self, request, *args, **kwargs):
        user = _get_user_or_none(self.kwargs['user_id'])
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)
        reviews = UserReview.objects.filter(user=user).select_related('user')
        if not request.user.is_authenticated or request.user.id != user.id:
            reviews = reviews.filter(is_public=True)
        serializer = self.get_serializer(reviews, many=True)
        return Response({'reviews': serializer.data})


class CreateReviewView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreateReviewSerializer

    def create(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        review, created = UserReview.objects.update_or_create(
            user=request.user, tmdb_id=data['tmdbId'], media_type=data['mediaType'],
            defaults={
                'title': data.get('title', ''), 'poster_path': data.get('posterPath', ''),
                'rating': data['rating'], 'review_text': data.get('reviewText', ''),
                'is_public': data.get('isPublic', True),
            }
        )
        return Response({
            'success': True, 'created': created,
            'review': UserReviewSerializer(review).data,
        })


class DeleteReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, review_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        deleted, _ = UserReview.objects.filter(user=request.user, id=review_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class ContentReviewsView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserReviewSerializer

    def list(self, request, *args, **kwargs):
        tmdb_id = self.kwargs['tmdb_id']
        media_type = request.query_params.get('mediaType', 'movie')
        reviews = UserReview.objects.filter(
            tmdb_id=tmdb_id, media_type=media_type, is_public=True
        ).select_related('user')
        serializer = self.get_serializer(reviews, many=True)
        return Response({'reviews': serializer.data})
