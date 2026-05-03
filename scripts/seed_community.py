import os
import django
import sys
import random
from datetime import timedelta
from django.utils import timezone

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
django.setup()

from django.contrib.auth.models import User
from movies.models import (
    UserProfile, UserReview, UserFollow, ReviewAward, 
    ReviewComment, UserActivityStats, UserList, ListItem,
    Club, ClubMember, ClubThread, ClubPost
)
from django.db import transaction

# Verified TMDB Data
MOCK_MOVIES = [
    {'id': 157336, 'title': 'Interstellar', 'poster': '/gEU2QlsUUQZnSn4RbBDeAWjPtX.jpg'},
    {'id': 27205, 'title': 'Inception', 'poster': '/9gk7Y9C7S96vslv9u9AoHqpFfsU.jpg'},
    {'id': 155, 'title': 'The Dark Knight', 'poster': '/qJ2tW6WMUDp9s1vmsTu4X3Tzhwg.jpg'},
    {'id': 603, 'title': 'The Matrix', 'poster': '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg'},
    {'id': 13, 'title': 'Forrest Gump', 'poster': '/arw2vcBveWOV96mZpSqnE7oioL2.jpg'},
    {'id': 680, 'title': 'Pulp Fiction', 'poster': '/d5iIl9h9FvSiiJuKR0cyCcK0OIy.jpg'},
    {'id': 278, 'title': 'The Shawshank Redemption', 'poster': '/9O7gLzmreU0nGkIB6K3BsJbzvNv.jpg'},
    {'id': 238, 'title': 'The Godfather', 'poster': '/3bhkrjSTWv4ayMNaWpU4ZqTbqCD.jpg'},
    {'id': 122, 'title': 'The Lord of the Rings: The Return of the King', 'poster': '/rCzpEXaMUE6Gzhv3AaeH9qi97ea.jpg'},
    {'id': 424, 'title': "Schindler's List", 'poster': '/sF1U4EUdfy3pBTVpSTpVs9Asv2W.jpg'},
    {'id': 496243, 'title': 'Parasite', 'poster': '/7IiTTp0sXzI8Y9v9He9qZujp9Fv.jpg'},
    {'id': 129, 'title': 'Spirited Away', 'poster': '/39wmItSpsS4X4C3Z2FHqc9CcC1y.jpg'},
    {'id': 372058, 'title': 'Your Name.', 'poster': '/q719p6v8mYv6m9H66I58oH48T9o.jpg'},
    {'id': 299536, 'title': 'Avengers: Infinity War', 'poster': '/7WsyChvgyno9YvM31rO7pPjL0YP.jpg'},
    {'id': 671, 'title': "Harry Potter and the Philosopher's Stone", 'poster': '/wuMc08IPKEatv9rnqXkvTQCp9U6.jpg'},
]

CLUBS_DATA = [
    {
        'title': 'Sci-Fi Enthusiasts',
        'description': 'Exploring the boundaries of time, space, and reality through cinema.',
        'cover': 'https://image.tmdb.org/t/p/w780/628Dep6AxEtDxjZoGP78TsOxYbK.jpg'
    },
    {
        'title': 'The Anime Sanctuary',
        'description': 'From Ghibli masterpieces to modern Shonen blockbusters.',
        'cover': 'https://image.tmdb.org/t/p/w780/7Cc9L5VvO2YvTfU5S5UoXmYo4nS.jpg'
    },
    {
        'title': 'Indie Gems',
        'description': 'Celebrating independent films and unique directorial voices.',
        'cover': 'https://image.tmdb.org/t/p/w780/5AFe0A6lO6UqQWqA4K20d5q6Rpb.jpg'
    },
    {
        'title': 'Horror Nights',
        'description': 'Late-night discussions about jumpscares, slashers, and psychological thrillers.',
        'cover': 'https://image.tmdb.org/t/p/w780/iQ5ztdjvteGeboxtmRdXEChJzjI.jpg'
    },
    {
        'title': 'MCU Collective',
        'description': 'Charting the multiverses of the Marvel Cinematic Universe.',
        'cover': 'https://image.tmdb.org/t/p/w780/wd76S9CBeBAEb39aoxSTFc4U76O.jpg'
    },
    {
        'title': 'Classic Cinema',
        'description': 'Revisiting the golden age of Hollywood and world classics.',
        'cover': 'https://image.tmdb.org/t/p/w780/vGSpGqf1u9Gv2Z6N8P0Z9Lp896.jpg'
    },
    {
        'title': 'Criterion Corner',
        'description': 'For the true cinephiles who appreciate artistic and historically significant films.',
        'cover': 'https://image.tmdb.org/t/p/w780/9GK39mSjST608ueC3z9DbeS6P9.jpg'
    },
    {
        'title': 'Christopher Nolan Fans',
        'description': 'Dissecting non-linear timelines and practical effects.',
        'cover': 'https://image.tmdb.org/t/p/w780/8px99S6S3S3X3f5K8X1m8s9D6n.jpg'
    },
    {
        'title': 'Ghibli Garden',
        'description': 'A peaceful place to talk about Studio Ghibli magic.',
        'cover': 'https://image.tmdb.org/t/p/w780/6MTOn7xM3N2fU7w89UoXmYo4nS.jpg'
    },
    {
        'title': 'K-Drama World',
        'description': 'Latest Korean movies and trending serial films.',
        'cover': 'https://image.tmdb.org/t/p/w780/7m63X0m9XvTfU5S5UoXmYo4nS.jpg'
    },
    {
        'title': 'Action Junkies',
        'description': 'High stakes, high octane, and explosive entertainment.',
        'cover': 'https://image.tmdb.org/t/p/w780/wd76S9CBeBAEb39aoxSTFc4U76O.jpg'
    },
    {
        'title': 'Indie Animation',
        'description': 'Celebrating the art of independent animated storytelling.',
        'cover': 'https://image.tmdb.org/t/p/w780/7Cc9L5VvO2YvTfU5S5UoXmYo4nS.jpg'
    }
]

