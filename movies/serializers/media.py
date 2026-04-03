from rest_framework import serializers
from movies.models import Genre, Movie, UserRating, TmdbMovieCache, TmdbTrainingData


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            'id', 'title', 'description', 'poster_url', 'backdrop_url',
            'release_year', 'rating', 'duration', 'genres', 'trailer_url',
            'cast', 'director', 'is_trending', 'is_top_rated', 'is_new_release',
        ]


class UserRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRating
        fields = ['id', 'user', 'movie', 'rating', 'created_at']
        read_only_fields = ['created_at']


class TmdbMovieCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = TmdbMovieCache
        fields = '__all__'
