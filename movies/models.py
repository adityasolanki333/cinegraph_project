from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    profile_image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile: {self.user.email}"


class UserWatchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watchlist')
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, db_index=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'tmdb_id', 'media_type']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"


class UserFavorites(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, db_index=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'tmdb_id', 'media_type']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"


class ViewingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='viewing_history')
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, db_index=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    watched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    watch_duration = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-watched_at']
    
    def __str__(self):
        return f"{self.user.email} watched {self.title}"


class UserReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, db_index=True)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    rating = models.IntegerField()
    review_text = models.TextField(blank=True, default='')
    is_public = models.BooleanField(default=True, db_index=True)
    helpful_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'tmdb_id', 'media_type']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} reviewed {self.title}: {self.rating}/10"


class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['follower', 'following']
    
    def __str__(self):
        return f"{self.follower.email} follows {self.following.email}"


class UserList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lists')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    is_public = models.BooleanField(default=True, db_index=True)
    follower_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.email}'s list: {self.title}"


class ListItem(models.Model):
    list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='items')
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    note = models.TextField(blank=True, default='')
    position = models.IntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['list', 'tmdb_id', 'media_type']
        ordering = ['position', '-added_at']
    
    def __str__(self):
        return f"{self.title} in {self.list.title}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('follow', 'New Follower'),
        ('like', 'Review Liked'),
        ('comment', 'New Comment'),
        ('list_follow', 'List Followed'),
        ('recommendation', 'New Recommendation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, db_index=True)
    message = models.TextField()
    related_user_id = models.IntegerField(null=True, blank=True)
    related_tmdb_id = models.IntegerField(null=True, blank=True, db_index=True)
    related_media_type = models.CharField(max_length=10, blank=True, null=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.user.email}: {self.notification_type}"


class UserPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    preferred_genres = models.JSONField(default=list)
    disliked_genres = models.JSONField(default=list)
    preferred_decades = models.JSONField(default=list)
    language_preferences = models.JSONField(default=list)
    mood_preferences = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Preferences for {self.user.email}"

class Movie(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    poster_url = models.URLField(max_length=500)
    backdrop_url = models.URLField(max_length=500, blank=True, null=True)
    release_year = models.IntegerField()
    rating = models.FloatField(default=0.0)
    duration = models.IntegerField(help_text="Duration in minutes")
    genres = models.ManyToManyField(Genre, related_name='movies')
    trailer_url = models.URLField(max_length=500, blank=True, null=True)
    cast = models.TextField(blank=True, help_text="Comma-separated list of actors")
    director = models.CharField(max_length=255, blank=True)
    is_trending = models.BooleanField(default=False)
    is_top_rated = models.BooleanField(default=False)
    is_new_release = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_cast_list(self):
        if self.cast:
            return [c.strip() for c in self.cast.split(',')]
        return []

class UserRating(models.Model):
    user_id = models.CharField(max_length=100)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='user_ratings')
    rating = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user_id', 'movie']
    
    def __str__(self):
        return f"{self.user_id} - {self.movie.title}: {self.rating}"


class ReviewComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_comments')
    review = models.ForeignKey(UserReview, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on review {self.review.id}"


class ReviewAward(models.Model):
    AWARD_TYPES = [
        ('outstanding', 'Outstanding'),
        ('perfect', 'Perfect'),
        ('great', 'Great'),
        ('helpful', 'Helpful'),
        ('insightful', 'Insightful'),
        ('funny', 'Funny'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_awards')
    review = models.ForeignKey(UserReview, on_delete=models.CASCADE, related_name='awards')
    award_type = models.CharField(max_length=20, choices=AWARD_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'review', 'award_type']
    
    def __str__(self):
        return f"{self.user.email} gave {self.award_type} to review {self.review.id}"


class ReviewInteraction(models.Model):
    INTERACTION_TYPES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
        ('report', 'Report'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_interactions')
    review = models.ForeignKey(UserReview, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'review', 'interaction_type']
    
    def __str__(self):
        return f"{self.user.email} marked review {self.review.id} as {self.interaction_type}"


class ListFollow(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followed_lists')
    list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'list']
    
    def __str__(self):
        return f"{self.user.email} follows list {self.list.title}"


class UserActivityStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='activity_stats')
    total_reviews = models.IntegerField(default=0)
    total_lists = models.IntegerField(default=0)
    total_followers = models.IntegerField(default=0)
    total_following = models.IntegerField(default=0)
    total_awards_given = models.IntegerField(default=0)
    total_awards_received = models.IntegerField(default=0)
    total_comments = models.IntegerField(default=0)
    user_level = models.IntegerField(default=1)
    experience_points = models.IntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Activity stats for {self.user.email}: Level {self.user_level}"
    
    def calculate_level(self):
        xp = self.experience_points
        if xp < 100:
            return 1
        elif xp < 500:
            return 2
        elif xp < 1000:
            return 3
        elif xp < 2500:
            return 4
        elif xp < 5000:
            return 5
        elif xp < 10000:
            return 6
        elif xp < 25000:
            return 7
        elif xp < 50000:
            return 8
        elif xp < 100000:
            return 9
        else:
            return 10


class UserCommunity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='communities')
    community_name = models.CharField(max_length=255)
    match_percentage = models.IntegerField(default=0)
    member_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'community_name']
    
    def __str__(self):
        return f"{self.user.email} in {self.community_name}"


class ReviewSentimentCache(models.Model):
    review = models.OneToOneField('UserReview', on_delete=models.CASCADE, related_name='sentiment_cache')
    score = models.FloatField()
    classification = models.CharField(max_length=10)
    analyzed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sentiment cache for review {self.review_id}: {self.classification}"


class SentimentAnalytics(models.Model):
    tmdb_id = models.IntegerField(db_index=True)
    media_type = models.CharField(max_length=10, db_index=True)
    avg_sentiment_score = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
    positive_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tmdb_id', 'media_type']
    
    def __str__(self):
        return f"Sentiment for {self.tmdb_id} ({self.media_type})"


class UserRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_recommendations')
    for_tmdb_id = models.IntegerField()
    for_media_type = models.CharField(max_length=10)
    recommended_tmdb_id = models.IntegerField()
    recommended_media_type = models.CharField(max_length=10)
    recommended_title = models.CharField(max_length=255)
    recommended_poster_path = models.CharField(max_length=255, blank=True, null=True)
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email}: If you like {self.for_tmdb_id}, watch {self.recommended_title}"


class RecommendationVote(models.Model):
    VOTE_TYPES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_votes')
    recommendation = models.ForeignKey(UserRecommendation, on_delete=models.CASCADE, related_name='votes')
    vote_type = models.CharField(max_length=10, choices=VOTE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'recommendation']
    
    def __str__(self):
        return f"{self.user.email} voted {self.vote_type} on recommendation {self.recommendation.id}"


class RecommendationComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_comments')
    recommendation = models.ForeignKey(UserRecommendation, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.user.email} on recommendation {self.recommendation.id}"


class NotificationSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings')
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    follow_notifications = models.BooleanField(default=True)
    like_notifications = models.BooleanField(default=True)
    comment_notifications = models.BooleanField(default=True)
    recommendation_notifications = models.BooleanField(default=True)
    list_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification settings for {self.user.email}"


class ListCollaborator(models.Model):
    PERMISSION_LEVELS = [
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
        ('admin', 'Admin'),
    ]
    
    list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='collaborators')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collaborated_lists')
    permission = models.CharField(max_length=10, choices=PERMISSION_LEVELS, default='view')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['list', 'user']
    
    def __str__(self):
        return f"{self.user.email} collaborating on {self.list.title}"


