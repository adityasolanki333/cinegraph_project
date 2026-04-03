import json
import os
import re
import time
import requests
import concurrent.futures
import logging
from datetime import datetime, date
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import UserPreferences, UserReview, UserWatchlist, UserFavorites, ViewingHistory
from .api import tmdb_request
from .validation import error_response

logger = logging.getLogger(__name__)

TMDB_GENRE_MAP = {
    'Action': 28, 'Adventure': 12, 'Animation': 16, 'Comedy': 35,
    'Crime': 80, 'Documentary': 99, 'Drama': 18, 'Family': 10751,
    'Fantasy': 14, 'History': 36, 'Horror': 27, 'Music': 10402,
    'Mystery': 9648, 'Romance': 10749, 'Science Fiction': 878,
    'Thriller': 53, 'War': 10752, 'Western': 37
}

GENRE_ID_TO_NAME = {v: k for k, v in TMDB_GENRE_MAP.items()}

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

gemini_client = None
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


def fetch_current_movies():
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

    trending = []
    now_playing = []
    upcoming = []

    try:
        trending_data = tmdb_request("/trending/movie/week")
        for item in trending_data.get('results', [])[:8]:
            trending.append(format_movie(item))
    except Exception as e:
        logger.warning(f"Failed to fetch trending movies: {e}")

    try:
        now_playing_data = tmdb_request("/movie/now_playing", {"page": 1})
        for item in now_playing_data.get('results', [])[:6]:
            now_playing.append(format_movie(item))
    except Exception as e:
        logger.warning(f"Failed to fetch now playing movies: {e}")

    try:
        upcoming_data = tmdb_request("/movie/upcoming", {"page": 1})
        for item in upcoming_data.get('results', [])[:5]:
            upcoming.append(format_movie(item))
    except Exception as e:
        logger.warning(f"Failed to fetch upcoming movies: {e}")

    return {
        'trending': trending,
        'now_playing': now_playing,
        'upcoming': upcoming,
    }


GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemma-3-12b-it",
]


def call_gemini_api(prompt, max_retries=2):
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    if gemini_client:
        for model in GEMINI_MODELS:
            for attempt in range(max_retries):
                try:
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    if response and response.text:
                        logger.info(f"Gemini {model} responded successfully")
                        return response.text, None
                except Exception as e:
                    error_str = str(e).lower()
                    if '429' in error_str or 'quota' in error_str or 'rate' in error_str or 'resource_exhausted' in error_str or '503' in error_str or 'unavailable' in error_str:
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            logger.warning(f"Model {model} rate limited/unavailable, trying next")
                            break
                    elif '404' in error_str or 'not_found' in error_str:
                        logger.warning(f"Model {model} not found, skipping")
                        break
                    else:
                        logger.warning(f"Gemini {model} error: {e}")
                        break

    for model in GEMINI_MODELS:
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{api_url}?key={GEMINI_API_KEY}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                    return text, None
                elif response.status_code in (429, 503):
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    logger.warning(f"Model {model} returned {response.status_code}, trying next")
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


def call_gemini_streaming(prompt):
    if not GEMINI_API_KEY or not gemini_client:
        return None

    for model in GEMINI_MODELS:
        try:
            response = gemini_client.models.generate_content_stream(
                model=model,
                contents=prompt
            )
            return response
        except Exception as e:
            error_str = str(e).lower()
            if '429' in error_str or 'quota' in error_str or 'rate' in error_str or '503' in error_str or 'unavailable' in error_str:
                logger.warning(f"Streaming: Model {model} rate limited/unavailable, trying next")
                continue
            elif '404' in error_str or 'not_found' in error_str:
                logger.warning(f"Streaming: Model {model} not found, skipping")
                continue
            else:
                logger.warning(f"Streaming: Gemini {model} error: {e}")
                continue

    return None


def parse_movie_recommendations(text):
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

    return movies[:10]


