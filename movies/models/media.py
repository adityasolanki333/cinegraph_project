from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name


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
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_ratings')
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='user_ratings')
    rating = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'movie']
    
    def __str__(self):
        return f"{self.user.email} - {self.movie.title}: {self.rating}"


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


class SearchInteraction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    query = models.CharField(max_length=255)
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
