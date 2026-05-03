import json
import os
import re
import time
import random
import hashlib
import requests
import concurrent.futures
import logging
from datetime import datetime, date
from django.core.cache import cache

# ── Cache constants ────────────────────────────────────────────────────────
AI_CHAT_CACHE_TTL = 30 * 60   # 30 min — includes current movies which change daily

def _chat_cache_key(user_id, message: str) -> str:
    """Per-user cache key for chat responses (personalized per user)."""
    uid = str(user_id) if user_id else "anon"
    normalized = " ".join(message.lower().strip().split())
    key_data = f"chat:v3:{uid}:{normalized}"
    return "aichat_" + hashlib.md5(key_data.encode("utf-8")).hexdigest()

from django.http import StreamingHttpResponse
from .models import UserPreferences, UserReview, UserWatchlist, UserFavorites, ViewingHistory
from .api import tmdb_request
from .validation import error_response
from movies.ml.utils import GENRE_MAP as _GENRE_ID_TO_NAME_MAP, GENRE_NAME_TO_ID as _GENRE_NAME_TO_ID_MAP

logger = logging.getLogger(__name__)

TMDB_GENRE_MAP = _GENRE_NAME_TO_ID_MAP

GENRE_ID_TO_NAME = _GENRE_ID_TO_NAME_MAP

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
# Caches the expensive Gemini paragraph on home “Continue watching” / pattern analyze (seconds → ms on repeat).
PATTERN_INSIGHT_CACHE_TTL = int(os.environ.get('PATTERN_INSIGHT_CACHE_TTL', '900'))

_MGMT_COMMANDS = {'migrate', 'makemigrations', 'collectstatic', 'check',
                  'showmigrations', 'sqlmigrate', 'inspectdb', 'shell',
                  'dbshell', 'flush', 'loaddata', 'dumpdata'}
import sys as _sys
_is_mgmt = len(_sys.argv) > 1 and _sys.argv[1] in _MGMT_COMMANDS

gemini_client = None
if not _is_mgmt:
    try:
        from google import genai
        if GEMINI_API_KEY:
            gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini client initialized successfully")
    except ImportError:
        logger.warning("google-genai not installed, using fallback")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}")


def get_user_context(user):
    reviews = UserReview.objects.filter(user=user).order_by('-created_at')[:10]
    watchlist = UserWatchlist.objects.filter(user=user).order_by('-added_at')[:10]
    favorites = UserFavorites.objects.filter(user=user).order_by('-added_at')[:10]
    history = ViewingHistory.objects.filter(user=user).order_by('-watched_at')[:10]

    context = {
        'recent_ratings': [
            {'title': r.title, 'rating': r.rating, 'mediaType': r.media_type}
            for r in reviews
        ],
        'watchlist': [{'title': w.title, 'mediaType': w.media_type} for w in watchlist],
        'favorites': [{'title': f.title, 'mediaType': f.media_type} for f in favorites],
        'recently_watched': [{'title': h.title, 'mediaType': h.media_type} for h in history],
    }

    try:
        prefs = UserPreferences.objects.get(user=user)
        context['preferred_genres'] = prefs.preferred_genres
        context['disliked_genres'] = prefs.disliked_genres
    except UserPreferences.DoesNotExist:
        context['preferred_genres'] = []
        context['disliked_genres'] = []

    return context


_current_movies_cache = {'data': None, 'timestamp': 0}
_CURRENT_MOVIES_TTL = 300

def fetch_current_movies():
    now = time.time()
    if _current_movies_cache['data'] and (now - _current_movies_cache['timestamp']) < _CURRENT_MOVIES_TTL:
        return _current_movies_cache['data']

    def format_movie(item):
        title = item.get('title') or item.get('name', 'Unknown')
        year = ''
        release = item.get('release_date') or item.get('first_air_date', '')
        if release:
            year = release[:4]
        rating = item.get('vote_average', 0)
        genre_ids = item.get('genre_ids', [])
        genres = [GENRE_ID_TO_NAME.get(gid, '') for gid in genre_ids[:3]]
        genres = [g for g in genres if g]
        return f"{title} ({year}) - Rating: {rating}/10 - Genres: {', '.join(genres) if genres else 'N/A'}"

    def fetch_trending():
        try:
            data = tmdb_request("/trending/movie/week")
            return [format_movie(item) for item in data.get('results', [])[:8]]
        except Exception as e:
            logger.warning(f"Failed to fetch trending movies: {e}")
            return []

    def fetch_now_playing():
        try:
            data = tmdb_request("/movie/now_playing", {"page": 1})
            return [format_movie(item) for item in data.get('results', [])[:6]]
        except Exception as e:
            logger.warning(f"Failed to fetch now playing movies: {e}")
            return []

    def fetch_upcoming():
        try:
            data = tmdb_request("/movie/upcoming", {"page": 1})
            return [format_movie(item) for item in data.get('results', [])[:5]]
        except Exception as e:
            logger.warning(f"Failed to fetch upcoming movies: {e}")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        trending_future = executor.submit(fetch_trending)
        now_playing_future = executor.submit(fetch_now_playing)
        upcoming_future = executor.submit(fetch_upcoming)

        result = {
            'trending': trending_future.result(),
            'now_playing': now_playing_future.result(),
            'upcoming': upcoming_future.result(),
        }

    _current_movies_cache['data'] = result
    _current_movies_cache['timestamp'] = time.time()
    return result


GEMINI_MODELS = [
    "gemma-3-27b-it",
]

_model_blacklist = {}
_BLACKLIST_COOLDOWN = 60

def _is_model_available(model):
    if model in _model_blacklist:
        if time.time() - _model_blacklist[model] < _BLACKLIST_COOLDOWN:
            return False
        del _model_blacklist[model]
    return True

def _blacklist_model(model):
    _model_blacklist[model] = time.time()


MOVIE_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"}
                },
                "required": ["title"]
            }
        }
    },
    "required": ["recommendations"]
}


