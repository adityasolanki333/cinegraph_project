import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'movieflix.settings')
django.setup()

from django.contrib.auth.models import User
from movies.models import Club, ClubMember, UserList, ListItem
from django.db import transaction

@transaction.atomic
def seed_data():
    # Ensure we have at least one user
    user, created = User.objects.get_or_create(
        username='cinephile_master',
        defaults={'email': 'cinephile@example.com', 'first_name': 'Cine', 'last_name': 'Phile'}
    )
    user.set_password('password123')
    user.save()

    print("Seeding Clubs...")
    clubs_data = [
        {
            'title': 'Sci-Fi Enthusiasts',
            'description': 'A club for people who love science fiction movies and discussing the future!',
            'cover_image_url': 'https://image.tmdb.org/t/p/w780/628Dep6AxEtDxjZoGP78TsOxYbK.jpg', # Example Star Wars / Sci-fi poster or backdrop
        },
        {
            'title': 'Classic Cinema',
            'description': 'Exploring the golden age of cinema. Black and white, silent films, and early talkies.',
            'cover_image_url': 'https://image.tmdb.org/t/p/w780/5AFe0A6lO6UqQWqA4K20d5q6Rpb.jpg',
        },
        {
            'title': 'Horror Nights',
            'description': 'For those who love to be scared. We watch and discuss the best (and worst) horror films.',
            'cover_image_url': 'https://image.tmdb.org/t/p/w780/iQ5ztdjvteGeboxtmRdXEChJzjI.jpg',
        }
    ]

    for c_data in clubs_data:
        club, created = Club.objects.get_or_create(
            title=c_data['title'],
            defaults={
                'description': c_data['description'],
                'owner': user,
                'cover_image_url': c_data['cover_image_url'],
                'is_public': True,
                'member_count': 1
            }
        )
        if created:
            ClubMember.objects.get_or_create(club=club, user=user, role='admin')
    
    print(f"Total Clubs: {Club.objects.count()}")

    print("Seeding Lists...")
    lists_data = [
        {
            'title': 'Top 10 Sci-Fi Masterpieces',
            'description': 'My personal favorite science fiction films of all time.',
            'items': [
                {'tmdb_id': 157336, 'media_type': 'movie', 'title': 'Interstellar', 'poster_path': '/gEU2QlsUUQZnSn4RbBDeAWjPtX.jpg', 'note': 'Mind-bending.'},
                {'tmdb_id': 603, 'media_type': 'movie', 'title': 'The Matrix', 'poster_path': '/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', 'note': 'A classic.'},
                {'tmdb_id': 278, 'media_type': 'movie', 'title': 'The Shawshank Redemption', 'poster_path': '/9O7gLzmreU0nGkIB6K3BsJbzvNv.jpg', 'note': 'Included because it is just great.'}
            ]
        },
        {
            'title': 'Essential Horror',
            'description': 'Movies to watch on Halloween.',
            'items': [
                {'tmdb_id': 11324, 'media_type': 'movie', 'title': 'Shutter Island', 'poster_path': '/kve20tXwUZpu4GUX8l6X7Z4jmL6.jpg', 'note': 'Thrilling.'},
                {'tmdb_id': 694, 'media_type': 'movie', 'title': 'The Shining', 'poster_path': '/b6ko0IKC8MdYBBPkkA1aBPLe2yz.jpg', 'note': 'Scary.'}
            ]
        }
    ]

    for l_data in lists_data:
        user_list, created = UserList.objects.get_or_create(
            title=l_data['title'],
            user=user,
            defaults={
                'description': l_data['description'],
                'is_public': True,
                'follower_count': 0
            }
        )
        for i, item in enumerate(l_data['items']):
            ListItem.objects.get_or_create(
                list=user_list,
                tmdb_id=item['tmdb_id'],
                media_type=item['media_type'],
                defaults={
                    'title': item['title'],
                    'poster_path': item['poster_path'],
                    'note': item['note'],
                    'position': i
                }
            )

    print(f"Total User Lists: {UserList.objects.count()}")
    print("Seed complete!")

if __name__ == "__main__":
    seed_data()
