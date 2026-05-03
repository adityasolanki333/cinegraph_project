import logging

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6)
    firstName = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)
    lastName = serializers.CharField(max_length=150, required=False, default='', allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=6)


def _user_dict(user):
    from movies.models.user import UserProfile
    profile_image_url = None
    bio = ''
    try:
        profile = user.profile
        profile_image_url = profile.profile_image_url
        bio = profile.bio or ''
    except Exception:
        pass

    display_name = user.first_name or user.username or user.email.split('@')[0]

    return {
        'id': str(user.id),
        'email': user.email,
        'username': user.username,
        'firstName': user.first_name or display_name,
        'lastName': user.last_name,
        'bio': bio,
        'profileImageUrl': profile_image_url,
        'createdAt': user.date_joined.isoformat(),
    }


def _get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


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
        tokens = _get_tokens_for_user(user)
        return Response({'success': True, 'user': _user_dict(user), 'tokens': tokens})


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
            tokens = _get_tokens_for_user(user)
            from django.core.cache import cache
            cache.delete(f"user:{user.id}:me")
            return Response({'success': True, 'user': _user_dict(user), 'tokens': tokens})
        return Response({'error': 'Invalid email or password', 'code': 'AUTH_REQUIRED'}, status=401)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({'success': True})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data)
        except Exception:
            return Response({'error': 'Invalid or expired refresh token', 'code': 'AUTH_REQUIRED'}, status=401)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.core.cache import cache
        cache_key = f"user:{request.user.id}:me"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        user = User.objects.select_related('profile').get(pk=request.user.pk)
        profile_image_url = None
        bio = ''
        try:
            profile = user.profile
            profile_image_url = profile.profile_image_url
            bio = profile.bio or ''
        except Exception:
            pass

        display_name = user.first_name or user.username or user.email.split('@')[0]
        data = {
            'user': {
                'id': str(user.id),
                'email': user.email,
                'username': user.username,
                'firstName': user.first_name or display_name,
                'lastName': user.last_name,
                'bio': bio,
                'profileImageUrl': profile_image_url,
                'createdAt': user.date_joined.isoformat(),
            }
        }
        cache.set(cache_key, data, 300)
        return Response(data)


class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': True,
                'message': 'If an account with that email exists, a reset link has been sent.'
            })

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        combined_token = f'{uid}:{token}'

        host = request.META.get('HTTP_HOST', '')
        scheme = 'https' if request.is_secure() or request.META.get('HTTP_X_FORWARDED_PROTO') == 'https' else 'http'
        reset_link = f'{scheme}://{host}/forget-password?token={combined_token}'

        from django.conf import settings
        from django.core.mail import send_mail
        email_sent = False

        if settings.EMAIL_HOST_USER:
            try:
                html_content = (
                    f'<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px">'
                    f'<h2 style="color:#6366f1">CineGraph Password Reset</h2>'
                    f'<p>Hi {user.first_name or "there"},</p>'
                    f'<p>We received a request to reset your password. Click the button below to set a new password:</p>'
                    f'<p style="text-align:center;margin:30px 0">'
                    f'<a href="{reset_link}" style="background:#6366f1;color:#fff;padding:12px 32px;'
                    f'border-radius:8px;text-decoration:none;font-weight:bold;display:inline-block">'
                    f'Reset Password</a></p>'
                    f'<p style="color:#666;font-size:14px">This link expires in 1 hour. '
                    f'If you did not request this, you can safely ignore this email.</p>'
                    f'<hr style="border:none;border-top:1px solid #eee;margin:20px 0">'
                    f'<p style="color:#999;font-size:12px">CineGraph - Your Movie & TV Companion</p>'
                    f'</div>'
                )
                plain_text = (
                    f'Hi {user.first_name or "there"},\n\n'
                    f'We received a request to reset your password.\n\n'
                    f'Click here to reset: {reset_link}\n\n'
                    f'This link expires in 1 hour.\n'
                    f'If you did not request this, you can safely ignore this email.'
                )
                send_mail(
                    subject='CineGraph - Reset Your Password',
                    message=plain_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    html_message=html_content,
                    fail_silently=False,
                )
                email_sent = True
                logger.info('Password reset email sent to %s', email)
            except Exception as e:
                logger.error('Failed to send password reset email: %s', e)

        response_data = {
            'success': True,
            'message': 'If an account with that email exists, a reset link has been sent.'
        }

        is_debug = getattr(settings, 'DEBUG', False)
        if is_debug and not email_sent:
            response_data['demo_reset_token'] = combined_token
            response_data['demo_reset_link'] = f'/forget-password?token={combined_token}'

        return Response(response_data)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)

        combined_token = serializer.validated_data['token']
        password = serializer.validated_data['password']

        try:
            uid_b64, token = combined_token.split(':', 1)
        except ValueError:
            return Response({'error': 'Invalid reset link', 'code': 'VALIDATION_ERROR'}, status=400)

        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            user_id = force_str(urlsafe_base64_decode(uid_b64))
            user = User.objects.get(pk=user_id)
        except (ValueError, User.DoesNotExist):
            return Response({'error': 'Invalid reset link', 'code': 'VALIDATION_ERROR'}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Reset link has expired or already been used', 'code': 'VALIDATION_ERROR'}, status=400)

        try:
            validate_password(password, user)
        except DjangoValidationError as e:
            return Response({'error': '; '.join(e.messages), 'code': 'VALIDATION_ERROR'}, status=400)

        user.set_password(password)
        user.save()
        return Response({'success': True, 'message': 'Password successfully reset'})


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

                user.delete()

            return Response({'success': True, 'message': 'Account permanently deleted'})
        except Exception as e:
            logger.error('Error deleting account for user %s: %s', user.id, str(e))
            return Response({'error': 'Failed to delete account', 'code': 'SERVER_ERROR'}, status=500)