def call_gemini_api(prompt, max_retries=1, use_json_mode=False, json_schema=None):
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    sdk_tried = False
    if gemini_client:
        sdk_tried = True
        for model in GEMINI_MODELS:
            if not _is_model_available(model):
                logger.info(f"Skipping blacklisted model {model}")
                continue
            if use_json_mode and model.startswith("gemma"):
                logger.info(f"Skipping {model} (no JSON mode support)")
                continue
            for attempt in range(max_retries):
                try:
                    sdk_config = {
                        "temperature": 0.7,
                        "max_output_tokens": 2048,
                    }
                    if use_json_mode:
                        sdk_config["response_mime_type"] = "application/json"
                        if json_schema:
                            sdk_config["response_schema"] = json_schema
                    from google.genai import types
                    config = types.GenerateContentConfig(**sdk_config)
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    if response and response.text:
                        logger.info(f"Gemini {model} responded successfully")
                        return response.text, None
                except Exception as e:
                    error_str = str(e).lower()
                    if '429' in error_str or 'quota' in error_str or 'rate' in error_str or 'resource_exhausted' in error_str or '503' in error_str or 'unavailable' in error_str:
                        _blacklist_model(model)
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            logger.warning(f"Model {model} rate limited/unavailable, trying next")
                            break
                    elif '404' in error_str or 'not_found' in error_str:
                        logger.warning(f"Model {model} not found, skipping")
                        _blacklist_model(model)
                        break
                    else:
                        logger.warning(f"Gemini {model} error: {e}")
                        break

    if not sdk_tried:
        for model in GEMINI_MODELS:
            if not _is_model_available(model):
                logger.info(f"Skipping blacklisted model {model} (REST)")
                continue
            if use_json_mode and model.startswith("gemma"):
                logger.info(f"Skipping {model} (no JSON mode support, REST)")
                continue
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

            generation_config = {"temperature": 0.7, "maxOutputTokens": 2048}
            if use_json_mode:
                generation_config["responseMimeType"] = "application/json"
                if json_schema:
                    generation_config["responseSchema"] = json_schema

            for attempt in range(max_retries):
                try:
                    response = requests.post(
                        api_url,
                        headers={
                            "Content-Type": "application/json",
                            "x-goog-api-key": GEMINI_API_KEY,
                        },
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": generation_config
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                        return text, None
                    elif response.status_code in (429, 503):
                        _blacklist_model(model)
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        logger.warning(f"Model {model} returned {response.status_code}, trying next")
                        break
                    elif response.status_code == 404:
                        _blacklist_model(model)
                        logger.warning(f"Model {model} not found (REST 404), skipping")
                        break
                    elif response.status_code >= 400:
                        logger.warning(f"Gemini REST API error {response.status_code} for model {model}")
                        break
                except requests.Timeout:
                    logger.warning(f"Gemini REST API timeout for model {model}")
                    break
                except Exception as e:
                    logger.warning(f"REST API error: {e}")
                    break

    return None, "AI service is temporarily busy. Showing trending movies instead."


def _validated_stream(raw_stream, model_name):
    first_chunk = next(raw_stream)
    if first_chunk and first_chunk.text:
        yield first_chunk
    for chunk in raw_stream:
        yield chunk


def call_gemini_streaming(prompt):
    if not GEMINI_API_KEY or not gemini_client:
        return None

    for model in GEMINI_MODELS:
        if not _is_model_available(model):
            logger.info(f"Streaming: Skipping blacklisted model {model}")
            continue
        try:
            raw_stream = gemini_client.models.generate_content_stream(
                model=model,
                contents=prompt
            )
            validated = _validated_stream(raw_stream, model)
            first = next(validated)
            def _chain(first_chunk, rest):
                yield first_chunk
                yield from rest
            logger.info(f"Streaming: Model {model} validated successfully")
            return _chain(first, validated)
        except StopIteration:
            logger.warning(f"Streaming: Model {model} returned empty stream, trying next")
            continue
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'quota' in error_str or 'rate' in error_str or 'resource_exhausted' in error_str or '503' in error_str or 'unavailable' in error_str:
                _blacklist_model(model)
                logger.warning(f"Streaming: Model {model} rate limited/unavailable, trying next")
                continue
            elif '404' in error_str or 'not_found' in error_str:
                _blacklist_model(model)
                logger.warning(f"Streaming: Model {model} not found, skipping")
                continue
            else:
                logger.warning(f"Streaming: Gemini {model} error: {e}")
                continue

    # SDK streaming failed (no client, all models errored, or empty stream). One-shot completion
    # still returns a full reply so the user is not left with a blank bubble.
    if GEMINI_API_KEY:
        logger.info("Streaming: using non-streaming Gemini fallback")
        text, err = call_gemini_api(prompt, max_retries=2, use_json_mode=False)
        if text and not err:
            from types import SimpleNamespace

            def _single_chunk_stream():
                yield SimpleNamespace(text=text)

            return _single_chunk_stream()

    return None


# ── Mood detection ─────────────────────────────────────────────────────────
MOOD_GENRE_MAP = {
    # horror / thriller
    'scary': [27], 'horror': [27], 'spooky': [27], 'creepy': [27], 'frightening': [27],
    'thriller': [53], 'thrilling': [53], 'suspense': [53], 'suspenseful': [53], 'tense': [53],
    # comedy
    'funny': [35], 'comedy': [35], 'laugh': [35], 'hilarious': [35], 'lighthearted': [35],
    'fun': [35], 'humorous': [35], 'humour': [35], 'humor': [35],
    # romance
    'romantic': [10749], 'romance': [10749], 'love story': [10749],
    'date night': [10749], 'date': [10749], 'couple': [10749], 'valentines': [10749],
    # action / adventure
    'action': [28], 'adventure': [12], 'exciting': [28, 12], 'explosive': [28],
    'superhero': [28, 878], 'epic': [28, 12], 'adrenaline': [28], 'intense': [28, 53],
    'fight': [28], 'combat': [28, 10752], 'chase': [28],
    # drama
    'drama': [18], 'emotional': [18], 'cry': [18], 'tearjerker': [18], 'moving': [18],
    'touching': [18], 'heartfelt': [18],
    # sci-fi / fantasy
    'sci-fi': [878], 'scifi': [878], 'science fiction': [878], 'fantasy': [14],
    'mind-bending': [878, 9648], 'mind bending': [878, 9648], 'futuristic': [878],
    'space': [878], 'alien': [878], 'robot': [878],
    # mystery / crime
    'mystery': [9648], 'detective': [9648, 80], 'crime': [80], 'heist': [80],
    'whodunit': [9648], 'murder': [9648, 80], 'noir': [80, 9648],
    # family / animation
    'animated': [16], 'animation': [16], 'family': [10751], 'kids': [16, 10751],
    'cartoon': [16], 'pixar': [16], 'disney': [16, 10751], 'children': [10751],
    # other moods
    'feel-good': [35, 10749], 'feel good': [35, 10749], 'uplifting': [35, 18],
    'inspirational': [18, 36], 'motivational': [18, 36],
    'historical': [36], 'history': [36], 'war': [10752], 'western': [37],
    'documentary': [99], 'true story': [99, 36], 'based on true': [99, 36],
    'musical': [10402], 'music': [10402],
}

_MOOD_INDICATORS = [
    'in the mood', 'feel like', 'feeling', 'i want', 'i need', 'want to watch',
    'something', 'recommend', 'suggest', 'show me', 'give me', 'looking for',
    'watch', 'movie night', 'tonight', 'for me', 'any good',
]

# Any of these keywords alone is enough to trigger mood-based search
_STRONG_MOOD_KEYWORDS = [
    'horror', 'comedy', 'thriller', 'romance', 'romantic', 'action', 'sci-fi', 'scifi',
    'mystery', 'animated', 'documentary', 'drama', 'fantasy', 'date night', 'date',
    'funny', 'scary', 'thrilling', 'feel-good', 'feel good', 'adventure', 'crime',
    'superhero', 'musical', 'war', 'western', 'family', 'animation',
]


def detect_mood_genres(message: str):
    """Return list of TMDB genre IDs if the message looks like a mood/vibe query."""
    msg = message.lower().strip()
    has_indicator = any(ind in msg for ind in _MOOD_INDICATORS)
    genre_ids = []
    for keyword, ids in MOOD_GENRE_MAP.items():
        if keyword in msg:
            for g in ids:
                if g not in genre_ids:
                    genre_ids.append(g)
    is_strong = any(kw in msg for kw in _STRONG_MOOD_KEYWORDS)
    # Trigger if: genre detected AND (there's a mood indicator OR a strong standalone keyword)
    # Also trigger for very short messages that are almost certainly just a genre name
    is_short_genre_query = len(msg.split()) <= 4 and bool(genre_ids)
    if genre_ids and (has_indicator or is_strong or is_short_genre_query):
        return genre_ids
    return []


def _build_movie_card(item: dict) -> dict:
    return {
        'id': item.get('id'),
        'tmdbId': item.get('id'),
        'title': item.get('title') or item.get('name'),
        'media_type': item.get('media_type', 'movie'),
        'poster_path': item.get('poster_path'),
        'overview': item.get('overview', ''),
        'vote_average': item.get('vote_average'),
        'release_date': item.get('release_date') or item.get('first_air_date'),
        'genre_ids': item.get('genre_ids', []),
    }


def fetch_trending_by_genre(genre_ids: list, limit: int = 4):
    """
    Return movies matching the given genres.
    Priority: trending/week (genre-filtered) → discover/popular (genre-filtered).
    Results are shuffled so repeated requests for the same mood vary.
    """
    pool = []
    seen_ids: set = set()
    genre_str = ','.join(str(g) for g in genre_ids[:2])

    # ── Step 1: Scan first 2 pages of trending/week, keep genre matches ────
    for t_page in [1, 2]:
        try:
            t_data = tmdb_request("/trending/movie/week", {"page": t_page})
            for item in t_data.get('results', []):
                iid = item.get('id')
                if not item.get('poster_path') or iid in seen_ids:
                    continue
                if any(g in item.get('genre_ids', []) for g in genre_ids):
                    pool.append(_build_movie_card(item))
                    seen_ids.add(iid)
        except Exception as e:
            logger.warning(f"Trending page {t_page} failed: {e}")

    logger.info(f"fetch_trending_by_genre genres={genre_ids}: {len(pool)} from trending")

    # ── Step 2: Always supplement with discover so we always get `limit` ───
    # Use two random pages from the first 3 to add variety across calls
    disc_pages = random.sample(range(1, 4), k=2)
    for d_page in disc_pages:
        if len(pool) >= limit * 2:   # have enough variety already
            break
        try:
            d_data = tmdb_request("/discover/movie", {
                "with_genres": genre_str,
                "sort_by": "popularity.desc",
                "vote_count.gte": 50,
                "page": d_page,
            })
            for item in d_data.get('results', []):
                iid = item.get('id')
                if item.get('poster_path') and iid not in seen_ids:
                    pool.append(_build_movie_card(item))
                    seen_ids.add(iid)
        except Exception as e:
            logger.warning(f"Discover page {d_page} failed: {e}")

    logger.info(f"fetch_trending_by_genre genres={genre_ids}: {len(pool)} total after discover")

    random.shuffle(pool)
    return pool[:limit]


def parse_movie_recommendations_from_json(text):
    try:
        data = json.loads(text)
        movies = []
        recommendations = []
        if isinstance(data, dict):
            recommendations = data.get('recommendations', data.get('movies', []))
        elif isinstance(data, list):
            recommendations = data
        for item in recommendations:
            if isinstance(item, str):
                title = item.strip()
            elif isinstance(item, dict):
                title = (item.get('title') or item.get('name', '')).strip()
            else:
                continue
            if title and len(title) > 2 and title not in movies:
                movies.append(title)
        if movies:
            return movies[:30]
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        logger.debug(f"JSON movie extraction parse failed, will use regex fallback: {e}")
    return None


def parse_movie_recommendations_regex(text):
    movies = []

    pattern1 = re.findall(r'\*\*([^*]+?)\s*\((\d{4}(?:-\d{4})?(?:\s*-\s*(?:Present|present))?)?\)\*\*', text)
    for match in pattern1:
        title = match[0].strip()
        if title and len(title) > 2 and title not in movies:
            movies.append(title)

    if len(movies) < 5:
        pattern2 = re.findall(r'\*\*([^*\(\)]+?)\*\*', text)
        for title in pattern2:
            title = title.strip()
            if (title and len(title) > 2 and len(title) < 60 and
                title not in movies and
                not any(word in title.lower() for word in ['note', 'important', 'tip', 'warning', 'summary', 'currently', 'trending', 'upcoming'])):
                movies.append(title)

    if len(movies) < 5:
        pattern3 = re.findall(r'\d+\.\s+([^-\n]+?)(?:\s*\(\d{4}\))?(?:\s*[-–]|$)', text)
        for title in pattern3:
            title = title.strip().strip('*').strip()
            if title and len(title) > 2 and title not in movies:
                movies.append(title)

    return movies[:30]


def parse_movie_recommendations(text):
    json_result = parse_movie_recommendations_from_json(text)
    if json_result:
        return json_result
    return parse_movie_recommendations_regex(text)


def extract_movie_titles_structured(response_text):
    extraction_prompt = (
        "Extract all movie and TV show titles from the following text. "
        "Return a JSON object with a 'recommendations' array, where each item has a 'title' field.\n\n"
        f"Text:\n{response_text[:3000]}"
    )
    try:
        extracted, error = call_gemini_api(
            extraction_prompt,
            max_retries=1,
            use_json_mode=True,
            json_schema=MOVIE_EXTRACTION_SCHEMA,
        )
        if extracted and not error:
            titles = parse_movie_recommendations_from_json(extracted)
            if titles:
                logger.info(f"Structured extraction found {len(titles)} titles")
                return titles
    except Exception as e:
        logger.warning(f"Structured movie extraction failed: {e}")
    return None


MAX_USER_MESSAGE_LENGTH = 2000
PROMPT_TOKEN_BUDGET = 6000
CHARS_PER_TOKEN = 4

INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.IGNORECASE),
    re.compile(r'ignore\s+(all\s+)?above\s+instructions', re.IGNORECASE),
    re.compile(r'disregard\s+(all\s+)?previous', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\b', re.IGNORECASE),
    re.compile(r'act\s+as\s+(?:a\s+)?(?:different|new)', re.IGNORECASE),
    re.compile(r'^system\s*:', re.IGNORECASE | re.MULTILINE),
    re.compile(r'<\|(?:im_start|im_end|system|endoftext)\|>', re.IGNORECASE),
    re.compile(r'(?:```|""")[\s\S]*?(?:system|prompt|instruction)', re.IGNORECASE),
    re.compile(r'forget\s+(everything|all|your)\s+(you|instructions|rules)', re.IGNORECASE),
    re.compile(r'override\s+(your|the|all)\s+(instructions|rules|prompt)', re.IGNORECASE),
]


