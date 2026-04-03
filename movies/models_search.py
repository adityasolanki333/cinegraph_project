from django.db import models
from django.contrib.auth.models import User

# ... existing models ...

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
