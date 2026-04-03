import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

logger = logging.getLogger(__name__)


def _to_response(result):
    from django.http import HttpResponseBase
    if isinstance(result, HttpResponseBase):
        return result
    if isinstance(result, dict):
        status = result.get('_status', 200)
        data = {k: v for k, v in result.items() if k != '_status'}
        return Response(data, status=status)
    return Response(result)


class HybridRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_hybrid_recommendations
        return _to_response(get_hybrid_recommendations(request, user_id))


class CollaborativeRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_collaborative_recommendations
        return _to_response(get_collaborative_recommendations(request, user_id))


class SimilarItemsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id):
        from movies.ml_api import get_similar_items
        return _to_response(get_similar_items(request, tmdb_id))


class UserSimilarityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_user_similarity
        return _to_response(get_user_similarity(request, user_id))


class RecommendationExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, tmdb_id):
        from movies.ml_api import get_recommendation_explanation
        return _to_response(get_recommendation_explanation(request, user_id, tmdb_id))


class SemanticSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from movies.ml_api import semantic_search
        return _to_response(semantic_search(request))

    def post(self, request):
        from movies.ml_api import semantic_search
        return _to_response(semantic_search(request))


class BanditStatisticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_bandit_statistics
        return _to_response(get_bandit_statistics(request, user_id))


class BanditSelectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        from movies.ml_api import select_recommendation_arm
        return _to_response(select_recommendation_arm(request, user_id))


class BanditRewardView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.ml_api import update_bandit_reward
        return _to_response(update_bandit_reward(request))


class ApplyDiversityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.ml_api import apply_diversity
        return _to_response(apply_diversity(request))


class DiversityMetricsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_diversity_metrics
        return _to_response(get_diversity_metrics(request, user_id))


class SentimentAnalyticsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id):
        from movies.ml_api import get_sentiment_analytics
        return _to_response(get_sentiment_analytics(request, tmdb_id))


class AnalyzeTextSentimentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.ml_api import analyze_text_sentiment
        return _to_response(analyze_text_sentiment(request))


class UpdateSentimentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, tmdb_id):
        from movies.ml_api import update_sentiment_for_content
        return _to_response(update_sentiment_for_content(request, tmdb_id))


class RecommendationHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_recommendation_history
        return _to_response(get_recommendation_history(request, user_id))


class LogRecommendationInteractionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.ml_api import log_recommendation_interaction
        return _to_response(log_recommendation_interaction(request))


class GlobalFeatureImportanceView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from movies.ml_api import get_global_feature_importance
        return _to_response(get_global_feature_importance(request))


class CounterfactualExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, tmdb_id):
        from movies.ml_api import get_counterfactual_explanation
        return _to_response(get_counterfactual_explanation(request, user_id, tmdb_id))


class LocalExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id, tmdb_id):
        from movies.ml_api import get_local_explanation
        return _to_response(get_local_explanation(request, user_id, tmdb_id))


class CalibrateConfidenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from movies.ml_api import calibrate_confidence
        return _to_response(calibrate_confidence(request))


class ViewingPatternsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from movies.ml_api import get_viewing_patterns
        return _to_response(get_viewing_patterns(request, user_id))


class SimilarMoviesSemanticView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id):
        from movies.ml_api import get_similar_movies_semantic
        return _to_response(get_similar_movies_semantic(request, tmdb_id))
