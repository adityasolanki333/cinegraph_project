import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6)
    firstName = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    lastName = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=6)


def _user_dict(user):
    return {
        'id': str(user.id),
        'email': user.email,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'createdAt': user.date_joined.isoformat(),
    }


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'csrfToken': get_token(request)})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        data = serializer.validated_data
        email = data['email'].strip()
        password = data['password']
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            provisional_user = User(username=email, email=email, first_name=first_name, last_name=last_name)
            validate_password(password, user=provisional_user)
        except DjangoValidationError as e:
            return Response({'error': '; '.join(e.messages), 'code': 'VALIDATION_ERROR'}, status=400)

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            return Response({'error': 'Email already registered', 'code': 'VALIDATION_ERROR'}, status=400)

        user = User.objects.create_user(
            username=email, email=email, password=password,
            first_name=first_name, last_name=last_name
        )
        login(request, user)
        return Response({'success': True, 'user': _user_dict(user)})


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        user = authenticate(
            request, username=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        if user is not None:
            login(request, user)
            return Response({'success': True, 'user': _user_dict(user)})
        return Response({'error': 'Invalid email or password', 'code': 'AUTH_REQUIRED'}, status=401)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        logout(request)
        return Response({'success': True})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            user = request.user
            return Response({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'createdAt': user.date_joined.isoformat(),
                }
            })
        return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        logger.warning(
            'Password reset requested for %s but email sending is not configured. '
            'No reset token has been generated or sent.',
            serializer.validated_data['email'],
        )
        return Response({
            'success': True,
            'message': 'Password reset is not yet available. Email delivery has not been configured.'
        })


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
        signer = TimestampSigner()

        try:
            user_id = signer.unsign(serializer.validated_data['token'], max_age=3600)
            user = User.objects.get(id=user_id)
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({'success': True, 'message': 'Password successfully reset'})
        except SignatureExpired:
            return Response({'error': 'Reset link has expired', 'code': 'VALIDATION_ERROR'}, status=400)
        except BadSignature:
            return Response({'error': 'Invalid reset link', 'code': 'VALIDATION_ERROR'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)


class DeleteAccountSerializer(serializers.Serializer):
    confirmation = serializers.CharField()


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        serializer = DeleteAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        confirmation = serializer.validated_data['confirmation']
        if confirmation != 'DELETE':
            return Response({'error': 'Please type DELETE to confirm account deletion', 'code': 'VALIDATION_ERROR'}, status=400)

        user = request.user

        from movies.models import (
            UserProfile, UserPreferences, UserWatchlist, UserFavorites,
            ViewingHistory, UserReview, UserFollow, UserList,
            UserActivityStats, UserBadge, UserCommunity, DiversityMetrics,
        )
        from movies.models.notifications import Notification, NotificationSettings
        from movies.models.social import ListItem, ListFollow

        from django.db import transaction

        try:
            with transaction.atomic():
                UserProfile.objects.filter(user=user).delete()
                UserPreferences.objects.filter(user=user).delete()
                UserWatchlist.objects.filter(user=user).delete()
                UserFavorites.objects.filter(user=user).delete()
                ViewingHistory.objects.filter(user=user).delete()
                UserReview.objects.filter(user=user).delete()
                UserFollow.objects.filter(follower=user).delete()
                UserFollow.objects.filter(following=user).delete()
                user_lists = UserList.objects.filter(user=user)
                for user_list in user_lists:
                    ListItem.objects.filter(list=user_list).delete()
                    ListFollow.objects.filter(list=user_list).delete()
                user_lists.delete()
                Notification.objects.filter(user=user).delete()
                NotificationSettings.objects.filter(user=user).delete()
                UserActivityStats.objects.filter(user=user).delete()
                UserBadge.objects.filter(user=user).delete()
                UserCommunity.objects.filter(user=user).delete()
                DiversityMetrics.objects.filter(user=user).delete()

                logout(request)
                user.delete()

            return Response({'success': True, 'message': 'Account permanently deleted'})
        except Exception as e:
            logger.error('Error deleting account for user %s: %s', user.id, str(e))
            return Response({'error': 'Failed to delete account', 'code': 'SERVER_ERROR'}, status=500)
