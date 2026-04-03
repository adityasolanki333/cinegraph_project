import logging
from django.http import HttpResponseBase
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


def _to_response(result):
    if isinstance(result, HttpResponseBase):
        return result
    if isinstance(result, dict):
        status = result.get('_status', 200)
        data = {k: v for k, v in result.items() if k != '_status'}
        return Response(data, status=status)
    return Response(result)


class AiChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.recommendations_api import ai_chat
        return _to_response(ai_chat(request))


class AiChatStreamView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.recommendations_api import ai_chat_stream
        return _to_response(ai_chat_stream(request))


class SavePreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.recommendations_api import save_preferences
        return _to_response(save_preferences(request))


class GetPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.recommendations_api import get_preferences
        return _to_response(get_preferences(request, user_id))


class PatternAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.recommendations_api import pattern_analyze
        return _to_response(pattern_analyze(request, user_id))


class PatternPredictView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.recommendations_api import pattern_predict
        return _to_response(pattern_predict(request, user_id))


class ExplainWithGeminiView(APIView):
    permission_classes = [IsAuthenticated]

    def _handle(self, request):
        from movies.recommendations_api import explain_with_gemini
        return _to_response(explain_with_gemini(request))

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)
