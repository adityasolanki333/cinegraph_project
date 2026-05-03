from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, default='')
    profile_image_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile: {self.user.email}"


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
        indexes = [
            models.Index(fields=['user', '-added_at'], name='watchlist_user_added_idx'),
        ]
    
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
        indexes = [
            models.Index(fields=['user', '-added_at'], name='favorites_user_added_idx'),
        ]
    
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
        indexes = [
            models.Index(fields=['user', '-watched_at'], name='history_user_watched_idx'),
        ]
    
    def __str__(self):
        return f"{self.user.email} watched {self.title}"


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
