from django.contrib import admin
from django.contrib.auth.models import User
from .models import (
    Genre, Movie, UserRating,
    UserProfile, UserPreferences, UserActivityStats,
    UserWatchlist, UserFavorites, ViewingHistory,
    UserReview, ReviewComment, ReviewAward, ReviewInteraction,
    UserFollow, UserList, ListItem, ListFollow, ListCollaborator,
    Notification, NotificationSettings,
    UserCommunity, UserBadge,
    SentimentAnalytics, DiversityMetrics,
    Recommendation, RecommendationMetrics, RecommendationVote, RecommendationComment,
    UserRecommendation, UserSimilarity,
    FeatureWeight, FeatureContribution,
    UserEmbedding, ItemEmbedding, SemanticEmbedding,
    BanditExperiment, TmdbTrainingData, TmdbMovieCache,
)


class UserRatingInline(admin.TabularInline):
    model = UserRating
    extra = 0
    readonly_fields = ('created_at',)


class ListItemInline(admin.TabularInline):
    model = ListItem
    extra = 0
    readonly_fields = ('added_at',)


class ListFollowInline(admin.TabularInline):
    model = ListFollow
    extra = 0
    readonly_fields = ('created_at',)


class ListCollaboratorInline(admin.TabularInline):
    model = ListCollaborator
    extra = 0
    readonly_fields = ('invited_at',)


class ReviewCommentInline(admin.TabularInline):
    model = ReviewComment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class ReviewAwardInline(admin.TabularInline):
    model = ReviewAward
    extra = 0
    readonly_fields = ('created_at',)


class ReviewInteractionInline(admin.TabularInline):
    model = ReviewInteraction
    extra = 0
    readonly_fields = ('created_at',)


class RecommendationMetricsInline(admin.TabularInline):
    model = RecommendationMetrics
    extra = 0
    readonly_fields = ('created_at',)


class FeatureContributionInline(admin.TabularInline):
    model = FeatureContribution
    extra = 0
    readonly_fields = ('created_at',)


class RecommendationVoteInline(admin.TabularInline):
    model = RecommendationVote
    extra = 0
    readonly_fields = ('created_at',)


class RecommendationCommentInline(admin.TabularInline):
    model = RecommendationComment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'release_year', 'rating', 'duration', 'director', 'is_trending', 'is_top_rated', 'is_new_release', 'created_at')
    list_filter = ('is_trending', 'is_top_rated', 'is_new_release', 'release_year', 'genres')
    search_fields = ('title', 'description', 'director', 'cast')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    filter_horizontal = ('genres',)
    inlines = [UserRatingInline]


@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'movie', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'user__email', 'movie__title')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'bio', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'bio')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserActivityStats)
class UserActivityStatsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_level', 'experience_points', 'total_reviews', 'total_lists', 'total_followers', 'total_following', 'last_activity_at')
    list_filter = ('user_level', 'created_at', 'last_activity_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-experience_points',)
    readonly_fields = ('created_at', 'updated_at', 'last_activity_at')


@admin.register(UserWatchlist)
class UserWatchlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tmdb_id', 'media_type', 'title', 'added_at')
    list_filter = ('media_type', 'added_at')
    search_fields = ('user__username', 'user__email', 'title')
    ordering = ('-added_at',)
    readonly_fields = ('added_at',)


@admin.register(UserFavorites)
class UserFavoritesAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tmdb_id', 'media_type', 'title', 'added_at')
    list_filter = ('media_type', 'added_at')
    search_fields = ('user__username', 'user__email', 'title')
    ordering = ('-added_at',)
    readonly_fields = ('added_at',)


@admin.register(ViewingHistory)
class ViewingHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tmdb_id', 'media_type', 'title', 'watched_at', 'watch_duration')
    list_filter = ('media_type', 'watched_at')
    search_fields = ('user__username', 'user__email', 'title')
    ordering = ('-watched_at',)
    readonly_fields = ('watched_at',)


@admin.register(UserReview)
class UserReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tmdb_id', 'media_type', 'title', 'rating', 'is_public', 'helpful_count', 'created_at')
    list_filter = ('media_type', 'rating', 'is_public', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'review_text')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ReviewCommentInline, ReviewAwardInline, ReviewInteractionInline]


@admin.register(ReviewComment)
class ReviewCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'review', 'comment', 'parent_comment', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'comment')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewAward)
class ReviewAwardAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'review', 'award_type', 'created_at')
    list_filter = ('award_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(ReviewInteraction)
class ReviewInteractionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'review', 'interaction_type', 'created_at')
    list_filter = ('interaction_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__username', 'follower__email', 'following__username', 'following__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserList)
class UserListAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'is_public', 'follower_count', 'created_at', 'updated_at')
    list_filter = ('is_public', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__email', 'title', 'description')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ListItemInline, ListFollowInline, ListCollaboratorInline]


@admin.register(ListItem)
class ListItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'list', 'tmdb_id', 'media_type', 'title', 'position', 'added_at')
    list_filter = ('media_type', 'added_at')
    search_fields = ('list__title', 'title')
    ordering = ('list', 'position', '-added_at')
    readonly_fields = ('added_at',)


@admin.register(ListFollow)
class ListFollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'list', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'list__title')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(ListCollaborator)
class ListCollaboratorAdmin(admin.ModelAdmin):
    list_display = ('id', 'list', 'user', 'permission', 'accepted', 'invited_at')
    list_filter = ('permission', 'accepted', 'invited_at')
    search_fields = ('user__username', 'user__email', 'list__title')
    ordering = ('-invited_at',)
    readonly_fields = ('invited_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__email', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'email_notifications', 'push_notifications', 'follow_notifications', 'like_notifications', 'comment_notifications', 'recommendation_notifications', 'list_notifications')
    list_filter = ('email_notifications', 'push_notifications', 'follow_notifications', 'like_notifications', 'comment_notifications')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(UserCommunity)
class UserCommunityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'community_name', 'match_percentage', 'member_count', 'created_at')
    list_filter = ('community_name', 'created_at')
    search_fields = ('user__username', 'user__email', 'community_name')
    ordering = ('-match_percentage',)
    readonly_fields = ('created_at',)


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'badge_type', 'earned_at')
    list_filter = ('badge_type', 'earned_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-earned_at',)
    readonly_fields = ('earned_at',)


@admin.register(SentimentAnalytics)
class SentimentAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('id', 'tmdb_id', 'media_type', 'avg_sentiment_score', 'total_reviews', 'positive_count', 'negative_count', 'neutral_count', 'last_updated')
    list_filter = ('media_type', 'last_updated')
    search_fields = ('tmdb_id',)
    ordering = ('-last_updated',)
    readonly_fields = ('last_updated',)


@admin.register(DiversityMetrics)
class DiversityMetricsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'date', 'genre_diversity', 'decade_diversity', 'language_diversity', 'origin_diversity', 'overall_diversity_score')
    list_filter = ('date', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-date',)
    readonly_fields = ('created_at',)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'tmdb_id', 'media_type', 'title', 'recommendation_type', 'confidence', 'relevance_score', 'user_interacted', 'user_feedback', 'created_at')
    list_filter = ('recommendation_type', 'media_type', 'user_interacted', 'user_feedback', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RecommendationMetricsInline, FeatureContributionInline]


@admin.register(RecommendationMetrics)
class RecommendationMetricsAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation', 'user', 'clicked_at', 'added_to_watchlist', 'actually_watched', 'user_rating', 'effectiveness_score', 'created_at')
    list_filter = ('added_to_watchlist', 'actually_watched', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(RecommendationVote)
class RecommendationVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recommendation', 'vote_type', 'created_at')
    list_filter = ('vote_type', 'created_at')
    search_fields = ('user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(RecommendationComment)
class RecommendationCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recommendation', 'comment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'comment')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserRecommendation)
class UserRecommendationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'for_tmdb_id', 'for_media_type', 'recommended_tmdb_id', 'recommended_media_type', 'recommended_title', 'created_at')
    list_filter = ('for_media_type', 'recommended_media_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'recommended_title', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    inlines = [RecommendationVoteInline, RecommendationCommentInline]


@admin.register(UserSimilarity)
class UserSimilarityAdmin(admin.ModelAdmin):
    list_display = ('id', 'user1', 'user2', 'similarity_score', 'common_movies', 'calculated_at')
    list_filter = ('calculated_at',)
    search_fields = ('user1__username', 'user1__email', 'user2__username', 'user2__email')
    ordering = ('-similarity_score',)
    readonly_fields = ('calculated_at',)


@admin.register(FeatureWeight)
class FeatureWeightAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'feature_name', 'weight', 'success_count', 'total_count', 'success_rate', 'learning_rate', 'last_updated')
    list_filter = ('feature_name', 'last_updated')
    search_fields = ('user__username', 'user__email', 'feature_name')
    ordering = ('-weight',)
    readonly_fields = ('created_at', 'last_updated')


@admin.register(FeatureContribution)
class FeatureContributionAdmin(admin.ModelAdmin):
    list_display = ('id', 'recommendation', 'user', 'feature_name', 'contribution_score', 'feature_value', 'was_successful', 'outcome_type', 'created_at')
    list_filter = ('feature_name', 'was_successful', 'outcome_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'feature_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(UserEmbedding)
class UserEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'embedding_version', 'last_updated', 'created_at')
    list_filter = ('embedding_version', 'last_updated')
    search_fields = ('user__username', 'user__email')
    ordering = ('-last_updated',)
    readonly_fields = ('created_at', 'last_updated')


@admin.register(ItemEmbedding)
class ItemEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('id', 'tmdb_id', 'media_type', 'embedding_version', 'last_updated', 'created_at')
    list_filter = ('media_type', 'embedding_version', 'last_updated')
    search_fields = ('tmdb_id',)
    ordering = ('-last_updated',)
    readonly_fields = ('created_at', 'last_updated')


@admin.register(SemanticEmbedding)
class SemanticEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('id', 'tmdb_id', 'media_type', 'created_at')
    list_filter = ('media_type', 'created_at')
    search_fields = ('tmdb_id', 'text_source')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(BanditExperiment)
class BanditExperimentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'experiment_type', 'arm_chosen', 'reward', 'exploration_rate', 'created_at')
    list_filter = ('experiment_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'arm_chosen')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(TmdbTrainingData)
class TmdbTrainingDataAdmin(admin.ModelAdmin):
    list_display = ('tmdb_id', 'title', 'vote_average', 'vote_count', 'popularity', 'release_date', 'runtime', 'director', 'original_language')
    list_filter = ('original_language', 'status')
    search_fields = ('tmdb_id', 'title', 'original_title', 'director', 'cast', 'genres')
    ordering = ('-popularity',)


@admin.register(TmdbMovieCache)
class TmdbMovieCacheAdmin(admin.ModelAdmin):
    list_display = ('id', 'tmdb_id', 'media_type', 'title', 'vote_average', 'vote_count', 'popularity', 'release_date', 'original_language', 'adult', 'created_at')
    list_filter = ('media_type', 'original_language', 'adult', 'created_at', 'updated_at')
    search_fields = ('tmdb_id', 'title', 'overview')
    ordering = ('-popularity',)
    readonly_fields = ('created_at', 'updated_at')
