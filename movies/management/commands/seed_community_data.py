"""
Management command to seed rich community data:
- 8 realistic users with varied genre preferences
- 60+ cross-user reviews on popular movies & TV shows
- 5 curated lists (Sci-Fi Essentials, Best Crime Dramas, etc.)
- Follow relationships between users
- Viewing history and favorites

Run: python manage.py seed_community_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random


SAMPLE_MOVIES = [
    {'tmdb_id': 550,    'title': 'Fight Club',              'media_type': 'movie', 'genres': ['Drama', 'Thriller']},
    {'tmdb_id': 13,     'title': 'Forrest Gump',            'media_type': 'movie', 'genres': ['Drama', 'Romance']},
    {'tmdb_id': 155,    'title': 'The Dark Knight',         'media_type': 'movie', 'genres': ['Action', 'Crime']},
    {'tmdb_id': 238,    'title': 'The Godfather',           'media_type': 'movie', 'genres': ['Crime', 'Drama']},
    {'tmdb_id': 680,    'title': 'Pulp Fiction',            'media_type': 'movie', 'genres': ['Crime', 'Thriller']},
    {'tmdb_id': 120,    'title': 'The Lord of the Rings: The Fellowship of the Ring', 'media_type': 'movie', 'genres': ['Adventure', 'Fantasy']},
    {'tmdb_id': 278,    'title': 'The Shawshank Redemption', 'media_type': 'movie', 'genres': ['Drama']},
    {'tmdb_id': 27205,  'title': 'Inception',               'media_type': 'movie', 'genres': ['Sci-Fi', 'Thriller']},
    {'tmdb_id': 603,    'title': 'The Matrix',              'media_type': 'movie', 'genres': ['Sci-Fi', 'Action']},
    {'tmdb_id': 157336, 'title': 'Interstellar',            'media_type': 'movie', 'genres': ['Sci-Fi', 'Drama']},
    {'tmdb_id': 807,    'title': 'Se7en',                   'media_type': 'movie', 'genres': ['Crime', 'Thriller']},
    {'tmdb_id': 244786, 'title': 'Whiplash',                'media_type': 'movie', 'genres': ['Drama', 'Music']},
    {'tmdb_id': 11,     'title': 'Star Wars: A New Hope',  'media_type': 'movie', 'genres': ['Sci-Fi', 'Adventure']},
    {'tmdb_id': 389,    'title': '12 Angry Men',            'media_type': 'movie', 'genres': ['Drama']},
    {'tmdb_id': 496243, 'title': 'Parasite',                'media_type': 'movie', 'genres': ['Thriller', 'Drama']},
    {'tmdb_id': 299536, 'title': 'Avengers: Infinity War',  'media_type': 'movie', 'genres': ['Action', 'Sci-Fi']},
    {'tmdb_id': 76341,  'title': 'Mad Max: Fury Road',      'media_type': 'movie', 'genres': ['Action', 'Thriller']},
    {'tmdb_id': 19995,  'title': 'Avatar',                  'media_type': 'movie', 'genres': ['Sci-Fi', 'Adventure']},
    {'tmdb_id': 424,    'title': "Schindler's List",        'media_type': 'movie', 'genres': ['Drama', 'History']},
    {'tmdb_id': 598,    'title': 'City of God',             'media_type': 'movie', 'genres': ['Crime', 'Drama']},
]

SAMPLE_TV = [
    {'tmdb_id': 1396,  'title': 'Breaking Bad',      'media_type': 'tv', 'genres': ['Crime', 'Drama']},
    {'tmdb_id': 1399,  'title': 'Game of Thrones',   'media_type': 'tv', 'genres': ['Fantasy', 'Drama']},
    {'tmdb_id': 66732, 'title': 'Stranger Things',   'media_type': 'tv', 'genres': ['Sci-Fi', 'Horror']},
    {'tmdb_id': 1668,  'title': 'Friends',           'media_type': 'tv', 'genres': ['Comedy']},
    {'tmdb_id': 1418,  'title': 'The Big Bang Theory','media_type': 'tv', 'genres': ['Comedy']},
    {'tmdb_id': 46952, 'title': 'Black Mirror',      'media_type': 'tv', 'genres': ['Sci-Fi', 'Thriller']},
    {'tmdb_id': 1434,  'title': 'Family Guy',        'media_type': 'tv', 'genres': ['Comedy', 'Animation']},
    {'tmdb_id': 57243, 'title': 'Doctor Who',        'media_type': 'tv', 'genres': ['Sci-Fi', 'Adventure']},
]

ALL_CONTENT = SAMPLE_MOVIES + SAMPLE_TV

REVIEW_TEMPLATES = {
    'high': [
        "An absolute masterpiece. One of the best {type}s I've ever seen. The direction, acting, and storytelling all come together perfectly.",
        "This is cinema at its finest. Every scene is crafted with intention and precision. Highly recommended to everyone.",
        "A stunning achievement in filmmaking. The performances are outstanding and the story stays with you long after it ends.",
        "Few {type}s manage to be both entertaining and deeply meaningful. This is one of them. A must-watch.",
        "Completely blew me away. I've watched it three times now and discover something new every time.",
    ],
    'mid': [
        "Solid {type} with some great moments. The pacing could be tighter in the middle sections but overall worth watching.",
        "Good but not great. Has some excellent scenes but loses steam toward the end. Worth watching on a lazy evening.",
        "Enjoyable enough, though it doesn't quite live up to the hype. The lead performance is great though.",
        "Entertaining for what it is. Don't go in expecting a masterpiece and you'll have a good time.",
        "Mixed feelings about this one. Some really inspired sequences let down by a formulaic plot.",
    ],
    'low': [
        "Disappointing. Had high hopes but the execution fell flat. The potential was there but squandered.",
        "Not for me. I can see why others like it but the pacing is too slow and the payoff too minimal.",
        "Overhyped. There are better {type}s in this genre that deserve more attention.",
    ],
}

COMMUNITY_USERS = [
    {
        'username': 'cinephile_alex',
        'first_name': 'Alex', 'last_name': 'Chen',
        'email': 'alex.chen@example.com',
        'preferred_genres': ['Drama', 'Thriller', 'Crime'],
        'bio': 'Film buff with a passion for slow-burn dramas.',
    },
    {
        'username': 'scifi_sarah',
        'first_name': 'Sarah', 'last_name': 'Kim',
        'email': 'sarah.kim@example.com',
        'preferred_genres': ['Sci-Fi', 'Adventure', 'Fantasy'],
        'bio': 'I will watch anything with spaceships.',
    },
    {
        'username': 'comedy_mike',
        'first_name': 'Mike', 'last_name': 'Torres',
        'email': 'mike.torres@example.com',
        'preferred_genres': ['Comedy', 'Animation', 'Action'],
        'bio': 'Life is too short for boring movies!',
    },
    {
        'username': 'horror_luna',
        'first_name': 'Luna', 'last_name': 'Park',
        'email': 'luna.park@example.com',
        'preferred_genres': ['Horror', 'Thriller', 'Mystery'],
        'bio': 'The darker the better.',
    },
    {
        'username': 'indie_james',
        'first_name': 'James', 'last_name': 'Wright',
        'email': 'james.wright@example.com',
        'preferred_genres': ['Drama', 'Romance', 'Documentary'],
        'bio': 'Passionate about world cinema and indie films.',
    },
    {
        'username': 'action_raj',
        'first_name': 'Raj', 'last_name': 'Patel',
        'email': 'raj.patel@example.com',
        'preferred_genres': ['Action', 'Adventure', 'Sci-Fi'],
        'bio': 'Explosions, car chases, and everything in between.',
    },
    {
        'username': 'binge_emma',
        'first_name': 'Emma', 'last_name': 'Liu',
        'email': 'emma.liu@example.com',
        'preferred_genres': ['Drama', 'Crime', 'Fantasy'],
        'bio': 'TV series addict. Currently rewatching Breaking Bad.',
    },
    {
        'username': 'film_noah',
        'first_name': 'Noah', 'last_name': 'Santos',
        'email': 'noah.santos@example.com',
        'preferred_genres': ['History', 'War', 'Drama'],
        'bio': 'History through the lens of great storytelling.',
    },
]

CURATED_LISTS = [
    {
        'title': 'Sci-Fi Essentials 🚀',
        'description': 'The definitive science fiction must-watches. From space opera to existential AI dramas.',
        'tmdb_ids': [27205, 603, 157336, 11, 19995, 46952, 66732, 57243],
        'owner_username': 'scifi_sarah',
    },
    {
        'title': 'Crime Masterpieces 🔍',
        'description': 'The greatest crime films and shows ever made. Moral complexity guaranteed.',
        'tmdb_ids': [238, 680, 155, 807, 1396, 598, 424],
        'owner_username': 'cinephile_alex',
    },
    {
        'title': 'Best of the 2010s Decade 📅',
        'description': 'My picks for the defining movies of the 2010s decade.',
        'tmdb_ids': [496243, 27205, 157336, 244786, 76341, 299536],
        'owner_username': 'binge_emma',
    },
    {
        'title': 'Perfect for a Lazy Sunday ☕',
        'description': 'Movies that are great for a relaxing day — not too intense, just pure enjoyment.',
        'tmdb_ids': [13, 278, 120, 1668, 1418],
        'owner_username': 'comedy_mike',
    },
    {
        'title': 'Dark & Disturbing Picks 🌑',
        'description': 'Films that will make you uncomfortable in the best possible way.',
        'tmdb_ids': [550, 807, 680, 496243, 46952, 66732],
        'owner_username': 'horror_luna',
    },
]


class Command(BaseCommand):
    help = 'Seed rich community data: 8 users, 60+ reviews, 5 curated lists, follow relationships'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Remove existing seeded community users before re-seeding',
        )

    def handle(self, *args, **options):
        from movies.models import (
            UserWatchlist, UserFavorites, UserReview,
            ViewingHistory, UserPreferences, UserList, ListItem,
            UserActivityStats
        )

        if options.get('clear'):
            usernames = [u['username'] for u in COMMUNITY_USERS]
            deleted_count, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(self.style.WARNING(f'Removed {deleted_count} existing community users.'))

        # ── 1. Ensure demo_user exists ──────────────────────────────────────
        demo_user, _ = User.objects.get_or_create(
            username='demo_user',
            defaults={'email': 'demo@cinesuggest.com', 'first_name': 'Demo', 'last_name': 'User'}
        )

        # ── 2. Create community users ───────────────────────────────────────
        created_users = []
        for profile in COMMUNITY_USERS:
            user, created = User.objects.get_or_create(
                username=profile['username'],
                defaults={
                    'email': profile['email'],
                    'first_name': profile['first_name'],
                    'last_name': profile['last_name'],
                }
            )
            if created:
                user.set_password('Cinema2024!')
                user.save()

            # Preferences
            prefs, _ = UserPreferences.objects.get_or_create(
                user=user,
                defaults={
                    'preferred_genres': profile['preferred_genres'],
                    'disliked_genres': [],
                    'preferred_decades': ['2010s', '2000s'],
                    'language_preferences': ['en'],
                }
            )

            # Activity stats
            UserActivityStats.objects.get_or_create(user=user)
            created_users.append(user)

        self.stdout.write(f'Ensured {len(created_users)} community users exist.')

        # ── 3. Create reviews (60+ across all users × popular content) ──────
        review_count = 0
        for content in ALL_CONTENT:
            # Each content item gets reviews from 3-6 random users
            reviewers = random.sample(created_users, min(random.randint(3, 6), len(created_users)))
            for user in reviewers:
                rating = random.choices(
                    [random.randint(7, 10), random.randint(5, 7), random.randint(3, 5)],
                    weights=[70, 20, 10]
                )[0]

                template_key = 'high' if rating >= 8 else ('mid' if rating >= 5 else 'low')
                templates = REVIEW_TEMPLATES[template_key]
                text = random.choice(templates).format(type=content['media_type'])

                _, created = UserReview.objects.get_or_create(
                    user=user,
                    tmdb_id=content['tmdb_id'],
                    defaults={
                        'title': content['title'],
                        'media_type': content['media_type'],
                        'rating': rating,
                        'review_text': text,
                        'is_public': True,
                        'created_at': timezone.now() - timedelta(days=random.randint(1, 180)),
                    }
                )
                if created:
                    review_count += 1

        self.stdout.write(f'Created {review_count} new reviews.')

        # ── 4. Add favorites and viewing history ────────────────────────────
        fav_count = 0
        hist_count = 0
        for user in created_users:
            content_sample = random.sample(ALL_CONTENT, min(8, len(ALL_CONTENT)))
            for content in content_sample[:5]:
                _, created = UserFavorites.objects.get_or_create(
                    user=user,
                    tmdb_id=content['tmdb_id'],
                    defaults={
                        'title': content['title'],
                        'media_type': content['media_type'],
                        'poster_path': '',
                    }
                )
                if created:
                    fav_count += 1

            for content in content_sample:
                _, created = ViewingHistory.objects.get_or_create(
                    user=user,
                    tmdb_id=content['tmdb_id'],
                    defaults={
                        'title': content['title'],
                        'media_type': content['media_type'],
                        'watch_duration': random.randint(60, 150),
                        'poster_path': '',
                    }
                )
                if created:
                    hist_count += 1

        self.stdout.write(f'Added {fav_count} favorites and {hist_count} viewing history entries.')

        # ── 5. Create curated lists with items ─────────────────────────────
        list_count = 0
        for list_data in CURATED_LISTS:
            try:
                owner = User.objects.get(username=list_data['owner_username'])
            except User.DoesNotExist:
                owner = demo_user

            lst, created = UserList.objects.get_or_create(
                user=owner,
                title=list_data['title'],
                defaults={
                    'description': list_data['description'],
                    'is_public': True,
                }
            )
            if created:
                list_count += 1
                # Add items to list
                for pos, tmdb_id in enumerate(list_data['tmdb_ids']):
                    content = next((c for c in ALL_CONTENT if c['tmdb_id'] == tmdb_id), None)
                    if content:
                        ListItem.objects.get_or_create(
                            list=lst,
                            tmdb_id=content['tmdb_id'],
                            media_type=content['media_type'],
                            defaults={
                                'title': content['title'],
                                'poster_path': '',
                                'position': pos,
                            }
                        )

        self.stdout.write(f'Created {list_count} curated lists.')

        # ── 6. Create follow relationships ──────────────────────────────────
        from movies.models import UserFollow
        follow_count = 0
        all_users = [demo_user] + created_users
        for user in created_users:
            # Follow 3-5 other users
            others = [u for u in all_users if u != user]
            to_follow = random.sample(others, min(random.randint(3, 5), len(others)))
            for target in to_follow:
                _, created = UserFollow.objects.get_or_create(
                    follower=user,
                    following=target,
                )
                if created:
                    follow_count += 1

        self.stdout.write(f'Created {follow_count} follow relationships.')

        # ── 7. Update activity stats ────────────────────────────────────────
        for user in created_users:
            stats, _ = UserActivityStats.objects.get_or_create(user=user)
            stats.total_reviews = UserReview.objects.filter(user=user).count()
            stats.total_lists = UserList.objects.filter(user=user).count()
            stats.total_following = user.following.count() if hasattr(user, 'following') else 0
            stats.total_followers = user.followers.count() if hasattr(user, 'followers') else 0
            stats.experience_points = stats.total_reviews * 50 + stats.total_lists * 30 + random.randint(0, 200)
            stats.user_level = stats.calculate_level()
            stats.save()

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Community seed complete!\n'
            f'  • {len(created_users)} community users\n'
            f'  • {review_count} reviews\n'
            f'  • {fav_count} favorites\n'
            f'  • {list_count} curated lists\n'
            f'  • {follow_count} follow relationships\n'
            f'\nCommunity feed, leaderboards, and trending should now be populated.'
        ))