class UserBadge(models.Model):
    BADGE_TYPES = [
        ('first_review', 'First Review'),
        ('review_master', 'Review Master'),
        ('list_creator', 'List Creator'),
        ('social_butterfly', 'Social Butterfly'),
        ('movie_buff', 'Movie Buff'),
        ('tv_addict', 'TV Addict'),
        ('critic', 'Critic'),
        ('curator', 'Curator'),
        ('trendsetter', 'Trendsetter'),
        ('influencer', 'Influencer'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge_type = models.CharField(max_length=30, choices=BADGE_TYPES)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'badge_type']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.email} earned {self.badge_type}"


class DiversityMetrics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='diversity_metrics')
    date = models.DateField()
    genre_diversity = models.FloatField(default=0)
    decade_diversity = models.FloatField(default=0)
    language_diversity = models.FloatField(default=0)
    origin_diversity = models.FloatField(default=0)
    overall_diversity_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Diversity metrics for {self.user.email} on {self.date}"


class Recommendation(models.Model):
    RECOMMENDATION_TYPES = [
        ('collaborative', 'Collaborative Filtering'),
        ('content', 'Content-Based'),
        ('ai', 'AI-Generated'),
        ('hybrid', 'Hybrid'),
    ]
    FEEDBACK_CHOICES = [
        ('liked', 'Liked'),
        ('disliked', 'Disliked'),
        ('not_interested', 'Not Interested'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10)
    title = models.CharField(max_length=255)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    reason = models.TextField()
    confidence = models.FloatField()
    relevance_score = models.FloatField()
    user_interacted = models.BooleanField(default=False)
    user_feedback = models.CharField(max_length=20, choices=FEEDBACK_CHOICES, blank=True, null=True)
    ai_explanation = models.TextField(blank=True, null=True)
    source_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recommendation for {self.user.email}: {self.title}"


class RecommendationMetrics(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='metrics')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_metrics')
    clicked_at = models.DateTimeField(blank=True, null=True)
    view_duration = models.IntegerField(blank=True, null=True)
    added_to_watchlist = models.BooleanField(default=False)
    added_to_watchlist_at = models.DateTimeField(blank=True, null=True)
    actually_watched = models.BooleanField(default=False)
    watched_at = models.DateTimeField(blank=True, null=True)
    user_rating = models.IntegerField(blank=True, null=True)
    effectiveness_score = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Metrics for recommendation {self.recommendation.id}"


class UserSimilarity(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarity_as_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='similarity_as_user2')
    similarity_score = models.FloatField()
    common_movies = models.IntegerField()
    calculated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user1', 'user2']
    
    def __str__(self):
        return f"Similarity between {self.user1.id} and {self.user2.id}: {self.similarity_score}"


class FeatureWeight(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feature_weights', blank=True, null=True)
    feature_name = models.CharField(max_length=100)
    weight = models.FloatField(default=0.5)
    success_count = models.IntegerField(default=0)
    total_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0)
    learning_rate = models.FloatField(default=0.1)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'feature_name']
    
    def __str__(self):
        user_str = self.user.email if self.user else 'Global'
        return f"Feature weight {self.feature_name} for {user_str}: {self.weight}"


