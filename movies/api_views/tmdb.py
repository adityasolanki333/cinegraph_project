import json
import random
import hashlib
from datetime import date, timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.cache import cache

from movies.api import tmdb_request, tmdb_request_post, tmdb_request_delete


class TMDBProxyView(APIView):
    permission_classes = [AllowAny]
    endpoint = None
    append_to_response = None

    def get_endpoint(self, **kwargs):
        return self.endpoint

    def get_params(self, request, **kwargs):
        params = {}
        if request.query_params.get('page'):
            params['page'] = request.query_params['page']
        if self.append_to_response:
            params['append_to_response'] = self.append_to_response
        return params

    def get(self, request, **kwargs):
        endpoint = self.get_endpoint(**kwargs)
        params = self.get_params(request, **kwargs)
        cache_key = f"tmdb:{endpoint}:{hashlib.md5(str(sorted((params or {}).items())).encode()).hexdigest()}"
        data = cache.get(cache_key)
        if data is None:
            data = tmdb_request(endpoint, params or None)
            if data:
                cache.set(cache_key, data, 600)  # 10 minutes
        return Response(data)


class TrendingView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/trending/all/{self.request.query_params.get('time_window', 'week')}"


class MoviesPopularView(TMDBProxyView):
    endpoint = "/movie/popular"


class MoviesTopRatedView(TMDBProxyView):
    endpoint = "/movie/top_rated"


class MoviesNowPlayingView(TMDBProxyView):
    endpoint = "/movie/now_playing"


class MoviesUpcomingView(TMDBProxyView):
    endpoint = "/movie/upcoming"


class MovieDetailsView(TMDBProxyView):
    append_to_response = "videos,credits,similar,recommendations"

    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}"


class MovieVideosView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/videos"


class MovieCreditsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/credits"


class MovieWatchProvidersView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/watch/providers"


class MovieSimilarView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/similar"


class MovieRecommendationsTmdbView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/recommendations"


class MovieChangesView(TMDBProxyView):
    endpoint = "/movie/changes"


class MovieReviewsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/reviews"


class MovieImagesView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/images"


class MovieKeywordsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/movie/{kwargs['movie_id']}/keywords"


class TVPopularView(TMDBProxyView):
    endpoint = "/tv/popular"


class TVTopRatedView(TMDBProxyView):
    endpoint = "/tv/top_rated"


class TVAiringTodayView(TMDBProxyView):
    endpoint = "/tv/airing_today"


class TVOnTheAirView(TMDBProxyView):
    endpoint = "/tv/on_the_air"


class TVDetailsView(TMDBProxyView):
    append_to_response = "videos,credits,similar,recommendations"

    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}"


class TVWatchProvidersView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/watch/providers"


class TVSimilarView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/similar"


class TVRecommendationsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/recommendations"


class TVSeasonView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/season/{kwargs['season_number']}"


class TVReviewsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/reviews"


class TVImagesView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/images"


class TVKeywordsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/keywords"


class TVVideosView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/videos"


class TVCreditsView(TMDBProxyView):
    def get_endpoint(self, **kwargs):
        return f"/tv/{kwargs['tv_id']}/credits"


