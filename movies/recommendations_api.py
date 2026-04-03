import json
import os
import re
import time
import requests
import concurrent.futures
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from .models import UserPreferences, UserReview, UserWatchlist, UserFavorites, ViewingHistory
from .api import tmdb_request

logger = logging.getLogger(__name__)

# Shared TMDB genre ID mapping used across pattern analysis functions
TMDB_GENRE_MAP = {
    'Action': 28, 'Adventure': 12, 'Animation': 16, 'Comedy': 35,
    'Crime': 80, 'Documentary': 99, 'Drama': 18, 'Family': 10751,
    'Fantasy': 14, 'History': 36, 'Horror': 27, 'Music': 10402,
    'Mystery': 9648, 'Romance': 10749, 'Science Fiction': 878,
    'Thriller': 53, 'War': 10752, 'Western': 37
}


GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# Initialize Gemini client using new google-genai SDK
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


GEMINI_MODELS = [
    "gemma-3-12b-it", # Prioritize User request
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

def call_gemini_api(prompt, max_retries=2):
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"
    
    # Try using the new SDK first
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
                    if '429' in error_str or 'quota' in error_str or 'rate' in error_str:
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        else:
                            logger.warning(f"Model {model} rate limited, trying next")
                            break
                    else:
                        logger.warning(f"Gemini {model} error: {e}")
                        break
    
    # Fallback to REST API
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
                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break
                elif response.status_code >= 400:
                    break
            except Exception as e:
                logger.warning(f"REST API error: {e}")
                break
    
    return None, "Gemini API quota exceeded - please try again later"


def parse_movie_recommendations(text):
    movies = []
    
    # Pattern 1: **Title (Year)** format (markdown bold with year)
    pattern1 = re.findall(r'\*\*([^*]+?)\s*\((\d{4}(?:-\d{4})?(?:\s*-\s*(?:Present|present))?)?\)\*\*', text)
    for match in pattern1:
        title = match[0].strip()
        if title and len(title) > 2 and title not in movies:
            movies.append(title)
    
    # Pattern 2: **Title** format (markdown bold without year)
    if len(movies) < 5:
        pattern2 = re.findall(r'\*\*([^*\(\)]+?)\*\*', text)
        for title in pattern2:
            title = title.strip()
            # Filter out non-movie titles
            if (title and len(title) > 2 and len(title) < 60 and 
                title not in movies and 
                not any(word in title.lower() for word in ['note', 'important', 'tip', 'warning', 'summary'])):
                movies.append(title)
    
    # Pattern 3: Numbered list format - 1. Title (Year)
    if len(movies) < 5:
        pattern3 = re.findall(r'\d+\.\s+([^-\n]+?)(?:\s*\(\d{4}\))?(?:\s*[-–]|$)', text)
        for title in pattern3:
            title = title.strip().strip('*').strip()
            if title and len(title) > 2 and title not in movies:
                movies.append(title)
    
    return movies[:10]
@csrf_exempt
@require_POST
def ai_chat(request):
    from django.contrib.auth.models import User
    
    user = request.user if request.user.is_authenticated else None
    if not user:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            user = None
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
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
        
        prompt = f"""You are a helpful movie and TV show recommendation assistant. Based on the user's preferences and request, suggest relevant movies or TV shows.

User's Profile:
- Recently rated: {json.dumps(user_context['recent_ratings'][:5])}
- Favorites: {json.dumps(user_context['favorites'][:5])}
- Recently watched: {json.dumps(user_context['recently_watched'][:5])}
- Preferred genres: {user_context['preferred_genres']}
- Disliked genres: {user_context['disliked_genres']}

User's Request: {user_message}

Please provide a helpful response. If recommending movies/TV shows, format them as a numbered list like:
1. Movie Title (Year) - Brief reason why they might like it
2. Another Title (Year) - Reason

Keep recommendations relevant to the user's taste based on their profile. Be conversational and helpful."""

        response_text, error = call_gemini_api(prompt)
        
        if error:
            popular_data = tmdb_request("/movie/popular", {"page": 1})
            fallback_movies = []
            for item in popular_data.get('results', [])[:8]:
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
            
            return JsonResponse({
                'response': "Here are some popular movies you might enjoy while I'm taking a quick break! These are currently trending and highly rated.",
                'movies': fallback_movies,
                'suggestions': ['Action movies', 'Comedy films', 'Drama recommendations'],
                'source': 'fallback'
            })
        
        movie_titles = parse_movie_recommendations(response_text)
        
        movies = []
        
        # Parallelize TMDB searches
        def search_movie(title):
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
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_title = {executor.submit(search_movie, title): title for title in movie_titles[:6]}
            for future in concurrent.futures.as_completed(future_to_title):
                result = future.result()
                if result:
                    movies.append(result)
        
        return JsonResponse({
            'response': response_text,
            'movies': movies,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@require_POST
def save_preferences(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
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
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_GET
def get_preferences(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    if str(request.user.id) != str(user_id):
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
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
    from django.contrib.auth.models import User
    
    user = request.user if request.user.is_authenticated else None
    if not user:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            return JsonResponse({
                'userId': str(user_id),
                'analysis': None,
                'message': 'Login to see viewing patterns'
            })
    
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
    
    return JsonResponse({
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
    })


@require_GET
def pattern_predict(request, user_id):
    from django.contrib.auth.models import User
    
    user = request.user if request.user.is_authenticated else None
    if not user:
        try:
            user = User.objects.get(username='demo_user')
        except User.DoesNotExist:
            user = None
    
    history = ViewingHistory.objects.filter(user=user).order_by('-watched_at')[:20] if user else ViewingHistory.objects.all()[:20]
    reviews = UserReview.objects.filter(user=user).order_by('-created_at')[:20] if user else UserReview.objects.all()[:20]
    
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
    """Generate compelling explanation for why two movies match (using Gemini AI)"""
    from .ml.explainability_engine import explainability_engine as engine
    
    source_title = request.GET.get('sourceTitle', '')
    source_overview = request.GET.get('sourceOverview', '')
    recommended_title = request.GET.get('recommendedTitle', '')
    recommended_overview = request.GET.get('recommendedOverview', '')
    
    if not all([source_title, recommended_title]):
        return JsonResponse({'error': 'Missing required parameters'}, status=400)
    
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


