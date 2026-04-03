"""
Management command to seed demo user with sample data for ML recommendations
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random


class Command(BaseCommand):
    help = 'Seed demo_user with sample watchlist, favorites, ratings, and viewing history'

    def handle(self, *args, **options):
        from movies.models import (
            UserWatchlist, UserFavorites, UserReview, 
            ViewingHistory, UserPreferences
        )
        
        demo_user, created = User.objects.get_or_create(
            username='demo_user',
            defaults={'email': 'demo@cinesuggest.com'}
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created demo_user'))
        else:
            self.stdout.write('demo_user already exists')
        
        sample_movies = [
            {'tmdb_id': 550, 'title': 'Fight Club', 'media_type': 'movie'},
            {'tmdb_id': 13, 'title': 'Forrest Gump', 'media_type': 'movie'},
            {'tmdb_id': 155, 'title': 'The Dark Knight', 'media_type': 'movie'},
            {'tmdb_id': 238, 'title': 'The Godfather', 'media_type': 'movie'},
            {'tmdb_id': 680, 'title': 'Pulp Fiction', 'media_type': 'movie'},
            {'tmdb_id': 120, 'title': 'The Lord of the Rings: The Fellowship of the Ring', 'media_type': 'movie'},
            {'tmdb_id': 278, 'title': 'The Shawshank Redemption', 'media_type': 'movie'},
            {'tmdb_id': 27205, 'title': 'Inception', 'media_type': 'movie'},
            {'tmdb_id': 603, 'title': 'The Matrix', 'media_type': 'movie'},
            {'tmdb_id': 157336, 'title': 'Interstellar', 'media_type': 'movie'},
            {'tmdb_id': 807, 'title': 'Se7en', 'media_type': 'movie'},
            {'tmdb_id': 244786, 'title': 'Whiplash', 'media_type': 'movie'},
            {'tmdb_id': 11, 'title': 'Star Wars: Episode IV - A New Hope', 'media_type': 'movie'},
            {'tmdb_id': 389, 'title': '12 Angry Men', 'media_type': 'movie'},
            {'tmdb_id': 496243, 'title': 'Parasite', 'media_type': 'movie'},
        ]
        
        sample_tv = [
            {'tmdb_id': 1396, 'title': 'Breaking Bad', 'media_type': 'tv'},
            {'tmdb_id': 1399, 'title': 'Game of Thrones', 'media_type': 'tv'},
            {'tmdb_id': 66732, 'title': 'Stranger Things', 'media_type': 'tv'},
            {'tmdb_id': 1402, 'title': 'The Walking Dead', 'media_type': 'tv'},
            {'tmdb_id': 60735, 'title': 'The Flash', 'media_type': 'tv'},
        ]
        
        all_content = sample_movies + sample_tv
        
        watchlist_count = 0
        for item in all_content[:8]:
            obj, created = UserWatchlist.objects.get_or_create(
                user=demo_user,
                tmdb_id=item['tmdb_id'],
                defaults={
                    'title': item['title'],
                    'media_type': item['media_type'],
                    'poster_path': f"/sample_{item['tmdb_id']}.jpg"
                }
            )
            if created:
                watchlist_count += 1
        self.stdout.write(f'Added {watchlist_count} items to watchlist')
        
        favorites_count = 0
        for item in all_content[3:10]:
            obj, created = UserFavorites.objects.get_or_create(
                user=demo_user,
                tmdb_id=item['tmdb_id'],
                defaults={
                    'title': item['title'],
                    'media_type': item['media_type'],
                    'poster_path': f"/sample_{item['tmdb_id']}.jpg"
                }
            )
            if created:
                favorites_count += 1
        self.stdout.write(f'Added {favorites_count} items to favorites')
        
        reviews_count = 0
        for i, item in enumerate(all_content[:12]):
            rating = random.choice([7, 8, 8, 9, 9, 9, 10, 10])
            obj, created = UserReview.objects.get_or_create(
                user=demo_user,
                tmdb_id=item['tmdb_id'],
                defaults={
                    'title': item['title'],
                    'media_type': item['media_type'],
                    'rating': rating,
                    'review_text': f"Great {item['media_type']}! Really enjoyed this one.",
                    'created_at': timezone.now() - timedelta(days=random.randint(1, 60))
                }
            )
            if created:
                reviews_count += 1
        self.stdout.write(f'Added {reviews_count} reviews')
        
        history_count = 0
        for i, item in enumerate(all_content[:10]):
            obj, created = ViewingHistory.objects.get_or_create(
                user=demo_user,
                tmdb_id=item['tmdb_id'],
                defaults={
                    'title': item['title'],
                    'media_type': item['media_type'],
                    'watch_duration': random.randint(80, 150),
                    'poster_path': f"/sample_{item['tmdb_id']}.jpg"
                }
            )
            if created:
                history_count += 1
        self.stdout.write(f'Added {history_count} viewing history entries')
        
        prefs, created = UserPreferences.objects.get_or_create(
            user=demo_user,
            defaults={
                'preferred_genres': ['Action', 'Drama', 'Thriller', 'Sci-Fi'],
                'disliked_genres': ['Horror', 'Musical'],
                'preferred_decades': ['2010s', '2000s', '1990s'],
                'language_preferences': ['en'],
            }
        )
        if created:
            self.stdout.write('Added user preferences')
        
        self.stdout.write(self.style.SUCCESS('\nDemo user data seeded successfully!'))
        self.stdout.write(f'Total: {watchlist_count} watchlist, {favorites_count} favorites, {reviews_count} reviews, {history_count} history')