def build_chat_prompt(user_message, user_context, conversation_history=None, current_movies=None):
    today = date.today().strftime("%B %d, %Y")
    current_year = date.today().year

    current_movies_section = ""
    if current_movies:
        trending_list = "\n".join(f"  - {m}" for m in current_movies.get('trending', []))
        now_playing_list = "\n".join(f"  - {m}" for m in current_movies.get('now_playing', []))
        upcoming_list = "\n".join(f"  - {m}" for m in current_movies.get('upcoming', []))
        current_movies_section = f"""
CURRENT MOVIES IN THEATERS & TRENDING (as of {today}):
Trending This Week:
{trending_list}

Now Playing in Theaters:
{now_playing_list}

Upcoming Releases:
{upcoming_list}
"""

    conversation_section = ""
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-6:]:
            role = "User" if msg.get('type') == 'user' else "Assistant"
            content = msg.get('content', '')[:300]
            history_lines.append(f"{role}: {content}")
        conversation_section = f"""
CONVERSATION HISTORY (for context - reference previous suggestions when relevant):
{chr(10).join(history_lines)}
"""

    prompt = f"""You are MovieVanders AI, an expert movie and TV show recommendation assistant. Today's date is {today}.

IMPORTANT GUIDELINES:
- Prioritize recent releases ({current_year - 2}-{current_year}) and currently trending movies when relevant
- When users ask about "new", "latest", "what's out now", or "recent" movies, focus on movies from the current movies list below
- Blend in acclaimed classics only when specifically asked or when they perfectly fit the request
- ALWAYS include the release year in parentheses after each title
- Be conversational, enthusiastic, and specific about why each recommendation fits
- Reference the user's viewing history and preferences to personalize suggestions
- If the user references a previous recommendation in the conversation, acknowledge it and build on it
{current_movies_section}
User's Profile:
- Recently rated: {json.dumps(user_context['recent_ratings'][:5])}
- Favorites: {json.dumps(user_context['favorites'][:5])}
- Recently watched: {json.dumps(user_context['recently_watched'][:5])}
- Preferred genres: {user_context['preferred_genres']}
- Disliked genres: {user_context['disliked_genres']}
{conversation_section}
User's Current Request: {user_message}

Provide a helpful, personalized response. When recommending movies/TV shows, format as a numbered list:
1. **Movie Title (Year)** - Specific reason why they'd enjoy it based on their taste
2. **Another Title (Year)** - Reason

Aim for 5-8 recommendations mixing recent hits with hidden gems. Keep it conversational."""

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


@csrf_exempt
@require_POST
def ai_chat(request):
    user = request.user if request.user.is_authenticated else None
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return error_response('Message is required', 'VALIDATION_ERROR', 400)
        
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

            return JsonResponse({
                'response': "I'm experiencing high demand right now, but here are some trending movies you might enjoy! Feel free to ask again in a moment for personalized recommendations.",
                'movies': fallback_movies,
                'suggestions': ['Action movies', 'Comedy films', 'Drama recommendations'],
                'source': 'fallback'
            })

        movie_titles = parse_movie_recommendations(response_text)

        movies = []

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

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_title = {executor.submit(search_movie, title): title for title in movie_titles[:8]}
            for future in concurrent.futures.as_completed(future_to_title):
                try:
                    result = future.result()
                    if result:
                        movies.append(result)
                except Exception as e:
                    logger.warning(f"Movie search thread error: {e}")

        return JsonResponse({
            'response': response_text,
            'movies': movies,
        })

    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@csrf_exempt
