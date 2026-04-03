import logging
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from movies.models import Notification, NotificationSettings
from movies.serializers.notifications import NotificationSerializer
from movies.pagination import StandardPagePagination

logger = logging.getLogger(__name__)


class NotificationsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def list(self, request, *args, **kwargs):
        user_id = self.kwargs['user_id']
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        notifications = Notification.objects.filter(user=request.user)[:50]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        serializer = self.get_serializer(notifications, many=True)
        return Response({
            'notifications': serializer.data,
            'unreadCount': unread_count,
        })


class MarkNotificationsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        notification_ids = request.data.get('notificationIds', [])
        if notification_ids:
            Notification.objects.filter(user=request.user, id__in=notification_ids).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user).update(is_read=True)
        return Response({'success': True})


class CommunityNotificationsView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardPagePagination

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get('unreadOnly', '').lower() == 'true'
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CommunityMarkNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, notification_id):
        updated = Notification.objects.filter(user=request.user, id=notification_id).update(is_read=True)
        if not updated:
            return Response({'error': 'Notification not found', 'code': 'NOT_FOUND'}, status=404)
        return Response({'success': True})


class CommunityMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        Notification.objects.filter(user=request.user).update(is_read=True)
        return Response({'success': True})


class CommunityDeleteNotificationView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        deleted, _ = Notification.objects.filter(
            user=request.user, id=self.kwargs['notification_id']
        ).delete()
        if not deleted:
            return Response({'error': 'Notification not found', 'code': 'NOT_FOUND'}, status=404)
        return Response({'success': True})


class UnreadCountView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'count': 0})
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})


class NotificationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        settings, _ = NotificationSettings.objects.get_or_create(user=request.user)
        return Response({
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


class UpdateNotificationSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if str(request.user.id) != str(user_id):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        settings, _ = NotificationSettings.objects.get_or_create(user=request.user)
        data = request.data

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

        return Response({
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
