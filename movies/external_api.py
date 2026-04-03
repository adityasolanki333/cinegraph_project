import os
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_GET


RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')


def rapidapi_request(url, host):
    if not RAPIDAPI_KEY:
        return None, "RapidAPI key not configured"
    
    try:
        response = requests.get(
            url,
            headers={
                'X-Rapidapi-Key': RAPIDAPI_KEY,
                'X-Rapidapi-Host': host
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"RapidAPI error: {response.status_code}"
    except Exception as e:
        return None, str(e)


@require_GET
def youtube_search(request):
    query = request.GET.get('q', '')
    hl = request.GET.get('hl', 'en')
    gl = request.GET.get('gl', 'US')
    
    if not query:
        return JsonResponse({'error': 'Search query is required'}, status=400)
    
    url = f"https://youtube138.p.rapidapi.com/auto-complete/?q={query}&hl={hl}&gl={gl}"
    data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@require_GET
def youtube_videos(request):
    query = request.GET.get('q', '')
    hl = request.GET.get('hl', 'en')
    gl = request.GET.get('gl', 'US')
    
    if not query:
        return JsonResponse({'error': 'Search query is required'}, status=400)
    
    search_query = f"{query} review"
    url = f"https://youtube138.p.rapidapi.com/search/?q={search_query}&hl={hl}&gl={gl}"
    data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@require_GET
def movie_ratings(request, imdb_id):
    if not imdb_id or not imdb_id.startswith('tt'):
        return JsonResponse({'error': 'Valid IMDb ID is required (format: tt1234567)'}, status=400)
    
    url = f"https://movies-ratings2.p.rapidapi.com/ratings?id={imdb_id}"
    data, error = rapidapi_request(url, 'movies-ratings2.p.rapidapi.com')
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@require_GET
def youtube_streaming_data(request, video_id):
    if not video_id:
        return JsonResponse({'error': 'Video ID is required'}, status=400)
    
    url = f"https://youtube138.p.rapidapi.com/video/details/?id={video_id}"
    data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)
