from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from movies.external_api import rapidapi_request


class YouTubeSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Search query is required', 'code': 'VALIDATION_ERROR'}, status=400)
        hl = request.query_params.get('hl', 'en')
        gl = request.query_params.get('gl', 'US')
        url = f"https://youtube138.p.rapidapi.com/auto-complete/?q={query}&hl={hl}&gl={gl}"
        data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
        if error:
            return Response({'error': error}, status=500)
        return Response(data)


class YouTubeVideosView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return Response({'error': 'Search query is required', 'code': 'VALIDATION_ERROR'}, status=400)
        hl = request.query_params.get('hl', 'en')
        gl = request.query_params.get('gl', 'US')
        url = f"https://youtube138.p.rapidapi.com/search/?q={query} review&hl={hl}&gl={gl}"
        data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
        if error:
            return Response({'error': error}, status=500)
        return Response(data)


class MovieRatingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, imdb_id):
        if not imdb_id or not imdb_id.startswith('tt'):
            return Response(
                {'error': 'Valid IMDb ID is required (format: tt1234567)', 'code': 'VALIDATION_ERROR'},
                status=400
            )
        url = f"https://movies-ratings2.p.rapidapi.com/ratings?id={imdb_id}"
        data, error = rapidapi_request(url, 'movies-ratings2.p.rapidapi.com')
        if error:
            return Response({'error': error}, status=500)
        return Response(data)


class YouTubeStreamingDataView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, video_id):
        if not video_id:
            return Response({'error': 'Video ID is required', 'code': 'VALIDATION_ERROR'}, status=400)
        url = f"https://youtube138.p.rapidapi.com/video/details/?id={video_id}"
        data, error = rapidapi_request(url, 'youtube138.p.rapidapi.com')
        if error:
            return Response({'error': error}, status=500)
        return Response(data)
