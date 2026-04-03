"""
Management command to download MovieLens small dataset and build the
item-item similarity cache used by the recommendation engine.

Usage:
    python manage.py build_movielens_index
    python manage.py build_movielens_index --rebuild   # force rebuild
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Download MovieLens small dataset and build item-item similarity cache'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rebuild',
            action='store_true',
            default=False,
            help='Force rebuild even if cache already exists',
        )

    def handle(self, *args, **options):
        from movies.ml.movielens_engine import movielens_engine, SIMILARITY_CACHE
        import os

        if options['rebuild']:
            self.stdout.write('Forcing rebuild of similarity cache …')
            movielens_engine.rebuild()
        else:
            if os.path.exists(SIMILARITY_CACHE):
                self.stdout.write(self.style.WARNING(
                    f'Cache already exists at {SIMILARITY_CACHE}\n'
                    'Run with --rebuild to regenerate.'
                ))
                movielens_engine._ensure_loaded()
            else:
                self.stdout.write('Building MovieLens similarity cache …')
                movielens_engine._ensure_loaded()

        if movielens_engine.is_ready():
            self.stdout.write(self.style.SUCCESS(
                f'MovieLens engine ready — {len(movielens_engine._cache)} movies indexed.'
            ))
        else:
            self.stdout.write(self.style.ERROR('MovieLens engine failed to initialise.'))
