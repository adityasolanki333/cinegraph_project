"""
Cinema-Guide test suite.
Tests: Auth, TMDB proxy (mocked), Reviews CRUD, Lists CRUD, Watchlist, Community.

Run: python manage.py test movies
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch
import json


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def create_user(username='testuser', password='Secure123!', email='test@cinema.com'):
    return User.objects.create_user(username=username, password=password, email=email,
                                    first_name='Test', last_name='User')


TRENDING_FIXTURE = {
    "page": 1,
    "results": [
        {"id": 27205, "title": "Inception", "media_type": "movie", "vote_average": 8.4},
        {"id": 155, "title": "The Dark Knight", "media_type": "movie", "vote_average": 9.0},
    ],
    "total_pages": 1,
    "total_results": 2,
}

POPULAR_FIXTURE = {
    "page": 1,
    "results": [
        {"id": 550, "title": "Fight Club", "vote_average": 8.4},
    ],
    "total_pages": 1,
    "total_results": 1,
}

SEARCH_FIXTURE = {
    "page": 1,
    "results": [
        {"id": 27205, "title": "Inception", "media_type": "movie", "vote_average": 8.4},
    ],
    "total_pages": 1,
    "total_results": 1,
}

MOVIE_DETAIL_FIXTURE = {
    "id": 27205,
    "title": "Inception",
    "overview": "A thief who steals corporate secrets...",
    "vote_average": 8.4,
    "genres": [{"id": 28, "name": "Action"}],
    "videos": {"results": []},
    "credits": {"cast": [], "crew": []},
    "similar": {"results": []},
    "recommendations": {"results": []},
}

TV_DETAIL_FIXTURE = {
    "id": 1396,
    "name": "Breaking Bad",
    "overview": "A chemistry teacher diagnosed with cancer...",
    "vote_average": 9.5,
    "genres": [{"id": 18, "name": "Drama"}],
    "videos": {"results": []},
    "credits": {"cast": [], "crew": []},
    "similar": {"results": []},
    "recommendations": {"results": []},
}


# ──────────────────────────────────────────────────────────────────────────────
# 1. Authentication Tests
# ──────────────────────────────────────────────────────────────────────────────

class AuthTests(TestCase):
    """Registration, login, logout, session persistence."""

    def setUp(self):
        self.client = Client()

    def test_register_new_user(self):
        """POST /api/auth/register creates a user and returns user data."""
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps({
                'email': 'newuser@cinema.com',
                'password': 'StrongPass123!',
                'firstName': 'New',
                'lastName': 'User',
            }),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertIn('user', data)

    def test_login_valid_credentials(self):
        """POST /api/auth/login with correct credentials returns user object."""
        user = create_user()
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({'email': 'test@cinema.com', 'password': 'Secure123!'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('user', data)

    def test_login_invalid_credentials_rejected(self):
        """POST /api/auth/login with wrong password returns 401."""
        create_user()
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({'email': 'test@cinema.com', 'password': 'wrongpassword'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

    def test_get_current_user_authenticated(self):
        """GET /api/auth/me returns user data when logged in."""
        user = create_user()
        self.client.force_login(user)
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('user', data)

    def test_get_current_user_unauthenticated(self):
        """GET /api/auth/me returns 401 when not logged in."""
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        """POST /api/auth/logout clears session."""
        user = create_user()
        self.client.force_login(user)
        response = self.client.post('/api/auth/logout')
        self.assertIn(response.status_code, [200, 204])
        me_response = self.client.get('/api/auth/me')
        self.assertEqual(me_response.status_code, 401)


# ──────────────────────────────────────────────────────────────────────────────
# 2. TMDB Proxy Tests (Mocked)
# ──────────────────────────────────────────────────────────────────────────────

@patch('movies.api_views.tmdb.tmdb_request')
class TMDBProxyTests(TestCase):
    """Verify TMDB proxy endpoints return expected structure using mocked API."""

    def setUp(self):
        self.client = Client()

    def _get(self, url, **kwargs):
        return self.client.get(url, follow=True, **kwargs)

    def test_trending_movies_returns_results(self, mock_tmdb):
        """GET /api/tmdb/trending returns result list."""
        mock_tmdb.return_value = TRENDING_FIXTURE
        response = self._get('/api/tmdb/trending')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertIsInstance(data['results'], list)
        self.assertEqual(len(data['results']), 2)
        mock_tmdb.assert_called_once()

    def test_popular_movies_returns_results(self, mock_tmdb):
        """GET /api/tmdb/movies/popular returns result list."""
        mock_tmdb.return_value = POPULAR_FIXTURE
        response = self._get('/api/tmdb/movies/popular')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        mock_tmdb.assert_called_once()

    def test_movie_search_returns_results(self, mock_tmdb):
        """GET /api/tmdb/search/multi?query=inception returns matches."""
        mock_tmdb.return_value = SEARCH_FIXTURE
        response = self._get('/api/tmdb/search/multi?query=inception')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        mock_tmdb.assert_called_once()

    def test_movie_detail_returns_id(self, mock_tmdb):
        """GET /api/tmdb/movie/27205 (Inception) returns movie id."""
        mock_tmdb.return_value = MOVIE_DETAIL_FIXTURE
        response = self._get('/api/tmdb/movie/27205')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('id'), 27205)
        mock_tmdb.assert_called_once()

    def test_tv_detail_returns_id(self, mock_tmdb):
        """GET /api/tmdb/tv/1396 (Breaking Bad) returns show id."""
        mock_tmdb.return_value = TV_DETAIL_FIXTURE
        response = self._get('/api/tmdb/tv/1396')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('id'), 1396)
        mock_tmdb.assert_called_once()

    def test_search_empty_query_returns_empty(self, mock_tmdb):
        """GET /api/tmdb/search/multi without query returns empty results."""
        response = self._get('/api/tmdb/search/multi')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['results'], [])
        mock_tmdb.assert_not_called()

    def test_trending_fixture_data_preserved(self, mock_tmdb):
        """Mocked response data is correctly passed through the proxy."""
        mock_tmdb.return_value = TRENDING_FIXTURE
        response = self._get('/api/tmdb/trending')
        data = response.json()
        self.assertEqual(data['results'][0]['title'], 'Inception')
        self.assertEqual(data['results'][1]['title'], 'The Dark Knight')


# ──────────────────────────────────────────────────────────────────────────────
# 3. Reviews CRUD Tests
# ──────────────────────────────────────────────────────────────────────────────

class ReviewsCRUDTests(TestCase):
    """Create, read, and delete reviews."""

    def setUp(self):
        self.client = Client()
        self.user = create_user()
        self.client.force_login(self.user)

    def _post_review(self, tmdb_id=27205, rating=9, review_text='Great movie!'):
        return self.client.post(
            '/api/ratings',
            data=json.dumps({
                'tmdbId': tmdb_id,
                'mediaType': 'movie',
                'title': 'Inception',
                'rating': rating,
                'reviewText': review_text,
            }),
            content_type='application/json'
        )

    def test_create_review(self):
        """POST /api/ratings creates a review and returns it."""
        response = self._post_review()
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertEqual(data.get('rating'), 9)
        self.assertEqual(data.get('tmdbId'), 27205)

    def test_get_reviews_for_movie(self):
        """GET /api/ratings?tmdbId=27205 returns list of reviews."""
        self._post_review()
        response = self.client.get('/api/ratings?tmdbId=27205&mediaType=movie')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        self.assertEqual(data[0]['tmdbId'], 27205)

    def test_create_review_requires_rating(self):
        """POST /api/ratings without rating returns 400."""
        response = self.client.post(
            '/api/ratings',
            data=json.dumps({'tmdbId': 27205, 'mediaType': 'movie', 'title': 'x'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_update_review(self):
        """PUT /api/ratings/:id updates an existing review."""
        create_response = self._post_review(rating=7)
        review_id = create_response.json().get('id')
        self.assertIsNotNone(review_id)

        update_response = self.client.put(
            f'/api/ratings/{review_id}',
            data=json.dumps({'rating': 10, 'review': 'Even better on rewatch!'}),
            content_type='application/json',
            HTTP_X_USER_ID=str(self.user.id)
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json().get('rating'), 10)

    def test_delete_review(self):
        """DELETE /api/ratings/:id removes the review."""
        create_response = self._post_review()
        review_id = create_response.json().get('id')
        self.assertIsNotNone(review_id)

        del_response = self.client.delete(
            f'/api/ratings/{review_id}',
            HTTP_X_USER_ID=str(self.user.id)
        )
        self.assertIn(del_response.status_code, [200, 204])

        # Verify it's gone
        get_response = self.client.get('/api/ratings?tmdbId=27205&mediaType=movie')
        reviews = get_response.json()
        ids = [r['id'] for r in reviews]
        self.assertNotIn(review_id, ids)


# ──────────────────────────────────────────────────────────────────────────────
# 4. Lists CRUD Tests
# ──────────────────────────────────────────────────────────────────────────────

class ListsCRUDTests(TestCase):
    """Create, update, add items, delete lists."""

    def setUp(self):
        self.client = Client()
        self.user = create_user()
        self.client.force_login(self.user)

    def _create_list(self, title='My Sci-Fi List', description='Test list', is_public=True):
        return self.client.post(
            '/api/community/lists',
            data=json.dumps({'title': title, 'description': description, 'isPublic': is_public}),
            content_type='application/json'
        )

    def test_create_list(self):
        """POST /api/community/lists creates a list."""
        response = self._create_list()
        self.assertIn(response.status_code, [200, 201])
        data = response.json()
        self.assertTrue(data.get('success'))
        self.assertIn('list', data)
        self.assertEqual(data['list']['title'], 'My Sci-Fi List')

    def test_add_item_to_list(self):
        """POST /api/community/lists/:id/items adds a movie to a list."""
        create_response = self._create_list()
        list_id = create_response.json()['list']['id']

        add_response = self.client.post(
            f'/api/community/lists/{list_id}/items',
            data=json.dumps({
                'tmdbId': 27205,
                'mediaType': 'movie',
                'title': 'Inception',
            }),
            content_type='application/json'
        )
        self.assertIn(add_response.status_code, [200, 201])
        data = add_response.json()
        self.assertTrue(data.get('success'))

    def test_duplicate_item_not_added_twice(self):
        """Adding same movie to list twice is idempotent (no duplicate)."""
        create_response = self._create_list()
        list_id = create_response.json()['list']['id']

        payload = json.dumps({'tmdbId': 27205, 'mediaType': 'movie', 'title': 'Inception'})
        self.client.post(f'/api/community/lists/{list_id}/items',
                         data=payload, content_type='application/json')
        second = self.client.post(f'/api/community/lists/{list_id}/items',
                                  data=payload, content_type='application/json')
        self.assertEqual(second.json().get('created'), False)

    def test_get_user_lists(self):
        """GET /api/users/:id/lists returns the user's lists."""
        self._create_list(title='List A')
        self._create_list(title='List B')
        response = self.client.get(f'/api/users/{self.user.id}/lists')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        lists = data.get('lists') or data
        self.assertIsInstance(lists, list)
        self.assertGreaterEqual(len(lists), 2)

    def test_delete_list(self):
        """DELETE /api/community/lists/:id removes the list."""
        create_response = self._create_list()
        list_id = create_response.json()['list']['id']

        del_response = self.client.delete(f'/api/community/lists/{list_id}')
        self.assertIn(del_response.status_code, [200, 204])

    def test_create_list_requires_auth(self):
        """POST /api/community/lists returns 401 when unauthenticated."""
        anon_client = Client()
        response = anon_client.post(
            '/api/community/lists',
            data=json.dumps({'title': 'Anon List', 'description': '', 'isPublic': True}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)


# ──────────────────────────────────────────────────────────────────────────────
# 5. Watchlist Tests
# ──────────────────────────────────────────────────────────────────────────────

class WatchlistTests(TestCase):
    """Add, list, and remove watchlist items."""

    def setUp(self):
        self.client = Client()
        self.user = create_user()
        self.client.force_login(self.user)

    def test_add_to_watchlist(self):
        """POST /api/users/:id/watchlist/add adds movie."""
        response = self.client.post(
            f'/api/users/{self.user.id}/watchlist/add',
            data=json.dumps({'tmdbId': 155, 'mediaType': 'movie', 'title': 'The Dark Knight'}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [200, 201])

    def test_get_watchlist(self):
        """GET /api/users/:id/watchlist returns items list."""
        # Add an item first
        self.client.post(
            f'/api/users/{self.user.id}/watchlist/add',
            data=json.dumps({'tmdbId': 155, 'mediaType': 'movie', 'title': 'The Dark Knight'}),
            content_type='application/json'
        )
        response = self.client.get(f'/api/users/{self.user.id}/watchlist')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        items = data.get('items') or data
        self.assertIsInstance(items, list)
        self.assertGreater(len(items), 0)

    def test_watchlist_requires_auth(self):
        """Watchlist endpoints require authentication."""
        anon_client = Client()
        response = anon_client.post(
            f'/api/users/{self.user.id}/watchlist/add',
            data=json.dumps({'tmdbId': 155, 'mediaType': 'movie', 'title': 'x'}),
            content_type='application/json'
        )
        self.assertIn(response.status_code, [401, 403])


# ──────────────────────────────────────────────────────────────────────────────
# 6. Community Feed Tests
# ──────────────────────────────────────────────────────────────────────────────

class CommunityTests(TestCase):
    """Community feed, top reviews, trending endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = create_user()
        self.client.force_login(self.user)

    def test_community_feed_returns_list(self):
        """GET /api/community/community-feed returns a list."""
        response = self.client.get(f'/api/community/community-feed?userId={self.user.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('feed', data)
        self.assertIsInstance(data['feed'], list)

    def test_top_reviews_endpoint(self):
        """GET /api/community/top-reviews returns a list."""
        response = self.client.get('/api/community/top-reviews')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('reviews', data)

    def test_leaderboards_endpoint(self):
        """GET /api/community/leaderboards returns leaderboard data."""
        response = self.client.get('/api/community/leaderboards')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('leaderboard', data)

    def test_trending_endpoint(self):
        """GET /api/community/trending returns a list."""
        response = self.client.get('/api/community/trending')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue('trending' in data or 'results' in data or isinstance(data, list))
