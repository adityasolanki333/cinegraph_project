import hashlib
import json
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.core.cache import cache

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')
TMDB_CACHE_TTL = int(os.environ.get('TMDB_CACHE_TTL', '300'))

# Persistent session with connection pooling and automatic retries on transient errors
_session = requests.Session()
_retry = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods={"GET"},
    raise_on_status=False,
)
_adapter = HTTPAdapter(
    max_retries=_retry,
    pool_connections=10,
    pool_maxsize=20,
)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def get_headers():
    return {
        "Authorization": f"Bearer {TMDB_API_KEY}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
    }


def _tmdb_cache_key(endpoint, params):
    payload = json.dumps({"e": endpoint, "p": params or {}}, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:48]
    return f"tmdb:v1:{digest}"


def tmdb_request(endpoint, params=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    cache_key = _tmdb_cache_key(endpoint, params)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = _session.get(url, headers=get_headers(), params=params, timeout=10)
        data = response.json()
        if response.ok:
            cache.set(cache_key, data, TMDB_CACHE_TTL)
        return data
    except Exception:
        return {"error": "Failed to fetch data from TMDB"}


def tmdb_request_post(endpoint, body=None):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = _session.post(url, headers=get_headers(), json=body, timeout=10)
        return response.json()
    except Exception:
        return {"error": "Failed to post data to TMDB"}


def tmdb_request_delete(endpoint):
    if not TMDB_API_KEY:
        return {"error": "TMDB API key not configured"}
    url = f"{TMDB_BASE_URL}{endpoint}"
    try:
        response = _session.delete(url, headers=get_headers(), timeout=10)
        return response.json()
    except Exception:
        return {"error": "Failed to delete data from TMDB"}
