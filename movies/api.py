import os
import requests

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
    except Exception:
        return {"error": "Failed to fetch data from TMDB"}


def tmdb_request_post(endpoint, body=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.post(url, headers=get_headers(), json=body, timeout=10)
        return response.json()
    except Exception:
        return {"error": "Failed to post data to TMDB"}


def tmdb_request_delete(endpoint):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = requests.delete(url, headers=get_headers(), timeout=10)
        return response.json()
    except Exception:
        return {"error": "Failed to delete data from TMDB"}
