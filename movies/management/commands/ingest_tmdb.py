import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from tqdm import tqdm

class Command(BaseCommand):
    help = 'Ingest TMDB movies into local SQLite/Postgres DB'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, default='datasets/TMDB_all_movies.csv', help='Path to TMDB CSV')
        parser.add_argument('--limit', type=int, default=10000, help='Number of movies to process (for testing)')
        parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for database bulk upload')

    def handle(self, *args, **options):
        from movies.models import TmdbTrainingData

        # Process Data
        csv_path = options['csv']
        if not os.path.exists(csv_path):
             if os.path.exists(os.path.join(settings.BASE_DIR, csv_path)):
                 csv_path = os.path.join(settings.BASE_DIR, csv_path)
             else:
                 self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
                 return

        self.stdout.write(f"Reading CSV from {csv_path}...")
        
        try:
            df = pd.read_csv(csv_path, usecols=['id', 'title', 'overview', 'vote_average', 'vote_count', 'release_date', 'genres', 'popularity', 'poster_path', 'tagline', 'cast', 'director'])
        except ValueError:
             df = pd.read_csv(csv_path)

        # Filter for quality
        df = df.dropna(subset=['overview', 'title'])
        if 'vote_count' in df.columns:
            df = df[df['vote_count'] > 5]
        
        if options['limit'] and options['limit'] > 0:
            df = df.head(options['limit'])
            
        self.stdout.write(f"Processing {len(df)} movies...")
        
        batch_size = options['batch_size']
        
        for i in tqdm(range(0, len(df), batch_size)):
            batch = df.iloc[i:i+batch_size]
            django_objects = []
            
            for index, row in batch.iterrows():
                try:
                    title = str(row.get('title', ''))
                    overview = str(row.get('overview', ''))
                    genres_str = str(row.get('genres', ''))
                    
                    # Prepare SQL Data
                    django_objects.append(TmdbTrainingData(
                        tmdb_id=int(row['id']),
                        title=title,
                        overview=overview,
                        vote_average=float(row.get('vote_average', 0)),
                        vote_count=float(row.get('vote_count', 0)),
                        release_date=str(row.get('release_date', '')),
                        genres=genres_str,
                        popularity=float(row.get('popularity', 0)) if 'popularity' in row else 0.0,
                        poster_path=str(row.get('poster_path', '')) if 'poster_path' in row else None
                    ))
                except Exception:
                    continue

            # Save to Django DB (Bulk Update/Create)
            if django_objects:
                try:
                    from django.db import connection
                    connection.ensure_connection()
                    
                    TmdbTrainingData.objects.bulk_create(django_objects, ignore_conflicts=True)
                except Exception as e:
                     import traceback
                     self.stdout.write(self.style.ERROR(f"SQL Batch Error: {e}"))
                     self.stdout.write(self.style.ERROR(traceback.format_exc()))

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {len(df)} movies to SQL."))
