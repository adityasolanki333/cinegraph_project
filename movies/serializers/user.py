from rest_framework import serializers
from django.contrib.auth.models import User
from movies.models import (
    UserProfile, UserPreferences, UserWatchlist, UserFavorites,
    ViewingHistory, UserActivityStats, UserBadge, UserCommunity,
    DiversityMetrics,
)


class UserBriefSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    firstName = serializers.CharField(source='first_name')
    lastName = serializers.CharField(source='last_name')

    class Meta:
        model = User
        fields = ['id', 'firstName', 'lastName']

    def get_id(self, obj):
        return str(obj.id)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['bio', 'profile_image_url', 'created_at', 'updated_at']


class UserPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreferences
        fields = [
            'preferred_genres', 'disliked_genres', 'preferred_decades',
            'language_preferences', 'mood_preferences',
        ]


class UserWatchlistSerializer(serializers.ModelSerializer):
    tmdbId = serializers.IntegerField(source='tmdb_id')
    mediaType = serializers.CharField(source='media_type')
    posterPath = serializers.CharField(source='poster_path', allow_blank=True, required=False)
    addedAt = serializers.DateTimeField(source='added_at', format='iso-8601', read_only=True)

    class Meta:
        model = UserWatchlist
        fields = ['id', 'tmdbId', 'mediaType', 'title', 'posterPath', 'addedAt']
        read_only_fields = ['id', 'addedAt']


class CreateWatchlistSerializer(serializers.Serializer):
    tmdbId = serializers.IntegerField(min_value=1)
    mediaType = serializers.ChoiceField(choices=['movie', 'tv'])
    title = serializers.CharField(max_length=255, default='')
    posterPath = serializers.CharField(max_length=255, allow_blank=True, default='')


class UserFavoritesSerializer(serializers.ModelSerializer):
    tmdbId = serializers.IntegerField(source='tmdb_id')
    mediaType = serializers.CharField(source='media_type')
    posterPath = serializers.CharField(source='poster_path', allow_blank=True, required=False)
    addedAt = serializers.DateTimeField(source='added_at', format='iso-8601', read_only=True)

    class Meta:
        model = UserFavorites
        fields = ['id', 'tmdbId', 'mediaType', 'title', 'posterPath', 'addedAt']
        read_only_fields = ['id', 'addedAt']


class CreateFavoritesSerializer(serializers.Serializer):
    tmdbId = serializers.IntegerField(min_value=1)
    mediaType = serializers.ChoiceField(choices=['movie', 'tv'])
    title = serializers.CharField(max_length=255, default='')
    posterPath = serializers.CharField(max_length=255, allow_blank=True, default='')


class ViewingHistorySerializer(serializers.ModelSerializer):
    tmdbId = serializers.IntegerField(source='tmdb_id')
    mediaType = serializers.CharField(source='media_type')
    posterPath = serializers.CharField(source='poster_path', allow_blank=True, required=False)
    watchedAt = serializers.DateTimeField(source='watched_at', format='iso-8601', read_only=True)

    class Meta:
        model = ViewingHistory
        fields = ['id', 'tmdbId', 'mediaType', 'title', 'posterPath', 'watchedAt']
        read_only_fields = ['id', 'watchedAt']


class CreateViewingHistorySerializer(serializers.Serializer):
    tmdbId = serializers.IntegerField(min_value=1)
    mediaType = serializers.ChoiceField(choices=['movie', 'tv'])
    title = serializers.CharField(max_length=255, default='')
    posterPath = serializers.CharField(max_length=255, allow_blank=True, default='')


class UpdateProfileSerializer(serializers.Serializer):
    bio = serializers.CharField(max_length=2000, allow_blank=True, required=False)
    profileImageUrl = serializers.CharField(max_length=10000, allow_blank=True, required=False)
    firstName = serializers.CharField(max_length=150, allow_blank=True, required=False)
    lastName = serializers.CharField(max_length=150, allow_blank=True, required=False)


class UserActivityStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivityStats
        fields = [
            'total_reviews', 'total_lists', 'total_followers', 'total_following',
            'total_awards_given', 'total_awards_received', 'total_comments',
            'user_level', 'experience_points',
        ]


class UserBadgeSerializer(serializers.ModelSerializer):
    earnedAt = serializers.DateTimeField(source='earned_at', format='iso-8601')
    badgeType = serializers.CharField(source='badge_type')

    class Meta:
        model = UserBadge
        fields = ['id', 'badgeType', 'earnedAt']


class DiversityMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiversityMetrics
        fields = [
            'date', 'genre_diversity', 'decade_diversity',
            'language_diversity', 'origin_diversity', 'overall_diversity_score',
        ]