class SearchMultiView(TMDBProxyView):
    endpoint = "/search/multi"

    def get_params(self, request, **kwargs):
        query = request.query_params.get('query', '')
        if not query:
            return None
        return {"query": query, "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class SearchMoviesView(TMDBProxyView):
    endpoint = "/search/movie"

    def get_params(self, request, **kwargs):
        return {"query": request.query_params.get('query', ''), "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class SearchTVView(TMDBProxyView):
    endpoint = "/search/tv"

    def get_params(self, request, **kwargs):
        return {"query": request.query_params.get('query', ''), "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class SearchPeopleView(TMDBProxyView):
    endpoint = "/search/person"

    def get_params(self, request, **kwargs):
        return {"query": request.query_params.get('query', ''), "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class SearchCompaniesView(TMDBProxyView):
    endpoint = "/search/company"

    def get_params(self, request, **kwargs):
        return {"query": request.query_params.get('query', ''), "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class SearchCollectionsView(TMDBProxyView):
    endpoint = "/search/collection"

    def get_params(self, request, **kwargs):
        return {"query": request.query_params.get('query', ''), "page": request.query_params.get('page', 1)}

    def get(self, request, **kwargs):
        if not request.query_params.get('query'):
            return Response({"results": []})
        return super().get(request, **kwargs)


class GenresMovieView(TMDBProxyView):
    endpoint = "/genre/movie/list"

    def get_params(self, request, **kwargs):
        return None


class GenresTVView(TMDBProxyView):
    endpoint = "/genre/tv/list"

    def get_params(self, request, **kwargs):
        return None


class DiscoverMoviesView(TMDBProxyView):
    endpoint = "/discover/movie"

    def get_params(self, request, **kwargs):
        params = {
            "page": request.query_params.get('page', 1),
            "sort_by": request.query_params.get('sort_by', 'popularity.desc'),
        }
        for param in [
            'with_genres', 'with_original_language', 'region',
            'primary_release_year', 'primary_release_date.gte',
            'primary_release_date.lte', 'vote_count.gte', 'vote_average.gte',
        ]:
            value = request.query_params.get(param)
            if value:
                params[param] = value
        if request.query_params.get('year'):
            params['primary_release_year'] = request.query_params['year']
        return params


class DiscoverTVView(TMDBProxyView):
    endpoint = "/discover/tv"

    def get_params(self, request, **kwargs):
        params = {
            "page": request.query_params.get('page', 1),
            "sort_by": request.query_params.get('sort_by', 'popularity.desc'),
        }
        if request.query_params.get('with_genres'):
            params['with_genres'] = request.query_params['with_genres']
        return params


class PersonDetailsView(TMDBProxyView):
    append_to_response = "combined_credits"

    def get_endpoint(self, **kwargs):
        return f"/person/{kwargs['person_id']}"


class CertificationMovieListView(TMDBProxyView):
    endpoint = "/certification/movie/list"

    def get_params(self, request, **kwargs):
        return None


class IndianMoviesView(TMDBProxyView):
    endpoint = "/discover/movie"

    def get_params(self, request, **kwargs):
        return {
            "page": request.query_params.get('page', 1),
            "region": "IN",
            "with_original_language": "hi|ta|te|ml|kn|bn",
            "sort_by": "popularity.desc",
        }


class TMDBConfigurationView(TMDBProxyView):
    endpoint = "/configuration"

    def get_params(self, request, **kwargs):
        return None


MOOD_GENRE_MAP = {
    "happy": [35, 10751, 16],
    "romantic": [10749, 18],
    "energetic": [28, 12, 53],
    "thoughtful": [18, 36, 99],
    "scary": [27, 9648, 53],
    "nostalgic": [10751, 14],
    "animated": [16, 10751],
    "indie": [18, 10749],
}


class MoodRecommendationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, mood):
        genre_ids = MOOD_GENRE_MAP.get(mood, [])
        media_type = request.query_params.get('type', 'movie')
        seed = int(request.query_params.get('seed', 0))

        if not genre_ids:
            return Response({"recommendations": []})

        genre_str = ','.join(map(str, genre_ids[:2]))
        is_movie = media_type == 'movie'
        endpoint = "/discover/movie" if is_movie else "/discover/tv"

        today = date.today().isoformat()
        two_years_ago = (date.today() - timedelta(days=730)).isoformat()
        page = (seed % 5) + 1

        if is_movie:
            params = {
                "with_genres": genre_str,
                "sort_by": "primary_release_date.desc",
                "primary_release_date.gte": two_years_ago,
                "primary_release_date.lte": today,
                "vote_count.gte": 50,
                "page": page,
            }
        else:
            params = {
                "with_genres": genre_str,
                "sort_by": "first_air_date.desc",
                "first_air_date.gte": two_years_ago,
                "first_air_date.lte": today,
                "vote_count.gte": 20,
                "page": page,
            }

        data = tmdb_request(endpoint, params)
        results = data.get("results", []) if data else []
        rng = random.Random(seed)
        rng.shuffle(results)
        return Response({"recommendations": results[:8]})


class RateMovieView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, movie_id):
        rating = request.data.get('value', 5)
        session_id = request.data.get('session_id', '')
        endpoint = f"/movie/{movie_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        data = tmdb_request_post(endpoint, {"value": rating})
        return Response(data)

    def delete(self, request, movie_id):
        session_id = request.query_params.get('session_id', '')
        endpoint = f"/movie/{movie_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        data = tmdb_request_delete(endpoint)
        return Response(data)


class RateTVShowView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, tv_id):
        rating = request.data.get('value', 5)
        session_id = request.data.get('session_id', '')
        endpoint = f"/tv/{tv_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        data = tmdb_request_post(endpoint, {"value": rating})
        return Response(data)

    def delete(self, request, tv_id):
        session_id = request.query_params.get('session_id', '')
        endpoint = f"/tv/{tv_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        data = tmdb_request_delete(endpoint)
        return Response(data)


class GuestSessionView(TMDBProxyView):
    endpoint = "/authentication/guest_session/new"

    def get_params(self, request, **kwargs):
        return None


class RecordInteractionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response({'status': 'ok', 'received': bool(request.data)})
