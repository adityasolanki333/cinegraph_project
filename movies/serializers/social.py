from rest_framework import serializers
from movies.models import (
    UserReview, UserFollow, UserList, ListItem,
    ReviewComment, ReviewAward, ReviewInteraction,
    ListFollow, ListCollaborator, ReviewSentimentCache,
)


class UserReviewSerializer(serializers.ModelSerializer):
    tmdbId = serializers.IntegerField(source='tmdb_id')
    mediaType = serializers.CharField(source='media_type')
    posterPath = serializers.CharField(source='poster_path', allow_blank=True, required=False)
    reviewText = serializers.CharField(source='review_text', allow_blank=True, required=False)
    isPublic = serializers.BooleanField(source='is_public', default=True)
    helpfulCount = serializers.IntegerField(source='helpful_count', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', format='iso-8601', read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = UserReview
        fields = [
            'id', 'tmdbId', 'mediaType', 'title', 'posterPath',
            'rating', 'reviewText', 'isPublic', 'helpfulCount',
            'createdAt', 'updatedAt', 'user',
        ]
        read_only_fields = ['id', 'helpfulCount', 'createdAt', 'updatedAt']

    def get_user(self, obj):
        return {
            'id': str(obj.user.id),
            'firstName': obj.user.first_name,
            'lastName': obj.user.last_name,
        }


class CreateReviewSerializer(serializers.Serializer):
    tmdbId = serializers.IntegerField(min_value=1)
    mediaType = serializers.ChoiceField(choices=['movie', 'tv'])
    title = serializers.CharField(max_length=255, default='')
    posterPath = serializers.CharField(max_length=255, allow_blank=True, default='')
    rating = serializers.IntegerField(min_value=1, max_value=10)
    reviewText = serializers.CharField(max_length=5000, allow_blank=True, default='')
    isPublic = serializers.BooleanField(default=True)


class FollowSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    firstName = serializers.SerializerMethodField()
    lastName = serializers.SerializerMethodField()
    followedAt = serializers.DateTimeField(source='created_at', format='iso-8601')

    class Meta:
        model = UserFollow
        fields = ['id', 'firstName', 'lastName', 'followedAt']

    def get_id(self, obj):
        user = obj.follower if self.context.get('direction') == 'follower' else obj.following
        return str(user.id)

    def get_firstName(self, obj):
        user = obj.follower if self.context.get('direction') == 'follower' else obj.following
        return user.first_name

    def get_lastName(self, obj):
        user = obj.follower if self.context.get('direction') == 'follower' else obj.following
        return user.last_name


class FollowUserSerializer(serializers.Serializer):
    targetUserId = serializers.IntegerField()


class ListItemSerializer(serializers.ModelSerializer):
    tmdbId = serializers.IntegerField(source='tmdb_id')
    mediaType = serializers.CharField(source='media_type')
    posterPath = serializers.CharField(source='poster_path', allow_blank=True, required=False)
    addedAt = serializers.DateTimeField(source='added_at', format='iso-8601', read_only=True)

    class Meta:
        model = ListItem
        fields = ['id', 'tmdbId', 'mediaType', 'title', 'posterPath', 'note', 'position', 'addedAt']
        read_only_fields = ['id', 'addedAt']


class CreateListItemSerializer(serializers.Serializer):
    tmdbId = serializers.IntegerField(min_value=1)
    mediaType = serializers.ChoiceField(choices=['movie', 'tv'], default='movie')
    title = serializers.CharField(max_length=255, default='')
    posterPath = serializers.CharField(max_length=255, allow_blank=True, default='')
    note = serializers.CharField(max_length=1000, allow_blank=True, default='')


class UserListSerializer(serializers.ModelSerializer):
    isPublic = serializers.BooleanField(source='is_public')
    followerCount = serializers.IntegerField(source='follower_count', read_only=True)
    itemCount = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', format='iso-8601', read_only=True)
    user = serializers.SerializerMethodField()

    class Meta:
        model = UserList
        fields = ['id', 'title', 'description', 'isPublic', 'followerCount', 'itemCount', 'createdAt', 'updatedAt', 'user']
        read_only_fields = ['id', 'followerCount', 'createdAt', 'updatedAt']

    def get_itemCount(self, obj):
        return obj.items.count()

    def get_user(self, obj):
        profile_url = None
        if hasattr(obj.user, 'profile'):
            profile_url = obj.user.profile.profile_image_url
        return {
            'id': str(obj.user.id),
            'firstName': obj.user.first_name or obj.user.username,
            'lastName': obj.user.last_name,
            'profileImageUrl': profile_url,
        }


class CreateListSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=2000, allow_blank=True, default='')
    isPublic = serializers.BooleanField(default=True)


class UpdateListSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(max_length=2000, allow_blank=True, required=False)
    isPublic = serializers.BooleanField(required=False)


class ReviewCommentSerializer(serializers.ModelSerializer):
    userId = serializers.SerializerMethodField()
    userName = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601')

    class Meta:
        model = ReviewComment
        fields = ['id', 'userId', 'userName', 'comment', 'createdAt']

    def get_userId(self, obj):
        return str(obj.user.id)

    def get_userName(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class ReviewAwardSerializer(serializers.ModelSerializer):
    awardType = serializers.CharField(source='award_type')
    createdAt = serializers.DateTimeField(source='created_at', format='iso-8601')

    class Meta:
        model = ReviewAward
        fields = ['id', 'awardType', 'createdAt']


class ListCollaboratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListCollaborator
        fields = ['id', 'user', 'permission', 'accepted', 'invited_at']
