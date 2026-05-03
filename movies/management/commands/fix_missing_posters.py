import os
from django.core.management.base import BaseCommand
from movies.models import UserReview, ListItem, ViewingHistory, UserFavorites, UserWatchlist
from movies.api import tmdb_request

class Command(BaseCommand):
    help = 'Backfills missing poster_path for cinema models using TMDB API'

    def handle(self, *args, **options):
        models_to_check = [UserReview, ListItem, ViewingHistory, UserFavorites, UserWatchlist]
        total_updated = 0

        for model in models_to_check:
            # Filter for empty or null poster_path
            objs = model.objects.filter(poster_path__in=['', None])
            count = objs.count()
            self.stdout.write(f"Checking {model.__name__}: {count} records found with missing posters.")

            if count == 0:
                continue

            for obj in objs:
                media_type = getattr(obj, 'media_type', 'movie') # Default to movie if not present
                tmdb_id = obj.tmdb_id
                
                self.stdout.write(f"  Fetching for {obj.title} ({media_type} {tmdb_id})...")
                
                endpoint = f"/{media_type}/{tmdb_id}"
                data = tmdb_request(endpoint)
                
                if 'poster_path' in data and data['poster_path']:
                    obj.poster_path = data['poster_path']
                    obj.save()
                    total_updated += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✅ Updated {model.__name__} {obj.id}: {obj.title}"))
                else:
                    self.stdout.write(self.style.WARNING(f"    ❌ Could not find poster for {model.__name__} {obj.id}: {obj.title}"))

        self.stdout.write(self.style.SUCCESS(f"\nCompleted! Total updated: {total_updated} posters."))
