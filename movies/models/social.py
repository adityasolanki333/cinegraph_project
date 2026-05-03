from django.db import models
from django.contrib.auth.models import User


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
        indexes = [
            models.Index(fields=['user', '-created_at'], name='review_user_created_idx'),
        ]
    
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


class ReviewSentimentCache(models.Model):
    review = models.OneToOneField('UserReview', on_delete=models.CASCADE, related_name='sentiment_cache')
    score = models.FloatField()
    classification = models.CharField(max_length=10)
    analyzed_at = models.DateTimeField(auto_now=True)