def sanitize_user_message(message):
    if not isinstance(message, str):
        return ""
    message = message[:MAX_USER_MESSAGE_LENGTH]
    for pattern in INJECTION_PATTERNS:
        message = pattern.sub('[filtered]', message)
    return message.strip()


def estimate_tokens(text):
    return len(text) // CHARS_PER_TOKEN


def trim_conversation_history(conversation_history, budget_tokens):
    if not conversation_history:
        return []
    trimmed = []
    used_tokens = 0
    for msg in reversed(conversation_history):
        content = msg.get('content', '')[:300]
        msg_tokens = estimate_tokens(content) + 5
        if used_tokens + msg_tokens > budget_tokens:
            break
        trimmed.insert(0, msg)
        used_tokens += msg_tokens
    return trimmed


def build_chat_prompt(user_message, user_context, conversation_history=None, current_movies=None):
    today = date.today().strftime("%B %d, %Y")
    current_year = date.today().year

    user_message = sanitize_user_message(user_message)

    # Only inject current movies when the user explicitly asks for new/current/trending content
    _new_keywords = ['new', 'latest', 'recent', "what's out", 'now playing', 'trending', 'upcoming', 'theater', 'release', 'cinema']
    _wants_current = any(kw in user_message.lower() for kw in _new_keywords)
    current_movies_section = ""
    if current_movies and _wants_current:
        now_playing_list = "\n".join(f"  - {m}" for m in current_movies.get('now_playing', [])[:6])
        upcoming_list = "\n".join(f"  - {m}" for m in current_movies.get('upcoming', [])[:4])
        current_movies_section = f"""
CURRENTLY IN THEATERS (as of {today}) — only use these when the user asks for new/current releases:
Now Playing:
{now_playing_list}
Coming Soon:
{upcoming_list}
"""

    base_prompt = f"""You are CineBot, an expert movie and TV show recommendation assistant. Today's date is {today}.

GUIDELINES:
- Recommend based on the user's TASTE PROFILE and their specific request — do NOT default to whatever is generically popular
- Draw on your full knowledge of cinema across all eras, genres, and countries
- ALWAYS bold every title and include the year: **Title (Year)**
- Be conversational and explain specifically why each pick suits this user
- Mix well-known films with hidden gems and cult classics that match the taste
- Avoid repeating titles already mentioned in this conversation
{current_movies_section}
User's Taste Profile:
- Recently rated: {json.dumps(user_context['recent_ratings'][:5])}
- Favorites: {json.dumps(user_context['favorites'][:5])}
- Recently watched: {json.dumps(user_context['recently_watched'][:5])}
- Preferred genres: {user_context['preferred_genres']}
- Disliked genres: {user_context['disliked_genres']}
"""

    base_tokens = estimate_tokens(base_prompt)
    message_tokens = estimate_tokens(user_message)
    history_budget = PROMPT_TOKEN_BUDGET - base_tokens - message_tokens - 200

    conversation_section = ""
    if conversation_history and history_budget > 0:
        trimmed_history = trim_conversation_history(conversation_history, history_budget)
        if trimmed_history:
            history_lines = []
            for msg in trimmed_history:
                role = "User" if msg.get('type') == 'user' else "Assistant"
                content = msg.get('content', '')[:300]
                if msg.get('type') == 'user':
                    content = sanitize_user_message(content)
                history_lines.append(f"{role}: {content}")
            conversation_section = f"""
CONVERSATION HISTORY:
{chr(10).join(history_lines)}
"""

    prompt = base_prompt + conversation_section + f"""
User: {user_message}

Respond naturally. When listing movies/TV shows use this exact format:
1. **Title (Year)** - Brief personal reason tailored to this user's taste
2. **Title (Year)** - Reason

Give 4-6 recommendations. Bold every title with its year like **Title (Year)**."""

    return prompt


