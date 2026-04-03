"""
Nightly ETL Pipeline
====================
Django management command that aggregates user activity data into:
  - DiversityMetrics: per-user genre/decade/language diversity stats
  - UserCommunity: ML-driven user segmentation clusters

Usage:
  python manage.py run_nightly_etl
  python manage.py run_nightly_etl --dry-run
"""
import math
from datetime import date, timedelta
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db.models import Count

from movies.models import (
    UserReview, ViewingHistory, UserWatchlist,
    DiversityMetrics, UserCommunity, TmdbMovieCache
)


class Command(BaseCommand):
    help = 'Runs nightly ETL jobs: DiversityMetrics, UserCommunity segmentation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate ETL without writing to the database',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Run ETL for a specific user ID only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        target_user_id = options.get('user_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE: No changes will be written.'))

        # Scope to single user or all users
        if target_user_id:
            users = User.objects.filter(id=target_user_id)
        else:
            users = User.objects.all()

        today = date.today()
        processed = 0
        errors = 0

        self.stdout.write(f'Processing {users.count()} users...')

        for user in users.iterator():
            try:
                self._run_diversity_metrics(user, today, dry_run)
                self._run_community_segmentation(user, dry_run)
                processed += 1
            except Exception as e:
                errors += 1
                self.stderr.write(f'  Error processing user {user.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'ETL complete: {processed} users processed, {errors} errors.'
            )
        )

    # --------------------------------------------------------------------- #
    #  STAGE 1: Diversity Metrics                                            #
    # --------------------------------------------------------------------- #
    def _run_diversity_metrics(self, user, today, dry_run: bool):
        """Compute genre/decade/language diversity for this user."""
        reviews = UserReview.objects.filter(user=user).values('tmdb_id', 'media_type')
        watchlist = UserWatchlist.objects.filter(user=user).values('tmdb_id', 'media_type')
        history = ViewingHistory.objects.filter(user=user).values('tmdb_id', 'media_type')

        # Collect all unique tmdb_ids the user has interacted with
        tmdb_ids = set()
        for qs in (reviews, watchlist, history):
            for item in qs:
                tmdb_ids.add(item['tmdb_id'])

        if not tmdb_ids:
            return  # Nothing to compute

        # Fetch cached metadata
        cached_items = TmdbMovieCache.objects.filter(tmdb_id__in=tmdb_ids)

        genre_counter = Counter()
        decade_counter = Counter()
        lang_counter = Counter()

        for item in cached_items:
            # Genres
            if isinstance(item.genres, list):
                for g in item.genres:
                    name = g.get('name', '') if isinstance(g, dict) else str(g)
                    if name:
                        genre_counter[name] += 1
            # Decade
            if item.release_date and len(item.release_date) >= 4:
                try:
                    year = int(item.release_date[:4])
                    decade = (year // 10) * 10
                    decade_counter[str(decade)] += 1
                except ValueError:
                    pass
            # Language
            if item.original_language:
                lang_counter[item.original_language] += 1

        def shannon_diversity(counter: Counter) -> float:
            """Shannon entropy normalised to [0, 1]."""
            total = sum(counter.values())
            if total == 0 or len(counter) <= 1:
                return 0.0
            entropy = -sum(
                (count / total) * math.log(count / total)
                for count in counter.values()
            )
            max_entropy = math.log(len(counter))
            return round(entropy / max_entropy, 4) if max_entropy > 0 else 0.0

        genre_div = shannon_diversity(genre_counter)
        decade_div = shannon_diversity(decade_counter)
        lang_div = shannon_diversity(lang_counter)
        overall = round((genre_div * 0.5 + decade_div * 0.3 + lang_div * 0.2), 4)

        if not dry_run:
            DiversityMetrics.objects.update_or_create(
                user=user,
                date=today,
                defaults={
                    'genre_diversity': genre_div,
                    'decade_diversity': decade_div,
                    'language_diversity': lang_div,
                    'origin_diversity': lang_div,  # proxy
                    'overall_diversity_score': overall,
                }
            )

        self.stdout.write(
            f'  User {user.id}: genre={genre_div}, decade={decade_div}, lang={lang_div}, overall={overall}'
        )

    # --------------------------------------------------------------------- #
    #  STAGE 2: User Community Segmentation                                  #
    # --------------------------------------------------------------------- #
    def _run_community_segmentation(self, user, dry_run: bool):
        """Assign user to broad community clusters based on top genre."""
        genre_agg = (
            UserReview.objects
            .filter(user=user)
            .values('tmdb_id')
        )
        if not genre_agg:
            return

        tmdb_ids = [r['tmdb_id'] for r in genre_agg]
        cached = TmdbMovieCache.objects.filter(tmdb_id__in=tmdb_ids)

        genre_counter = Counter()
        for item in cached:
            if isinstance(item.genres, list):
                for g in item.genres:
                    name = g.get('name', '') if isinstance(g, dict) else str(g)
                    if name:
                        genre_counter[name] += 1

        if not genre_counter:
            return

        top_genre = genre_counter.most_common(1)[0][0]
        community_name = f'{top_genre} Enthusiasts'
        match_pct = min(100, int((genre_counter[top_genre] / sum(genre_counter.values())) * 100))

        if not dry_run:
            UserCommunity.objects.update_or_create(
                user=user,
                community_name=community_name,
                defaults={
                    'match_percentage': match_pct,
                    'member_count': UserCommunity.objects.filter(
                        community_name=community_name
                    ).count() + 1,
                }
            )

        self.stdout.write(f'  User {user.id} → community: "{community_name}" ({match_pct}% match)')