class FeatureContribution(models.Model):
    OUTCOME_TYPES = [
        ('clicked', 'Clicked'),
        ('watchlisted', 'Added to Watchlist'),
        ('rated_high', 'Rated High'),
        ('ignored', 'Ignored'),
        ('dismissed', 'Dismissed'),
    ]
    
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='feature_contributions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feature_contributions')
    feature_name = models.CharField(max_length=100)
    contribution_score = models.FloatField()
    feature_value = models.FloatField(blank=True, null=True)
    was_successful = models.BooleanField(blank=True, null=True)
    outcome_type = models.CharField(max_length=20, choices=OUTCOME_TYPES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feature {self.feature_name} contribution for recommendation {self.recommendation.id}"


class UserEmbedding(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='embedding')
    embedding = models.JSONField()
    embedding_version = models.CharField(max_length=20, default='v1')
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Embedding for {self.user.email} (version {self.embedding_version})"


class ItemEmbedding(models.Model):
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10)
    embedding = models.JSONField()
    embedding_version = models.CharField(max_length=20, default='v1')
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tmdb_id', 'media_type']
    
    def __str__(self):
        return f"Item embedding for {self.tmdb_id} ({self.media_type})"

class TmdbMovieCache(models.Model):
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10, default='movie')
    title = models.CharField(max_length=255)
    overview = models.TextField(blank=True, null=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)
    backdrop_path = models.CharField(max_length=255, blank=True, null=True)
    release_date = models.CharField(max_length=20, blank=True, null=True)
    genres = models.JSONField(default=list)
    vote_average = models.FloatField(default=0)
    vote_count = models.IntegerField(default=0)
    popularity = models.FloatField(default=0)
    original_language = models.CharField(max_length=10, blank=True, null=True)
    adult = models.BooleanField(default=False)
    cast = models.JSONField(default=list)
    crew = models.JSONField(default=list)
    keywords = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['tmdb_id', 'media_type']
        indexes = [
            models.Index(fields=['tmdb_id']),
            models.Index(fields=['media_type']),
            models.Index(fields=['popularity']),
        ]
    
    def __str__(self):
        return f"TMDB Cache: {self.title} ({self.tmdb_id})"

class SearchInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.CharField(max_length=255) # Normalized lowercase
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10, default='movie')
    action = models.CharField(max_length=20, choices=[('click', 'Click'), ('watch', 'Watch')])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['tmdb_id']),
        ]

    def __str__(self):
        return f"{self.query} -> {self.tmdb_id} ({self.action})"

class Club(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_clubs')
    cover_image_url = models.URLField(max_length=500, blank=True, null=True)
    is_public = models.BooleanField(default=True)
    member_count = models.IntegerField(default=1) # Start with owner
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class ClubMember(models.Model):
    ROLE_CHOICES = [
        ('member', 'Member'),
        ('moderator', 'Moderator'),
        ('admin', 'Admin'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['club', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.club.title}"

class ClubThread(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='threads')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_threads')
    title = models.CharField(max_length=255)
    content = models.TextField()
    view_count = models.IntegerField(default=0)
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', '-updated_at']

    def __str__(self):
        return self.title

class ClubPost(models.Model):
    thread = models.ForeignKey(ClubThread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_posts')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Post by {self.author.username} in {self.thread.title}"

class SemanticEmbedding(models.Model):
    tmdb_id = models.IntegerField()
    media_type = models.CharField(max_length=10)
    embedding = models.JSONField()
    text_source = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['tmdb_id', 'media_type']
    
    def __str__(self):
        return f"Semantic embedding for {self.tmdb_id} ({self.media_type})"

class BanditExperiment(models.Model):
    EXPERIMENT_TYPES = [
        ('epsilon_greedy', 'Epsilon Greedy'),
        ('thompson_sampling', 'Thompson Sampling'),
        ('ucb', 'Upper Confidence Bound'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bandit_experiments')
    experiment_type = models.CharField(max_length=30, choices=EXPERIMENT_TYPES)
    arm_chosen = models.CharField(max_length=100)
    reward = models.FloatField(blank=True, null=True)
    context = models.JSONField(blank=True, null=True)
    exploration_rate = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.experiment_type} - {self.arm_chosen}"

class TmdbTrainingData(models.Model):
    tmdb_id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, blank=True, null=True)
    vote_average = models.FloatField(blank=True, null=True)
    vote_count = models.FloatField(blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    release_date = models.CharField(max_length=20, blank=True, null=True)
    revenue = models.FloatField(blank=True, null=True)
    runtime = models.FloatField(blank=True, null=True)
    budget = models.FloatField(blank=True, null=True)
    imdb_id = models.CharField(max_length=20, blank=True, null=True)
    original_language = models.CharField(max_length=10, blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    popularity = models.FloatField(blank=True, null=True)
    tagline = models.TextField(blank=True, null=True)
    genres = models.TextField(blank=True, null=True)
    production_companies = models.TextField(blank=True, null=True)
    production_countries = models.TextField(blank=True, null=True)
    spoken_languages = models.TextField(blank=True, null=True)
    cast = models.TextField(blank=True, null=True)
    director = models.CharField(max_length=255, blank=True, null=True)
    director_of_photography = models.CharField(max_length=255, blank=True, null=True)
    writers = models.TextField(blank=True, null=True)
    producers = models.TextField(blank=True, null=True)
    music_composer = models.CharField(max_length=255, blank=True, null=True)
    imdb_rating = models.FloatField(blank=True, null=True)
    imdb_votes = models.FloatField(blank=True, null=True)
    poster_path = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['genres']),
            models.Index(fields=['popularity']),
            models.Index(fields=['release_date']),
        ]

    def __str__(self):
        return f"{self.title} ({self.tmdb_id})"