def get_fallback_trending_movies():
    trending_data = tmdb_request("/trending/movie/week")
    fallback_movies = []
    for item in trending_data.get('results', [])[:8]:
        fallback_movies.append({
            'id': item.get('id'),
            'tmdbId': item.get('id'),
            'title': item.get('title') or item.get('name'),
            'media_type': 'movie',
            'poster_path': item.get('poster_path'),
            'overview': item.get('overview', ''),
            'vote_average': item.get('vote_average'),
            'release_date': item.get('release_date'),
        })
    return fallback_movies


def ai_chat(request):
    user = request.user if request.user.is_authenticated else None
    
    try:
        data = request.data if isinstance(request.data, dict) else json.loads(request.data)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return error_response('Message is required', 'VALIDATION_ERROR', 400)

        # ── Mood detection: bypass cache so every mood query gets fresh results ──
        _mood_genres = detect_mood_genres(user_message)
        _is_mood_query = bool(_mood_genres)

        # ── Cache check (skipped for mood queries) ─────────────────────────
        _chat_key = _chat_cache_key(user.id if user else None, user_message)
        if not _is_mood_query:
            _cached_chat = cache.get(_chat_key)
            if _cached_chat is not None:
                logger.info(f"AI chat cache HIT for user={user.id if user else 'anon'}")
                _cached_chat["fromCache"] = True
                return _cached_chat

        if user:
            user_context = get_user_context(user)
        else:
            user_context = {
                'recent_ratings': [],
                'watchlist': [],
                'favorites': [],
                'recently_watched': [],
                'preferred_genres': [],
                'disliked_genres': []
            }

        current_movies = fetch_current_movies()

        prompt = build_chat_prompt(user_message, user_context, conversation_history, current_movies)

        response_text, error = call_gemini_api(prompt)

        if error:
            logger.warning(f"Gemini API failed, using trending fallback: {error}")
            fallback_movies = get_fallback_trending_movies()

            return {
                'response': "I'm experiencing high demand right now, but here are some trending movies you might enjoy! Feel free to ask again in a moment for personalized recommendations.",
                'movies': fallback_movies,
                'suggestions': ['Action movies', 'Comedy films', 'Drama recommendations'],
                'source': 'fallback'
            }

        # For mood queries, pull genre-filtered trending movies directly from TMDB
        movies = []
        if _is_mood_query:
            logger.info(f"Mood query detected, genre_ids={_mood_genres}. Fetching genre-trending movies.")
            movies = fetch_trending_by_genre(_mood_genres, limit=4)

        if not movies:
            # Skip structured extraction (always fails with gemma — no JSON mode); use regex directly
            movie_titles = parse_movie_recommendations(response_text)
        else:
            movie_titles = []

        def search_movie(title):
            try:
                search_data = tmdb_request("/search/multi", {"query": title, "page": 1})
                if search_data.get('results'):
                    for item in search_data['results'][:1]:
                        if item.get('media_type') in ['movie', 'tv']:
                            return {
                                'id': item.get('id'),
                                'tmdbId': item.get('id'),
                                'title': item.get('title') or item.get('name'),
                                'media_type': item.get('media_type'),
                                'poster_path': item.get('poster_path'),
                                'overview': item.get('overview', ''),
                                'vote_average': item.get('vote_average'),
                                'release_date': item.get('release_date') or item.get('first_air_date'),
                            }
            except Exception as e:
                logger.warning(f"TMDB search failed for '{title}': {e}")
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_title = {executor.submit(search_movie, title): title for title in movie_titles[:4]}
            for future in concurrent.futures.as_completed(future_to_title):
                try:
                    result = future.result()
                    if result:
                        movies.append(result)
                except Exception as e:
                    logger.warning(f"Movie search thread error: {e}")

        _chat_result = {
            'response': response_text,
            'movies': movies,
        }
        # ── Cache store (skipped for mood queries — results must stay fresh) ─
        try:
            if response_text and not _is_mood_query:
                cache.set(_chat_key, _chat_result, AI_CHAT_CACHE_TTL)
        except Exception as _ce:
            logger.warning(f"AI chat cache store failed: {_ce}")
        return _chat_result

    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        logger.error(f"AI chat error: {e}", exc_info=True)
        return error_response('An unexpected error occurred. Please try again.', 'INTERNAL_ERROR', 500)