@require_POST
def ai_chat_stream(request):
    user = request.user if request.user.is_authenticated else None
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return error_response('Message is required', 'VALIDATION_ERROR', 400)

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

        stream = call_gemini_streaming(prompt)

        if stream is None:
            fallback_movies = get_fallback_trending_movies()
            fallback_data = {
                'type': 'fallback',
                'response': "I'm experiencing high demand right now, but here are some trending movies you might enjoy!",
                'movies': fallback_movies,
                'source': 'fallback'
            }
            return JsonResponse(fallback_data)

        def event_stream():
            full_text = ""
            try:
                for chunk in stream:
                    if chunk.text:
                        full_text += chunk.text
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.text})}\n\n"

                movie_titles = parse_movie_recommendations(full_text)
                movies = []

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

                if movie_titles:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                        future_to_title = {executor.submit(search_movie, title): title for title in movie_titles[:8]}
                        for future in concurrent.futures.as_completed(future_to_title):
                            try:
                                result = future.result()
                                if result:
                                    movies.append(result)
                            except Exception as e:
                                logger.warning(f"Movie search thread error: {e}")

                if not full_text and not movies:
                    fallback = get_fallback_trending_movies()
                    yield f"data: {json.dumps({'type': 'done', 'movies': fallback})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'done', 'movies': movies})}\n\n"

            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': 'Stream interrupted. Please try again.'})}\n\n"

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
        return error_response(str(e), 'INTERNAL_ERROR', 500)


@require_POST
def save_preferences(request):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    try:
        data = json.loads(request.body)

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

        return JsonResponse({
            'success': True,
            'preferences': {
                'preferredGenres': prefs.preferred_genres,
                'dislikedGenres': prefs.disliked_genres,
                'preferredDecades': prefs.preferred_decades,
                'languagePreferences': prefs.language_preferences,
                'moodPreferences': prefs.mood_preferences,
            }
        })
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)


@require_GET
def get_preferences(request, user_id):
    if not request.user.is_authenticated:
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
    
    if str(request.user.id) != str(user_id):
        return error_response('Not authorized', 'FORBIDDEN', 403)
    
    try:
        prefs = UserPreferences.objects.get(user=request.user)
        return JsonResponse({
            'preferences': {
                'preferredGenres': prefs.preferred_genres,
                'dislikedGenres': prefs.disliked_genres,
                'preferredDecades': prefs.preferred_decades,
                'languagePreferences': prefs.language_preferences,
                'moodPreferences': prefs.mood_preferences,
            }
        })
    except UserPreferences.DoesNotExist:
        return JsonResponse({
            'preferences': {
                'preferredGenres': [],
                'dislikedGenres': [],
                'preferredDecades': [],
                'languagePreferences': [],
                'moodPreferences': {},
            }
        })


@require_GET
def pattern_analyze(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'userId': str(user_id),
            'analysis': None,
            'message': 'Login to see viewing patterns'
        })
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

        return JsonResponse(base_response)

    except Exception as e:
        logger.error(f"Pattern analysis error: {e}", exc_info=True)
        return JsonResponse({
            'userId': str(user_id),
            'analysis': None,
            'message': 'Unable to analyze viewing patterns right now. Please try again later.'
        })


@require_GET
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
    
    return JsonResponse({
        'userId': str(user_id),
        'prediction': {
            'nextGenre': next_genre,
            'nextRating': round(avg_rating, 1),
            'probability': round(probability, 2),
            'sessionType': session_type
        },
        'basedOn': 'viewing_patterns',
        'modelVersion': 'v1.0'
    })



@require_GET
def explain_with_gemini(request):
    from .ml.explainability_engine import explainability_engine as engine

    source_title = request.GET.get('sourceTitle', '')
    source_overview = request.GET.get('sourceOverview', '')
    recommended_title = request.GET.get('recommendedTitle', '')
    recommended_overview = request.GET.get('recommendedOverview', '')

    if not all([source_title, recommended_title]):
        return error_response('Missing required parameters', 'VALIDATION_ERROR', 400)
    
    try:
        explanation = engine.generate_gemini_explanation(
            source_title, source_overview or '',
            recommended_title, recommended_overview or ''
        )

        return JsonResponse({
            'sourceTitle': source_title,
            'recommendedTitle': recommended_title,
            'geminiExplanation': explanation,
            'fallback': explanation is None
        })
    except Exception as e:
        logger.error(f"Gemini explanation error: {e}", exc_info=True)
        return JsonResponse({
            'sourceTitle': source_title,
            'recommendedTitle': recommended_title,
            'geminiExplanation': None,
            'fallback': True
        })

