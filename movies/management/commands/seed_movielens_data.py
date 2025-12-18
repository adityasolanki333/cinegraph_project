"""
Management command to seed database with MovieLens ratings data for ML training
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
import csv
import os


class Command(BaseCommand):
    help = 'Seed database with MovieLens small dataset ratings for collaborative filtering'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit-users',
            type=int,
            default=100,
            help='Limit number of users to import (default: 100)'
        )
        parser.add_argument(
            '--limit-ratings',
            type=int,
            default=5000,
            help='Limit total ratings to import (default: 5000)'
        )

    def handle(self, *args, **options):
        from movies.models import UserReview, ViewingHistory
        
        limit_users = options['limit_users']
        limit_ratings = options['limit_ratings']
        
        data_dir = 'ml-latest-small'
        links_file = os.path.join(data_dir, 'links.csv')
        ratings_file = os.path.join(data_dir, 'ratings.csv')
        movies_file = os.path.join(data_dir, 'movies.csv')
        
        if not os.path.exists(links_file):
            self.stdout.write(self.style.ERROR(f'MovieLens data not found. Please download ml-latest-small.zip first.'))
            return
        
        self.stdout.write('Loading MovieLens links (movieId -> tmdbId mapping)...')
        movie_to_tmdb = {}
        with open(links_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = row['movieId']
                tmdb_id = row.get('tmdbId', '')
                if tmdb_id:
                    movie_to_tmdb[movie_id] = int(tmdb_id)
        self.stdout.write(f'Loaded {len(movie_to_tmdb)} movie-to-tmdb mappings')
        
        self.stdout.write('Loading MovieLens movie titles...')
        movie_titles = {}
        with open(movies_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                movie_id = row['movieId']
                title = row['title']
                if ' (' in title:
                    title = title.rsplit(' (', 1)[0]
                movie_titles[movie_id] = title
        self.stdout.write(f'Loaded {len(movie_titles)} movie titles')
        
        self.stdout.write(f'Loading MovieLens ratings (limit: {limit_users} users, {limit_ratings} ratings)...')
        user_ratings = {}
        total_ratings = 0
        with open(ratings_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row['userId']
                movie_id = row['movieId']
                rating = float(row['rating'])
                
                if movie_id not in movie_to_tmdb:
                    continue
                
                if user_id not in user_ratings:
                    if len(user_ratings) >= limit_users:
                        continue
                    user_ratings[user_id] = []
                
                if total_ratings >= limit_ratings:
                    break
                
                user_ratings[user_id].append({
                    'movie_id': movie_id,
                    'tmdb_id': movie_to_tmdb[movie_id],
                    'title': movie_titles.get(movie_id, f'Movie {movie_id}'),
                    'rating': int(rating * 2)
                })
                total_ratings += 1
        
        self.stdout.write(f'Loaded {total_ratings} ratings from {len(user_ratings)} users')
        
        self.stdout.write('Creating users and importing ratings...')
        users_created = 0
        reviews_created = 0
        history_created = 0
        
        with transaction.atomic():
            for ml_user_id, ratings in user_ratings.items():
                username = f'ml_user_{ml_user_id}'
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': f'{username}@movielens.org'}
                )
                if created:
                    users_created += 1
                
                for rating_data in ratings:
                    review, created = UserReview.objects.get_or_create(
                        user=user,
                        tmdb_id=rating_data['tmdb_id'],
                        defaults={
                            'media_type': 'movie',
                            'title': rating_data['title'],
                            'rating': rating_data['rating'],
                            'review_text': '',
                            'is_public': True
                        }
                    )
                    if created:
                        reviews_created += 1
                    
                    if rating_data['rating'] >= 7:
                        history, created = ViewingHistory.objects.get_or_create(
                            user=user,
                            tmdb_id=rating_data['tmdb_id'],
                            defaults={
                                'media_type': 'movie',
                                'title': rating_data['title'],
                                'watch_duration': 120
                            }
                        )
                        if created:
                            history_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'\nMovieLens data seeded successfully!'))
        self.stdout.write(f'  Users created: {users_created}')
        self.stdout.write(f'  Reviews created: {reviews_created}')
        self.stdout.write(f'  Viewing history entries: {history_created}')
        self.stdout.write(f'\nML collaborative filtering now has training data!')
