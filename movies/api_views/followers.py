import logging
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from movies.models import UserFollow, Notification
from movies.serializers.social import FollowSerializer, FollowUserSerializer

logger = logging.getLogger(__name__)


def _get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


class FollowersView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = FollowSerializer

    def get_queryset(self):
        return UserFollow.objects.filter(
            following_id=self.kwargs['user_id']
        ).select_related('follower')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['direction'] = 'follower'
        return ctx

    def list(self, request, *args, **kwargs):
        user = _get_user_or_404(self.kwargs['user_id'])
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'followers': serializer.data})


class FollowingView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = FollowSerializer

    def get_queryset(self):
        return UserFollow.objects.filter(
            follower_id=self.kwargs['user_id']
        ).select_related('following')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['direction'] = 'following'
        return ctx

    def list(self, request, *args, **kwargs):
        user = _get_user_or_404(self.kwargs['user_id'])
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'following': serializer.data})


class FollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = FollowUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        target_user_id = serializer.validated_data['targetUserId']
        target_user = _get_user_or_404(target_user_id)
        if not target_user:
            return Response({'error': 'Target user not found', 'code': 'NOT_FOUND'}, status=404)
        if request.user.id == target_user.id:
            return Response({'error': 'Cannot follow yourself', 'code': 'VALIDATION_ERROR'}, status=400)

        follow, created = UserFollow.objects.get_or_create(
            follower=request.user, following=target_user
        )
        if created:
            Notification.objects.create(
                user=target_user, notification_type='follow',
                message=f'{request.user.first_name or request.user.email} started following you',
                related_user_id=request.user.id
            )
        return Response({'success': True, 'created': created})


class UnfollowUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, target_user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        deleted, _ = UserFollow.objects.filter(
            follower=request.user, following_id=target_user_id
        ).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class IsFollowingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id, target_user_id):
        if not request.user.is_authenticated or str(request.user.id) != str(user_id):
            return Response({'isFollowing': False})
        exists = UserFollow.objects.filter(
            follower=request.user, following_id=target_user_id
        ).exists()
        return Response({'isFollowing': exists})
