from django.core.management.base import BaseCommand
from movies.models import Movie, Genre, UserRating
import random

class Command(BaseCommand):
    help = 'Populate database with sample movies'

    def handle(self, *args, **options):
        genres_data = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Thriller', 'Horror', 'Romance', 'Animation', 'Adventure', 'Fantasy']
        genres = {}
        for name in genres_data:
            genre, _ = Genre.objects.get_or_create(name=name)
            genres[name] = genre

        movies_data = [
            {
                'title': 'The Dark Knight',
                'description': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/hkBaDkMWbLaf8B1lsWsKX7Ew3Xq.jpg',
                'release_year': 2008,
                'rating': 9.0,
                'duration': 152,
                'genres': ['Action', 'Drama', 'Thriller'],
                'director': 'Christopher Nolan',
                'cast': 'Christian Bale, Heath Ledger, Aaron Eckhart, Michael Caine',
                'is_trending': True,
                'is_top_rated': True,
            },
            {
                'title': 'Inception',
                'description': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/9gk7adHYeDvHkCSEqAvQNLV5Ber.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/s3TBrRGB1iav7gFOCNx3H31MoES.jpg',
                'release_year': 2010,
                'rating': 8.8,
                'duration': 148,
                'genres': ['Action', 'Sci-Fi', 'Thriller'],
                'director': 'Christopher Nolan',
                'cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt, Ellen Page, Tom Hardy',
                'is_trending': True,
                'is_top_rated': True,
            },
            {
                'title': 'Interstellar',
                'description': 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/xJHokMbljvjADYdit5fK5VQsXEG.jpg',
                'release_year': 2014,
                'rating': 8.6,
                'duration': 169,
                'genres': ['Adventure', 'Drama', 'Sci-Fi'],
                'director': 'Christopher Nolan',
                'cast': 'Matthew McConaughey, Anne Hathaway, Jessica Chastain',
                'is_trending': True,
                'is_top_rated': True,
            },
            {
                'title': 'The Shawshank Redemption',
                'description': 'Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/kXfqcdQKsToO0OUXHcrrNCHDBzO.jpg',
                'release_year': 1994,
                'rating': 9.3,
                'duration': 142,
                'genres': ['Drama'],
                'director': 'Frank Darabont',
                'cast': 'Tim Robbins, Morgan Freeman, Bob Gunton',
                'is_top_rated': True,
            },
            {
                'title': 'Pulp Fiction',
                'description': 'The lives of two mob hitmen, a boxer, a gangster and his wife, and a pair of diner bandits intertwine in four tales of violence and redemption.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/d5iIlFn5s0ImszYzBPb8JPIfbXD.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/suaEOtk1N1sgg2MTM7oZd2cfVp3.jpg',
                'release_year': 1994,
                'rating': 8.9,
                'duration': 154,
                'genres': ['Drama', 'Thriller'],
                'director': 'Quentin Tarantino',
                'cast': 'John Travolta, Uma Thurman, Samuel L. Jackson',
                'is_top_rated': True,
            },
            {
                'title': 'The Matrix',
                'description': 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/fNG7i7RqMErkcqhohV2a6cV1Ehy.jpg',
                'release_year': 1999,
                'rating': 8.7,
                'duration': 136,
                'genres': ['Action', 'Sci-Fi'],
                'director': 'The Wachowskis',
                'cast': 'Keanu Reeves, Laurence Fishburne, Carrie-Anne Moss',
                'is_top_rated': True,
            },
            {
                'title': 'Avengers: Endgame',
                'description': 'After the devastating events of Infinity War, the universe is in ruins. With the help of remaining allies, the Avengers assemble once more to reverse Thanos actions.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/or06FN3Dka5tukK1e9sl16pB3iy.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/7RyHsO4yDXtBv1zUU3mTpHeQ0d5.jpg',
                'release_year': 2019,
                'rating': 8.4,
                'duration': 181,
                'genres': ['Action', 'Adventure', 'Sci-Fi'],
                'director': 'Anthony Russo, Joe Russo',
                'cast': 'Robert Downey Jr., Chris Evans, Mark Ruffalo, Chris Hemsworth',
                'is_trending': True,
            },
            {
                'title': 'Spider-Man: No Way Home',
                'description': 'With Spider-Mans identity now revealed, Peter asks Doctor Strange for help. When a spell goes wrong, dangerous foes from other worlds start to appear.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/1g0dhYtq4irTY1GPXvft6k4YLjm.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/iQFcwSGbZXMkeyKrxbPnwnRo5fl.jpg',
                'release_year': 2021,
                'rating': 8.3,
                'duration': 148,
                'genres': ['Action', 'Adventure', 'Fantasy'],
                'director': 'Jon Watts',
                'cast': 'Tom Holland, Zendaya, Benedict Cumberbatch',
                'is_trending': True,
                'is_new_release': True,
            },
            {
                'title': 'Dune',
                'description': 'Feature adaptation of Frank Herberts science fiction novel about the son of a noble family entrusted with the protection of the most valuable asset in the galaxy.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/jYEW5xZkZk2WTrdbMGAPFuBqbDc.jpg',
                'release_year': 2021,
                'rating': 8.0,
                'duration': 155,
                'genres': ['Sci-Fi', 'Adventure', 'Drama'],
                'director': 'Denis Villeneuve',
                'cast': 'Timothee Chalamet, Rebecca Ferguson, Oscar Isaac, Zendaya',
                'is_trending': True,
                'is_new_release': True,
            },
            {
                'title': 'Oppenheimer',
                'description': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/rLb2cwF3Pazuxaj0sRXQ037tGI1.jpg',
                'release_year': 2023,
                'rating': 8.5,
                'duration': 180,
                'genres': ['Drama', 'Thriller'],
                'director': 'Christopher Nolan',
                'cast': 'Cillian Murphy, Emily Blunt, Matt Damon, Robert Downey Jr.',
                'is_trending': True,
                'is_new_release': True,
                'is_top_rated': True,
            },
            {
                'title': 'Barbie',
                'description': 'Barbie and Ken are having the time of their lives in the colorful and seemingly perfect world of Barbie Land.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/nHf61UzkfFno5X1ofIhugCPus2R.jpg',
                'release_year': 2023,
                'rating': 7.0,
                'duration': 114,
                'genres': ['Comedy', 'Fantasy', 'Adventure'],
                'director': 'Greta Gerwig',
                'cast': 'Margot Robbie, Ryan Gosling, America Ferrera',
                'is_new_release': True,
            },
            {
                'title': 'John Wick: Chapter 4',
                'description': 'John Wick uncovers a path to defeating The High Table. But before he can earn his freedom, Wick must face off against a new enemy.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/vZloFAK7NmvMGKE7VkF5UHaz0I.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/7I6VUdPj6tQECNHdviJkUHD2u89.jpg',
                'release_year': 2023,
                'rating': 7.8,
                'duration': 169,
                'genres': ['Action', 'Thriller'],
                'director': 'Chad Stahelski',
                'cast': 'Keanu Reeves, Donnie Yen, Bill Skarsgard',
                'is_new_release': True,
            },
            {
                'title': 'The Godfather',
                'description': 'The aging patriarch of an organized crime dynasty transfers control of his clandestine empire to his reluctant son.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/3bhkrj58Vtu7enYsRolD1fZdja1.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/tmU7GeKVybMWFButWEGl2M4GeiP.jpg',
                'release_year': 1972,
                'rating': 9.2,
                'duration': 175,
                'genres': ['Drama', 'Thriller'],
                'director': 'Francis Ford Coppola',
                'cast': 'Marlon Brando, Al Pacino, James Caan',
                'is_top_rated': True,
            },
            {
                'title': 'Fight Club',
                'description': 'An insomniac office worker and a devil-may-care soapmaker form an underground fight club that evolves into something much more.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/hZkgoQYus5vegHoetLkCJzb17zJ.jpg',
                'release_year': 1999,
                'rating': 8.8,
                'duration': 139,
                'genres': ['Drama', 'Thriller'],
                'director': 'David Fincher',
                'cast': 'Brad Pitt, Edward Norton, Helena Bonham Carter',
                'is_top_rated': True,
            },
            {
                'title': 'Forrest Gump',
                'description': 'The presidencies of Kennedy and Johnson, the Vietnam War, and other historical events unfold from the perspective of an Alabama man with an IQ of 75.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/arw2vcBveWOVZr6pxd9XTd1TdQa.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/7c9UVPPiTPltouxRVY6N9uugaVA.jpg',
                'release_year': 1994,
                'rating': 8.8,
                'duration': 142,
                'genres': ['Drama', 'Romance', 'Comedy'],
                'director': 'Robert Zemeckis',
                'cast': 'Tom Hanks, Robin Wright, Gary Sinise',
                'is_top_rated': True,
            },
            {
                'title': 'Parasite',
                'description': 'Greed and class discrimination threaten the newly formed symbiotic relationship between the wealthy Park family and the destitute Kim clan.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/TU9NIjwzjoKPwQHoHshkFcQUCG.jpg',
                'release_year': 2019,
                'rating': 8.6,
                'duration': 132,
                'genres': ['Drama', 'Thriller'],
                'director': 'Bong Joon-ho',
                'cast': 'Song Kang-ho, Lee Sun-kyun, Cho Yeo-jeong',
                'is_top_rated': True,
            },
            {
                'title': 'Spirited Away',
                'description': 'During her familys move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/Ab8mkHmkYADjU7wQiOkia9BzGvS.jpg',
                'release_year': 2001,
                'rating': 8.6,
                'duration': 125,
                'genres': ['Animation', 'Fantasy', 'Adventure'],
                'director': 'Hayao Miyazaki',
                'cast': 'Rumi Hiiragi, Miyu Irino, Mari Natsuki',
                'is_top_rated': True,
            },
            {
                'title': 'The Avengers',
                'description': 'Earths mightiest heroes must come together to stop Loki and his alien army from enslaving humanity.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/RYMX2wcKCBAr24UyPD7xwmjaTn.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/kwUQFeFXOOpgloMgZaadhzkbTI.jpg',
                'release_year': 2012,
                'rating': 8.0,
                'duration': 143,
                'genres': ['Action', 'Adventure', 'Sci-Fi'],
                'director': 'Joss Whedon',
                'cast': 'Robert Downey Jr., Chris Evans, Scarlett Johansson, Chris Hemsworth',
                'is_trending': True,
            },
            {
                'title': 'Joker',
                'description': 'In Gotham City, mentally troubled comedian Arthur Fleck is disregarded and mistreated by society. He then embarks on a downward spiral of revolution and bloody crime.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/n6bUvigpRFqSwmPp1m2YMDNqKpc.jpg',
                'release_year': 2019,
                'rating': 8.4,
                'duration': 122,
                'genres': ['Drama', 'Thriller'],
                'director': 'Todd Phillips',
                'cast': 'Joaquin Phoenix, Robert De Niro, Zazie Beetz',
                'is_top_rated': True,
            },
            {
                'title': 'Get Out',
                'description': 'A young African-American visits his white girlfriends parents for the weekend, where his simmering uneasiness about their reception of him eventually reaches a boiling point.',
                'poster_url': 'https://image.tmdb.org/t/p/w500/qbafy91N3cMwULAo5xxT0jrXrBB.jpg',
                'backdrop_url': 'https://image.tmdb.org/t/p/original/skhX8PqY20fIVUoWVLoP7VY7IH6.jpg',
                'release_year': 2017,
                'rating': 7.7,
                'duration': 104,
                'genres': ['Horror', 'Thriller'],
                'director': 'Jordan Peele',
                'cast': 'Daniel Kaluuya, Allison Williams, Bradley Whitford',
                'is_top_rated': True,
            },
        ]

        for movie_data in movies_data:
            genre_names = movie_data.pop('genres')
            movie, created = Movie.objects.get_or_create(
                title=movie_data['title'],
                defaults=movie_data
            )
            if created:
                for genre_name in genre_names:
                    movie.genres.add(genres[genre_name])
                self.stdout.write(f'Created movie: {movie.title}')
            else:
                self.stdout.write(f'Movie already exists: {movie.title}')

        from django.contrib.auth.models import User
        usernames = ['user1', 'user2', 'user3', 'user4', 'user5']
        all_movies = list(Movie.objects.all())
        for username in usernames:
            user_obj, _ = User.objects.get_or_create(
                username=username,
                defaults={'email': f'{username}@example.com'}
            )
            for movie in random.sample(all_movies, min(10, len(all_movies))):
                UserRating.objects.get_or_create(
                    user=user_obj,
                    movie=movie,
                    defaults={'rating': random.uniform(3.0, 5.0)}
                )

        self.stdout.write(self.style.SUCCESS('Successfully populated database with movies'))