def voice_chat(request):
    """Process voice message using Gemini's audio understanding (multimodal)."""
    user = request.user if request.user.is_authenticated else None

    try:
        data = request.data if isinstance(request.data, dict) else json.loads(request.data)
        audio_b64 = data.get('audio', '')
        mime_type = data.get('mimeType', 'audio/webm')
        conversation_history = data.get('history', [])

        if not audio_b64:
            return error_response('Audio data is required', 'VALIDATION_ERROR', 400)

        if not GEMINI_API_KEY or not gemini_client:
            return error_response('AI service not configured', 'SERVICE_UNAVAILABLE', 503)

        from google.genai import types as genai_types

        if user:
            user_context = get_user_context(user)
        else:
            user_context = {
                'recent_ratings': [], 'watchlist': [], 'favorites': [],
                'recently_watched': [], 'preferred_genres': [], 'disliked_genres': []
            }
        # fetch_current_movies() returns a list of formatted strings e.g.
        # "Inception (2010) - Rating: 8.8/10 - Genres: Action, Sci-Fi"
        raw_current = fetch_current_movies()
        current_titles = raw_current[:6] if isinstance(raw_current, list) else []
        genre_prefs = user_context.get('preferred_genres', [])
        fav_titles = [f.get('title', '') for f in user_context.get('favorites', [])[:3]
                      if isinstance(f, dict) and f.get('title')]

        ctx_lines = []
        if current_titles:
            ctx_lines.append(f"Currently trending/in theaters: {'; '.join(current_titles[:4])}")
        if genre_prefs:
            ctx_lines.append(f"User's preferred genres: {', '.join(genre_prefs[:5])}")
        if fav_titles:
            ctx_lines.append(f"User's favourites: {', '.join(fav_titles)}")

        system_text = (
            "You are CineBot, an expert movie AI assistant.\n\n"
            + ("\n".join(ctx_lines) + "\n\n" if ctx_lines else "")
            + "Instructions:\n"
            "1. Transcribe exactly what the user said in the audio.\n"
            "2. Respond helpfully as a movie recommendation assistant.\n"
            "3. Format movie titles as **Title (Year)**.\n\n"
            'Respond ONLY with valid JSON: {"transcript":"<words user spoke>","response":"<your response>"}'
        )

        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    genai_types.Content(parts=[
                        genai_types.Part(
                            inline_data=genai_types.Blob(mime_type=mime_type, data=audio_b64)
                        ),
                        genai_types.Part(text=system_text),
                    ])
                ]
            )
        except Exception as e:
            logger.error(f"Gemini voice call failed: {e}")
            return error_response('Could not process audio. Please try again.', 'AI_ERROR', 500)

        if not response or not response.text:
            return error_response('No response from AI', 'AI_ERROR', 500)

        raw = response.text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

        try:
            parsed = json.loads(raw)
            transcript = parsed.get('transcript', 'Voice message')
            ai_response = parsed.get('response', raw)
        except json.JSONDecodeError:
            tm = re.search(r'"transcript"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            rm = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
            transcript = tm.group(1) if tm else 'Voice message'
            ai_response = rm.group(1) if rm else raw

        movie_titles = extract_movie_titles_structured(ai_response)
        if not movie_titles:
            movie_titles = parse_movie_recommendations(ai_response)

        movies = []

        def _search_movie(title):
            try:
                sd = tmdb_request("/search/multi", {"query": title, "page": 1})
                for item in (sd.get('results') or [])[:5]:
                    if item.get('media_type') in ['movie', 'tv'] and item.get('poster_path'):
                        return {
                            'id': item['id'], 'tmdbId': item['id'],
                            'title': item.get('title') or item.get('name'),
                            'media_type': item['media_type'],
                            'poster_path': item['poster_path'],
                            'overview': item.get('overview', ''),
                            'vote_average': item.get('vote_average'),
                            'release_date': item.get('release_date') or item.get('first_air_date'),
                        }
            except Exception as ex:
                logger.warning(f"TMDB voice search failed for '{title}': {ex}")
            return None

        if movie_titles:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                futures = {ex.submit(_search_movie, t): t for t in movie_titles[:4]}
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        r = fut.result()
                        if r:
                            movies.append(r)
                    except Exception as ex2:
                        logger.warning(f"Voice movie search thread error: {ex2}")

        return {'transcript': transcript, 'response': ai_response, 'movies': movies}

    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        logger.error(f"Voice chat error: {e}", exc_info=True)
        return error_response('Could not process voice message. Please try again.', 'INTERNAL_ERROR', 500)


def ai_chat_stream(request):
    user = request.user if request.user.is_authenticated else None
    
    try:
        data = request.data if isinstance(request.data, dict) else json.loads(request.data)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return error_response('Message is required', 'VALIDATION_ERROR', 400)

        # ── Mood detection (outer scope so event_stream closure can read it) ──
        _mood_genres = detect_mood_genres(user_message)
        _is_mood_query = bool(_mood_genres)

        def search_movie(title):
            try:
                search_data = tmdb_request("/search/multi", {"query": title, "page": 1})
                if search_data.get('results'):
                    for item in search_data['results'][:1]:
                        if item.get('media_type') in ['movie', 'tv']:
                            return {
                                'id': item.get('id'),
                                'tmdbId': item.get('id'),
                                'title': item.get('title') or item.get('name'),
                                'media_type': item.get('media_type'),
                                'poster_path': item.get('poster_path'),
                                'overview': item.get('overview', ''),
                                'vote_average': item.get('vote_average'),
                                'release_date': item.get('release_date') or item.get('first_air_date'),
                            }
            except Exception as e:
                logger.warning(f"TMDB search failed for '{title}': {e}")
            return None

        def event_stream():
            # ── Cache check: skipped for mood queries so results stay fresh ─
            _stream_key = _chat_cache_key(user.id if user else None, user_message)
            if not _is_mood_query:
                _cached_stream = cache.get(_stream_key)
                if _cached_stream is not None:
                    logger.info(f"AI chat stream cache HIT for user={user.id if user else 'anon'}")
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Loading response...'})}\n\n"
                    cached_text = _cached_stream.get('response', '')
                    chunk_size = 45
                    for _i in range(0, len(cached_text), chunk_size):
                        yield f"data: {json.dumps({'type': 'chunk', 'content': cached_text[_i:_i + chunk_size]})}\n\n"
                    cached_movies = _cached_stream.get('movies', [])
                    if cached_movies:
                        yield f"data: {json.dumps({'type': 'movies_loading', 'count': len(cached_movies)})}\n\n"
                        for _m in cached_movies:
                            yield f"data: {json.dumps({'type': 'movie', 'movie': _m})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'fromCache': True})}\n\n"
                    return

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as prep_executor:
                if user:
                    user_ctx_future = prep_executor.submit(get_user_context, user)
                else:
                    user_ctx_future = None
                movies_future = prep_executor.submit(fetch_current_movies)

                if user_ctx_future:
                    user_context = user_ctx_future.result()
                else:
                    user_context = {
                        'recent_ratings': [],
                        'watchlist': [],
                        'favorites': [],
                        'recently_watched': [],
                        'preferred_genres': [],
                        'disliked_genres': []
                    }
                current_movies = movies_future.result()

            prompt = build_chat_prompt(user_message, user_context, conversation_history, current_movies)
            stream = call_gemini_streaming(prompt)

            if stream is None:
                fallback_movies = get_fallback_trending_movies()
                fallback_data = {
                    'type': 'fallback',
                    'response': "I'm experiencing high demand right now, but here are some trending movies you might enjoy!",
                    'movies': fallback_movies,
                    'source': 'fallback'
                }
                yield f"data: {json.dumps(fallback_data)}\n\n"
                return

            full_text = ""
            collected_movies = []   # track for caching
            try:
                for chunk in stream:
                    if chunk.text:
                        full_text += chunk.text
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.text})}\n\n"

                if not full_text:
                    fallback = get_fallback_trending_movies()
                    _empty_stream_msg = (
                        "I couldn't finish that reply just now. "
                        "Here are some trending picks you might like:"
                    )
                    yield f"data: {json.dumps({'type': 'fallback', 'response': _empty_stream_msg, 'movies': fallback, 'source': 'fallback'})}\n\n"
                    return

                # ── Movie cards: mood queries use genre-filtered trending ───
                if _is_mood_query:
                    logger.info(f"Mood stream query, genre_ids={_mood_genres}. Fetching genre-trending movies.")
                    mood_movies = fetch_trending_by_genre(_mood_genres, limit=4)
                    if mood_movies:
                        yield f"data: {json.dumps({'type': 'movies_loading', 'count': len(mood_movies)})}\n\n"
                        for _mm in mood_movies:
                            collected_movies.append(_mm)
                            yield f"data: {json.dumps({'type': 'movie', 'movie': _mm})}\n\n"
                else:
                    # Regex-parse AI response for specific titles, then search TMDB
                    movie_titles = parse_movie_recommendations(full_text)
                    if movie_titles:
                        yield f"data: {json.dumps({'type': 'movies_loading', 'count': min(len(movie_titles), 4)})}\n\n"
                        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                            future_to_title = {executor.submit(search_movie, title): title for title in movie_titles[:4]}
                            for future in concurrent.futures.as_completed(future_to_title):
                                try:
                                    result = future.result()
                                    if result:
                                        collected_movies.append(result)
                                        yield f"data: {json.dumps({'type': 'movie', 'movie': result})}\n\n"
                                except Exception as e:
                                    logger.warning(f"Movie search thread error: {e}")

                # ── Cache store (skipped for mood queries) ─────────────────
                try:
                    if full_text and not _is_mood_query:
                        cache.set(_stream_key, {'response': full_text, 'movies': collected_movies}, AI_CHAT_CACHE_TTL)
                except Exception as _ce:
                    logger.warning(f"AI chat stream cache store failed: {_ce}")

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                fallback = get_fallback_trending_movies()
                fallback_msg = "I'm experiencing high demand right now, but here are some trending movies you might enjoy!"
                fallback_payload = json.dumps({'type': 'fallback', 'response': fallback_msg, 'movies': fallback, 'source': 'fallback'})
                yield f"data: {fallback_payload}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        logger.error(f"AI chat stream error: {e}", exc_info=True)
        return error_response('An unexpected error occurred. Please try again.', 'INTERNAL_ERROR', 500)


