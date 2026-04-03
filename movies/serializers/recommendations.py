from rest_framework import serializers
from movies.models import (
    Recommendation, RecommendationMetrics, UserRecommendation,
    RecommendationVote, RecommendationComment, SentimentAnalytics,
)


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'


class UserRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRecommendation
        fields = '__all__'


class RecommendationVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationVote
        fields = '__all__'


class RecommendationCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationComment
        fields = '__all__'


class SentimentAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalytics
        fields = '__all__'