THREAD_TITLES = [
    "What is your all-time favorite movie in this genre?",
    "Discussion: The ending of {title} was Mind-blowing!",
    "News: Official sequel announced for next year!",
    "Why {title} is a misunderstood masterpiece.",
    "Quick Poll: Which director is the GOAT?",
]

POST_CONTENTS = [
    "I've been thinking about this a lot lately. I think the cinematography was the real star here.",
    "Totally agree! The score by Hans Zimmer really elevated the experience too.",
    "I actually found it a bit overrated, but I can see why people enjoy it.",
    "Does anyone know if there's a 4K Criterion release for this?",
    "The character development was so subtle but effective. Truly great writing.",
]

@transaction.atomic
def seed_community():
    print("Starting Deep Seeding...")
    
    # 1. Create Seed Users
    usernames = ['movie_guru', 'cinema_fanatic', 'the_critic', 'film_buff', 'screen_queen', 'noir_lover', 'sci_fi_geek', 'anime_otaku', 'indie_darling']
    users = []
    
    for uname in usernames:
        email = f'{uname}@example.com'
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                'email': email,
                'first_name': uname.replace('_', ' ').title(),
                'last_name': 'Seed'
            }
        )
        if created or user.username != email:
            user.username = email
            user.email = email
            user.set_password('password123')
            user.save()
        
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'bio': f"Passionate {uname.replace('_', ' ')} sharing cinematic perspectives.",
                'profile_image_url': f"https://api.dicebear.com/7.x/avataaars/svg?seed={uname}"
            }
        )
        UserActivityStats.objects.get_or_create(user=user)
        users.append(user)

    print(f"Created/Verified {len(users)} seed users.")

    # 2. Create Reviews with Verified Posters
    print("Seeding reviews...")
    created_reviews = []
    for user in users:
        movies_to_review = random.sample(MOCK_MOVIES, random.randint(4, 6))
        for movie in movies_to_review:
            review, created = UserReview.objects.get_or_create(
                user=user,
                tmdb_id=movie['id'],
                media_type='movie',
                defaults={
                    'title': movie['title'],
                    'poster_path': movie['poster'],
                    'rating': random.randint(6, 10),
                    'review_text': f"My thoughts on {movie['title']}: " + random.choice([
                        "An absolute masterpiece of modern cinema. The visuals were stunning.",
                        "Truly a classic that everyone should watch at least once.",
                        "The acting was top-notch, especially the lead performance.",
                        "It really makes you think about the themes long after it's over.",
                        "Solid watch for fans of the genre. Recommended!",
                    ]),
                    'is_public': True,
                    'helpful_count': random.randint(0, 100)
                }
            )
            created_reviews.append(review)

    # 3. Create Clubs and Content
    print("Seeding clubs, threads, and posts...")
    for club_info in CLUBS_DATA:
        club, created = Club.objects.get_or_create(
            title=club_info['title'],
            defaults={
                'description': club_info['description'],
                'owner': random.choice(users),
                'cover_image_url': club_info['cover'],
                'member_count': random.randint(10, 500)
            }
        )
        
        # Add members
        potential_members = random.sample(users, random.randint(3, 6))
        for mem in potential_members:
            ClubMember.objects.get_or_create(club=club, user=mem)
        
        # Add Threads
        for _ in range(random.randint(3, 5)):
            thread_title = random.choice(THREAD_TITLES).format(title=random.choice(MOCK_MOVIES)['title'])
            thread = ClubThread.objects.create(
                club=club,
                author=random.choice(potential_members),
                title=thread_title,
                content=random.choice(POST_CONTENTS),
                view_count=random.randint(50, 200)
            )
            
            # Add Posts to Threads
            for _ in range(random.randint(2, 4)):
                ClubPost.objects.create(
                    thread=thread,
                    author=random.choice(potential_members),
                    content=random.choice(POST_CONTENTS)
                )

    # 4. Social Interactions
    print("Seeding social follows and awards...")
    for user in users:
        others = [u for u in users if u != user]
        for target in random.sample(others, random.randint(2, 4)):
            UserFollow.objects.get_or_create(follower=user, following=target)
            
    award_types = ['outstanding', 'perfect', 'great', 'helpful', 'insightful', 'funny']
    for review in created_reviews:
        if random.random() > 0.5:
            for au in random.sample(users, random.randint(1, 4)):
                if au != review.user:
                    ReviewAward.objects.get_or_create(user=au, review=review, award_type=random.choice(award_types))

    # 5. Update Activity Stats
    print("Updating activity stats...")
    for user in users:
        stats = user.activity_stats
        stats.total_reviews = UserReview.objects.filter(user=user).count()
        stats.total_lists = UserList.objects.filter(user=user).count()
        stats.total_followers = UserFollow.objects.filter(following=user).count()
        stats.total_following = UserFollow.objects.filter(follower=user).count()
        stats.total_awards_received = ReviewAward.objects.filter(review__user=user).count()
        stats.experience_points = stats.total_reviews * 30 + stats.total_awards_received * 50 + stats.total_followers * 10
        stats.user_level = stats.calculate_level()
        stats.save()

    print("Seed complete! Community and Clubs are now fully populated.")

if __name__ == "__main__":
    seed_community()