def save_preferences(request):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    try:
        data = request.data if isinstance(request.data, dict) else json.loads(request.data)

        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)

        if 'preferredGenres' in data:
            prefs.preferred_genres = data['preferredGenres']
        if 'dislikedGenres' in data:
            prefs.disliked_genres = data['dislikedGenres']
        if 'preferredDecades' in data:
            prefs.preferred_decades = data['preferredDecades']
        if 'languagePreferences' in data:
            prefs.language_preferences = data['languagePreferences']
        if 'moodPreferences' in data:
            prefs.mood_preferences = data['moodPreferences']

        prefs.save()

        return {
            'success': True,
            'preferences': {
                'preferredGenres': prefs.preferred_genres,
                'dislikedGenres': prefs.disliked_genres,
                'preferredDecades': prefs.preferred_decades,
                'languagePreferences': prefs.language_preferences,
                'moodPreferences': prefs.mood_preferences,
            }
        }
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)


def get_preferences(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    try:
        prefs = UserPreferences.objects.get(user=request.user)
        return {
            'preferences': {
                'preferredGenres': prefs.preferred_genres,
                'dislikedGenres': prefs.disliked_genres,
                'preferredDecades': prefs.preferred_decades,
                'languagePreferences': prefs.language_preferences,
                'moodPreferences': prefs.mood_preferences,
            }
        }
    except UserPreferences.DoesNotExist:
        return {
            'preferences': {
                'preferredGenres': [],
                'dislikedGenres': [],
                'preferredDecades': [],
                'languagePreferences': [],
                'moodPreferences': {},
            }
        }


def pattern_analyze(request, user_id):
    if not request.user.is_authenticated:
        return {
            'userId': str(user_id),
            'analysis': None,
            'message': 'Login to see viewing patterns'
        }
    user = request.user
    
    try:
        history = ViewingHistory.objects.filter(user=user).order_by('-watched_at')[:50]
        reviews = UserReview.objects.filter(user=user).order_by('-created_at')[:50]
        favorites = UserFavorites.objects.filter(user=user)[:20]

        avg_rating = 0
        if reviews:
            avg_rating = sum(r.rating for r in reviews) / len(reviews)

        is_binge_watcher = history.count() > 15 or (reviews.count() > 10 and avg_rating > 7)

        preferred_genre_ids = []
        try:
            prefs = UserPreferences.objects.get(user=user)
            for genre_name in (prefs.preferred_genres or [])[:5]:
                if genre_name in TMDB_GENRE_MAP:
                    preferred_genre_ids.append(TMDB_GENRE_MAP[genre_name])
        except UserPreferences.DoesNotExist:
            preferred_genre_ids = [28, 878, 53]

        if not preferred_genre_ids:
            preferred_genre_ids = [28, 878, 53]

        predicted_next = preferred_genre_ids[0] if preferred_genre_ids else 28

        history_titles = [h.title for h in history[:20]]
        review_data = [{'title': r.title, 'rating': r.rating} for r in reviews[:20]]
        favorite_titles = [f.title for f in favorites[:10]]
        genre_names = [GENRE_ID_TO_NAME.get(gid, 'Unknown') for gid in preferred_genre_ids]

        gemini_insight = None
        if history.count() > 0 or reviews.count() > 0:
            insight_cache_key = f'pattern_ai_insight:{user.id}'
            gemini_insight = cache.get(insight_cache_key)
            if gemini_insight is None:
                insight_prompt = f"""You are a film critic and viewing habit analyst. Based on this user's data, write a concise, insightful 3-4 sentence analysis of their viewing personality and taste evolution. Be specific and reference their actual movies/ratings.

Viewing Data:
- Recently watched: {json.dumps(history_titles[:15])}
- Reviews (title + rating): {json.dumps(review_data[:15])}
- Favorites: {json.dumps(favorite_titles[:10])}
- Preferred genres: {json.dumps(genre_names)}
- Average rating: {round(avg_rating, 1)}/10
- Total movies watched: {history.count()}
- Binge tendency: {'Yes' if is_binge_watcher else 'No'}

Write an engaging, personalized insight paragraph (not a list). Focus on patterns, taste sophistication, and what makes their viewing profile unique."""

                gemini_insight, _ = call_gemini_api(insight_prompt)
                if gemini_insight:
                    cache.set(insight_cache_key, gemini_insight, PATTERN_INSIGHT_CACHE_TTL)

        base_response = {
            'userId': str(user_id),
            'analysis': {
                'bingeWatcher': is_binge_watcher,
                'preferredGenres': preferred_genre_ids,
                'avgRating': round(avg_rating, 1),
                'predictedNextGenre': predicted_next,
            },
            'patterns': {
                'totalWatched': history.count(),
                'totalReviews': reviews.count(),
                'totalFavorites': favorites.count(),
            }
        }

        if gemini_insight:
            base_response['aiInsight'] = gemini_insight

        return base_response

    except Exception as e:
        logger.error(f"Pattern analysis error: {e}", exc_info=True)
        return {
            'userId': str(user_id),
            'analysis': None,
            'message': 'Unable to analyze viewing patterns right now. Please try again later.'
        }


def pattern_predict(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Authentication required', 'AUTH_REQUIRED', 401)
    user = request.user
    
    history = ViewingHistory.objects.filter(user=user).order_by('-watched_at')[:20]
    reviews = UserReview.objects.filter(user=user).order_by('-created_at')[:20]
    
    avg_rating = 7.5
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    
    avg_rating_val = avg_rating  # already computed above
    is_binge = history.count() > 15 or (reviews.count() > 10 and avg_rating_val > 7)
    session_type = 'binge' if is_binge else ('explorer' if history.count() > 5 else 'casual')
    
    next_genre = 28
    if user:
        try:
            prefs = UserPreferences.objects.get(user=user)
            for genre_name in (prefs.preferred_genres or [])[:1]:
                if genre_name in TMDB_GENRE_MAP:
                    next_genre = TMDB_GENRE_MAP[genre_name]
                    break
        except UserPreferences.DoesNotExist:
            pass
    
    probability = min(0.95, 0.6 + (history.count() * 0.02) + (reviews.count() * 0.01))
    
    return {
        'userId': str(user_id),
        'prediction': {
            'nextGenre': next_genre,
            'nextRating': round(avg_rating, 1),
            'probability': round(probability, 2),
            'sessionType': session_type
        },
        'basedOn': 'viewing_patterns',
        'modelVersion': 'v1.0'
    }



def explain_with_gemini(request):
    from .ml.explainability_engine import explainability_engine as engine

    params = request.GET
    if request.method == 'POST':
        try:
            body = request.data if isinstance(request.data, dict) else (json.loads(request.data) if request.data else {})
            params = body
        except (json.JSONDecodeError, ValueError):
            params = request.GET

    source_title = params.get('sourceTitle', '')
    source_overview = params.get('sourceOverview', '')
    recommended_title = params.get('recommendedTitle', '')
    recommended_overview = params.get('recommendedOverview', '')

    if not all([source_title, recommended_title]):
        return error_response('Missing required parameters', 'VALIDATION_ERROR', 400)
    
    try:
        explanation = engine.generate_gemini_explanation(
            source_title, source_overview or '',
            recommended_title, recommended_overview or ''
        )

        return {
            'sourceTitle': source_title,
            'recommendedTitle': recommended_title,
            'geminiExplanation': explanation,
            'fallback': explanation is None
        }
    except Exception as e:
        logger.error(f"Gemini explanation error: {e}", exc_info=True)
        return {
            'sourceTitle': source_title,
            'recommendedTitle': recommended_title,
            'geminiExplanation': None,
            'fallback': True
        }

