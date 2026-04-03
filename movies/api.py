import requests
import os
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from functools import lru_cache

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')

def get_headers():
    return {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Content-Type": "application/json"
    }

def tmdb_request(endpoint, params=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@require_GET
def trending(request):
    time_window = request.GET.get('time_window', 'week')
    data = tmdb_request(f"/trending/all/{time_window}")
    return JsonResponse(data)

@require_GET
def movies_popular(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/movie/popular", {"page": page})
    return JsonResponse(data)

@require_GET
def movies_top_rated(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/movie/top_rated", {"page": page})
    return JsonResponse(data)

@require_GET
def movies_now_playing(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/movie/now_playing", {"page": page})
    return JsonResponse(data)

@require_GET
def movies_upcoming(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/movie/upcoming", {"page": page})
    return JsonResponse(data)

@require_GET
def movie_details(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}", {"append_to_response": "videos,credits,similar,recommendations"})
    return JsonResponse(data)

@require_GET
def tv_popular(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/tv/popular", {"page": page})
    return JsonResponse(data)

@require_GET
def tv_top_rated(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/tv/top_rated", {"page": page})
    return JsonResponse(data)

@require_GET
def tv_details(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}", {"append_to_response": "videos,credits,similar,recommendations"})
    return JsonResponse(data)

@require_GET
def search_multi(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/multi", {"query": query, "page": page})
    return JsonResponse(data)

@require_GET
def search_movies(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/movie", {"query": query, "page": page})
    return JsonResponse(data)

@require_GET
def search_tv(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/tv", {"query": query, "page": page})
    return JsonResponse(data)

@require_GET
def genres_movie(request):
    data = tmdb_request("/genre/movie/list")
    return JsonResponse(data)

@require_GET
def genres_tv(request):
    data = tmdb_request("/genre/tv/list")
    return JsonResponse(data)

@require_GET
def discover_movies(request):
    params = {
        "page": request.GET.get('page', 1),
        "sort_by": request.GET.get('sort_by', 'popularity.desc'),
    }
    optional_params = [
        'with_genres', 'with_original_language', 'region',
        'primary_release_year', 'primary_release_date.gte',
        'primary_release_date.lte', 'vote_count.gte', 'vote_average.gte',
    ]
    for param in optional_params:
        value = request.GET.get(param)
        if value:
            params[param] = value
    if request.GET.get('year'):
        params['primary_release_year'] = request.GET.get('year')
    data = tmdb_request("/discover/movie", params)
    return JsonResponse(data)

@require_GET
def discover_tv(request):
    params = {
        "page": request.GET.get('page', 1),
        "sort_by": request.GET.get('sort_by', 'popularity.desc'),
    }
    if request.GET.get('with_genres'):
        params['with_genres'] = request.GET.get('with_genres')
    data = tmdb_request("/discover/tv", params)
    return JsonResponse(data)

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

@require_GET
def mood_recommendations(request, mood):
    import random
    genre_ids = MOOD_GENRE_MAP.get(mood, [])
    media_type = request.GET.get('type', 'movie')
    seed = int(request.GET.get('seed', 0))

    if not genre_ids:
        return JsonResponse({"recommendations": []})

    genre_str = ','.join(map(str, genre_ids[:2]))
    endpoint = "/discover/movie" if media_type == 'movie' else "/discover/tv"

    page = (seed % 5) + 1
    data = tmdb_request(endpoint, {
        "with_genres": genre_str,
        "sort_by": "popularity.desc",
        "page": page
    })

    results = data.get("results", [])
    rng = random.Random(seed)
    rng.shuffle(results)

    return JsonResponse({"recommendations": results[:8]})


@require_GET
def tv_airing_today(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/tv/airing_today", {"page": page})
    return JsonResponse(data)


@require_GET
def tv_on_the_air(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/tv/on_the_air", {"page": page})
    return JsonResponse(data)


@require_GET
def movie_videos(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/videos")
    return JsonResponse(data)


@require_GET
def movie_credits(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/credits")
    return JsonResponse(data)


@require_GET
def movie_watch_providers(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/watch/providers")
    return JsonResponse(data)


@require_GET
def tv_watch_providers(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/watch/providers")
    return JsonResponse(data)


@require_GET
def movie_similar(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/similar")
    return JsonResponse(data)


@require_GET
def movie_recommendations_tmdb(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/recommendations")
    return JsonResponse(data)


@require_GET
def tv_similar(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/similar")
    return JsonResponse(data)


@require_GET
def tv_recommendations(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/recommendations")
    return JsonResponse(data)


@require_GET
def tv_season(request, tv_id, season_number):
    data = tmdb_request(f"/tv/{tv_id}/season/{season_number}")
    return JsonResponse(data)


@require_GET
def person_details(request, person_id):
    data = tmdb_request(f"/person/{person_id}", {"append_to_response": "combined_credits"})
    return JsonResponse(data)


@require_GET
def movie_changes(request):
    page = request.GET.get('page', 1)
    data = tmdb_request("/movie/changes", {"page": page})
    return JsonResponse(data)


@require_GET
def certification_movie_list(request):
    data = tmdb_request("/certification/movie/list")
    return JsonResponse(data)


@require_GET
def indian_movies(request):
    page = request.GET.get('page', 1)
    params = {
        "page": page,
        "region": "IN",
        "with_original_language": "hi|ta|te|ml|kn|bn",
        "sort_by": "popularity.desc"
    }
    data = tmdb_request("/discover/movie", params)
    return JsonResponse(data)


@require_GET
def search_people(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/person", {"query": query, "page": page})
    return JsonResponse(data)


@require_GET
def search_companies(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/company", {"query": query, "page": page})
    return JsonResponse(data)


@require_GET
def search_collections(request):
    query = request.GET.get('query', '')
    page = request.GET.get('page', 1)
    if not query:
        return JsonResponse({"results": []})
    data = tmdb_request("/search/collection", {"query": query, "page": page})
    return JsonResponse(data)


@require_GET
def tmdb_configuration(request):
    data = tmdb_request("/configuration")
    return JsonResponse(data)


@require_GET
def movie_reviews(request, movie_id):
    page = request.GET.get('page', 1)
    data = tmdb_request(f"/movie/{movie_id}/reviews", {"page": page})
    return JsonResponse(data)


@require_GET
def movie_images(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/images")
    return JsonResponse(data)


@require_GET
def movie_keywords(request, movie_id):
    data = tmdb_request(f"/movie/{movie_id}/keywords")
    return JsonResponse(data)


@require_GET
def tv_reviews(request, tv_id):
    page = request.GET.get('page', 1)
    data = tmdb_request(f"/tv/{tv_id}/reviews", {"page": page})
    return JsonResponse(data)


@require_GET
def tv_images(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/images")
    return JsonResponse(data)


@require_GET
def tv_keywords(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/keywords")
    return JsonResponse(data)


@require_GET
def tv_videos(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/videos")
    return JsonResponse(data)


@require_GET
def tv_credits(request, tv_id):
    data = tmdb_request(f"/tv/{tv_id}/credits")
    return JsonResponse(data)


def tmdb_request_post(endpoint, body=None):
    """Make POST request to TMDB API"""
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.post(
            url, 
            headers=get_headers(), 
            json=body,
            timeout=10
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def tmdb_request_delete(endpoint):
    """Make DELETE request to TMDB API"""
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.delete(url, headers=get_headers(), timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def rate_movie(request, movie_id):
    """Rate a movie on TMDB (requires guest session)"""
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            rating = body.get('value', 5)
            session_id = body.get('session_id', '')
            
            endpoint = f"/movie/{movie_id}/rating"
            if session_id:
                endpoint = f"{endpoint}?session_id={session_id}"
            
            data = tmdb_request_post(endpoint, {"value": rating})
            return JsonResponse(data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    elif request.method == 'DELETE':
        session_id = request.GET.get('session_id', '')
        endpoint = f"/movie/{movie_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        
        data = tmdb_request_delete(endpoint)
        return JsonResponse(data)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def rate_tv_show(request, tv_id):
    """Rate a TV show on TMDB (requires guest session)"""
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            rating = body.get('value', 5)
            session_id = body.get('session_id', '')
            
            endpoint = f"/tv/{tv_id}/rating"
            if session_id:
                endpoint = f"{endpoint}?session_id={session_id}"
            
            data = tmdb_request_post(endpoint, {"value": rating})
            return JsonResponse(data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    elif request.method == 'DELETE':
        session_id = request.GET.get('session_id', '')
        endpoint = f"/tv/{tv_id}/rating"
        if session_id:
            endpoint = f"{endpoint}?session_id={session_id}"
        
        data = tmdb_request_delete(endpoint)
        return JsonResponse(data)
    else:
        return JsonResponse({"error": "Method not allowed"}, status=405)


@require_GET
def get_guest_session(request):
    """Get a new TMDB guest session for rating"""
    data = tmdb_request("/authentication/guest_session/new")
    return JsonResponse(data)


import json as _json
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def record_interaction(request):
    """Record a search interaction / click feedback for ML training."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        body = _json.loads(request.body)
    except Exception:
        body = {}
    return JsonResponse({'status': 'ok', 'received': bool(body)})
