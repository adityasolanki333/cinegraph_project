"""
Feedback Loop Service

Records interaction outcomes and updates per-user FeatureWeight records,
allowing the hybrid scoring formula to adapt over time instead of using
fixed collab_weight / content_weight.
"""
from __future__ import annotations

from typing import Dict, Optional

from django.contrib.auth.models import User
from django.db.models import F


DEFAULT_WEIGHTS = {
    'collaborative': 0.6,
    'content': 0.4,
    'popularity': 0.2,
    'recency': 0.15,
    'embedding_similarity': 0.1,
}

OUTCOME_REWARDS = {
    'clicked': 0.3,
    'watchlisted': 0.6,
    'rated_high': 1.0,
    'rated_medium': 0.4,
    'rated_low': 0.1,
    'ignored': 0.0,
    'dismissed': -0.2,
}

LEARNING_RATE = 0.05


class FeedbackService:

    def record_outcome(self, user, recommendation, interaction_type: str,
                       scoring_factors: Optional[Dict[str, float]] = None):
        from movies.models import FeatureContribution, FeatureWeight

        reward = OUTCOME_REWARDS.get(interaction_type, 0.0)
        is_success = reward >= 0.5

        if scoring_factors:
            for feature_name, contribution in scoring_factors.items():
                FeatureContribution.objects.create(
                    recommendation=recommendation,
                    user=user,
                    feature_name=feature_name,
                    contribution_score=contribution,
                    feature_value=contribution,
                    was_successful=is_success,
                    outcome_type=interaction_type,
                )

                fw, created = FeatureWeight.objects.get_or_create(
                    user=user,
                    feature_name=feature_name,
                    defaults={
                        'weight': DEFAULT_WEIGHTS.get(feature_name, 0.5),
                        'learning_rate': LEARNING_RATE,
                    }
                )
                fw.total_count = F('total_count') + 1
                if is_success:
                    fw.success_count = F('success_count') + 1
                fw.save(update_fields=['total_count', 'success_count', 'last_updated'])
                fw.refresh_from_db()

                if fw.total_count > 0:
                    fw.success_rate = fw.success_count / fw.total_count
                direction = 1.0 if is_success else -1.0
                fw.weight = max(0.05, min(1.0,
                    fw.weight + fw.learning_rate * direction * abs(reward)
                ))
                fw.save(update_fields=['weight', 'success_rate', 'last_updated'])

    def get_user_weights(self, user) -> Dict[str, float]:
        from movies.models import FeatureWeight

        valid_keys = set(DEFAULT_WEIGHTS.keys())
        weights = dict(DEFAULT_WEIGHTS)
        try:
            user_weights = FeatureWeight.objects.filter(
                user=user, total_count__gte=3,
                feature_name__in=valid_keys,
            ).values('feature_name', 'weight')
            for fw in user_weights:
                weights[fw['feature_name']] = fw['weight']
        except Exception:
            pass

        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights


feedback_service = FeedbackService()
