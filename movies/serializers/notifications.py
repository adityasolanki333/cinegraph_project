from rest_framework import serializers
from movies.models import Notification, NotificationSettings


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='notification_type')
    relatedUserId = serializers.IntegerField(source='related_user_id', allow_null=True)
    relatedTmdbId = serializers.IntegerField(source='related_tmdb_id', allow_null=True)
    relatedMediaType = serializers.CharField(source='related_media_type', allow_null=True, allow_blank=True)
    isRead = serializers.BooleanField(source='is_read')
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601')

    class Meta:
        model = Notification
        fields = ['id', 'type', 'message', 'relatedUserId', 'relatedTmdbId', 'relatedMediaType', 'isRead', 'createdAt']


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = [
            'email_notifications', 'push_notifications',
            'follow_notifications', 'like_notifications',
            'comment_notifications', 'recommendation_notifications',
            'list_notifications',
        ]
