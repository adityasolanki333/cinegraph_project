from django.db import models
from django.contrib.auth.models import User


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
