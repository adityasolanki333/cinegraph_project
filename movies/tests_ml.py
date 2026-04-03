"""
ML Pipeline Unit Tests.

Covers: RecommendationEngine, ContextualBanditEngine, DiversityEngine,
        SignalAggregator, FeedbackService.

Run: python manage.py test movies.tests_ml
"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
import numpy as np

from movies.ml.diversity_engine import (
    DiversityEngine, DiversityConfig, DiversityCandidate, MMRDiversifier,
)
from movies.ml.contextual_bandits import (
    ContextualBanditEngine, UserContext, BanditArm, RewardFeedback,
)


def _make_user(username='mluser', email='ml@test.com'):
    return User.objects.create_user(
        username=username, password='Pass1234!', email=email,
        first_name='ML', last_name='Test',
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. RecommendationEngine
# ──────────────────────────────────────────────────────────────────────────────

class RecommendationEngineTests(TestCase):
    """Tests for collaborative filtering recommendation engine."""

    def _build_engine(self):
        from movies.ml.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()

        user1 = _make_user('user1', 'u1@test.com')
        user2 = _make_user('user2', 'u2@test.com')
        user3 = _make_user('user3', 'u3@test.com')

        from movies.models import UserReview
        UserReview.objects.create(user=user1, tmdb_id=100, rating=9, media_type='movie', title='A')
        UserReview.objects.create(user=user1, tmdb_id=101, rating=8, media_type='movie', title='B')
        UserReview.objects.create(user=user2, tmdb_id=100, rating=8, media_type='movie', title='A')
        UserReview.objects.create(user=user2, tmdb_id=102, rating=7, media_type='movie', title='C')
        UserReview.objects.create(user=user3, tmdb_id=101, rating=6, media_type='movie', title='B')
        UserReview.objects.create(user=user3, tmdb_id=102, rating=9, media_type='movie', title='C')

        return engine, user1, user2, user3

    def test_build_matrix_returns_sparse(self):
        engine, *_ = self._build_engine()
        matrix = engine.build_user_item_matrix(None)
        self.assertIsNotNone(matrix)
        self.assertEqual(matrix.shape[0], 3)
        self.assertEqual(matrix.shape[1], 3)

    def test_compute_similarity_shape(self):
        engine, *_ = self._build_engine()
        engine.build_user_item_matrix(None)
        sim = engine.compute_user_similarity()
        self.assertEqual(sim.shape, (3, 3))
        for i in range(3):
            self.assertAlmostEqual(sim[i, i], 1.0, places=3)

    def test_get_collaborative_recommendations_valid_scores(self):
        engine, user1, user2, user3 = self._build_engine()
        engine.build_user_item_matrix(None)
        engine.compute_user_similarity()
        recs = engine.get_collaborative_recommendations(user1.id, n_recommendations=5)
        self.assertIsInstance(recs, list)
        for tmdb_id, score in recs:
            self.assertIsInstance(tmdb_id, int)
            self.assertIsInstance(score, (int, float))

    def test_get_recommendations_unknown_user_returns_empty(self):
        engine, *_ = self._build_engine()
        engine.build_user_item_matrix(None)
        engine.compute_user_similarity()
        recs = engine.get_collaborative_recommendations(99999)
        self.assertEqual(recs, [])

    def test_build_matrix_no_reviews_returns_none(self):
        from movies.ml.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        result = engine.build_user_item_matrix(None)
        self.assertIsNone(result)


# ──────────────────────────────────────────────────────────────────────────────
# 2. ContextualBanditEngine
# ──────────────────────────────────────────────────────────────────────────────

class ContextualBanditTests(TestCase):
    """Tests for Thompson Sampling contextual bandit."""

    def _make_context(self, user_id='1'):
        return UserContext(
            user_id=user_id,
            time_of_day='evening',
            day_of_week='weekend',
            session_duration=10.0,
            recent_genres=['Action', 'Drama'],
            recent_interaction_count=5,
        )

    def test_select_arm_returns_valid_arm(self):
        engine = ContextualBanditEngine()
        for arm_name in engine.ARMS:
            engine.arm_states['1'][arm_name] = BanditArm(
                name=arm_name, alpha=1.0, beta=1.0, pulls=0, rewards=0, success_rate=0.0,
            )
        ctx = self._make_context()
        selection = engine.select_arm(ctx)
        self.assertIn(selection.arm_chosen, engine.ARMS)
        self.assertGreaterEqual(selection.sampled_reward, 0.0)
        self.assertLessEqual(selection.sampled_reward, 2.0)
        self.assertEqual(len(selection.all_arm_scores), len(engine.ARMS))

    def test_update_reward_changes_alpha_beta(self):
        from movies.models import BanditExperiment
        user = _make_user('bandit_pos', 'bandit_pos@test.com')
        experiment = BanditExperiment.objects.create(
            user=user, experiment_type='thompson_sampling',
            arm_chosen='collaborative', context={}, exploration_rate=0.5,
        )

        engine = ContextualBanditEngine()
        user_id = str(user.id)
        arm_name = 'collaborative'
        engine.arm_states[user_id][arm_name] = BanditArm(
            name=arm_name, alpha=1.0, beta=1.0, pulls=5, rewards=2, success_rate=0.4,
        )
        original_alpha = engine.arm_states[user_id][arm_name].alpha

        with patch.object(engine, '_persist_arm_state'):
            with patch.object(engine, '_cleanup_old_experiments'):
                feedback = RewardFeedback(
                    experiment_id=str(experiment.id), reward=0.8, outcome_type='rated_high',
                )
                engine.update_reward(feedback)

        arm = engine.arm_states[user_id][arm_name]
        self.assertGreater(arm.alpha, original_alpha)

    def test_update_reward_negative_increases_beta(self):
        from movies.models import BanditExperiment
        user = _make_user('bandit_neg', 'bandit_neg@test.com')
        experiment = BanditExperiment.objects.create(
            user=user, experiment_type='thompson_sampling',
            arm_chosen='trending', context={}, exploration_rate=0.5,
        )

        engine = ContextualBanditEngine()
        user_id = str(user.id)
        arm_name = 'trending'
        engine.arm_states[user_id][arm_name] = BanditArm(
            name=arm_name, alpha=1.0, beta=1.0, pulls=3, rewards=1, success_rate=0.33,
        )
        original_beta = engine.arm_states[user_id][arm_name].beta

        with patch.object(engine, '_persist_arm_state'):
            with patch.object(engine, '_cleanup_old_experiments'):
                feedback = RewardFeedback(
                    experiment_id=str(experiment.id), reward=0.1, outcome_type='rated_low',
                )
                engine.update_reward(feedback)

        arm = engine.arm_states[user_id][arm_name]
        self.assertGreater(arm.beta, original_beta)

    def test_calculate_reward_maps(self):
        engine = ContextualBanditEngine()
        self.assertEqual(engine.calculate_reward('clicked'), 0.3)
        self.assertEqual(engine.calculate_reward('rated_high'), 1.0)
        self.assertEqual(engine.calculate_reward('unknown_type'), 0.0)

    def test_select_arm_all_arms_scored(self):
        engine = ContextualBanditEngine()
        for arm_name in engine.ARMS:
            engine.arm_states['1'][arm_name] = BanditArm(
                name=arm_name, alpha=2.0, beta=2.0, pulls=5, rewards=2, success_rate=0.4,
            )
        ctx = self._make_context()
        selection = engine.select_arm(ctx)
        scored_arms = {s['arm'] for s in selection.all_arm_scores}
        self.assertEqual(scored_arms, set(engine.ARMS))


# ──────────────────────────────────────────────────────────────────────────────
# 3. DiversityEngine (MMR)
# ──────────────────────────────────────────────────────────────────────────────

class DiversityEngineTests(TestCase):
    """Tests for MMR diversity and genre concentration."""

    def _make_candidates(self):
        return [
            DiversityCandidate(id='1', tmdb_id=100, media_type='movie', score=0.95,
                               genres=['Action', 'Sci-Fi']),
            DiversityCandidate(id='2', tmdb_id=101, media_type='movie', score=0.90,
                               genres=['Action', 'Thriller']),
            DiversityCandidate(id='3', tmdb_id=102, media_type='movie', score=0.85,
                               genres=['Comedy', 'Romance']),
            DiversityCandidate(id='4', tmdb_id=103, media_type='movie', score=0.80,
                               genres=['Drama', 'History']),
            DiversityCandidate(id='5', tmdb_id=104, media_type='movie', score=0.75,
                               genres=['Action', 'Sci-Fi']),
            DiversityCandidate(id='6', tmdb_id=105, media_type='movie', score=0.70,
                               genres=['Horror', 'Thriller']),
            DiversityCandidate(id='7', tmdb_id=106, media_type='movie', score=0.65,
                               genres=['Documentary']),
            DiversityCandidate(id='8', tmdb_id=107, media_type='movie', score=0.60,
                               genres=['Animation', 'Family']),
        ]

    def test_mmr_reduces_genre_concentration(self):
        mmr = MMRDiversifier()
        candidates = self._make_candidates()
        selected = mmr.apply_mmr(candidates, limit=5, lambda_param=0.5)

        self.assertEqual(len(selected), 5)

        all_genres = set()
        for c in selected:
            all_genres.update(c.genres)

        top5_by_score = sorted(candidates, key=lambda c: c.score, reverse=True)[:5]
        top5_genres = set()
        for c in top5_by_score:
            top5_genres.update(c.genres)

        self.assertGreaterEqual(len(all_genres), len(top5_genres))

    def test_mmr_first_item_is_highest_score(self):
        mmr = MMRDiversifier()
        candidates = self._make_candidates()
        selected = mmr.apply_mmr(candidates, limit=3, lambda_param=0.7)
        self.assertEqual(selected[0].tmdb_id, 100)

    def test_mmr_empty_input(self):
        mmr = MMRDiversifier()
        self.assertEqual(mmr.apply_mmr([], limit=5), [])

    def test_mmr_fewer_candidates_than_limit(self):
        mmr = MMRDiversifier()
        candidates = self._make_candidates()[:2]
        selected = mmr.apply_mmr(candidates, limit=10)
        self.assertEqual(len(selected), 2)

    def test_diversity_engine_apply_diversity(self):
        engine = DiversityEngine()
        candidates = self._make_candidates()
        config = DiversityConfig(lambda_param=0.5, epsilon_exploration=0.0, serendipity_rate=0.0)
        result = engine.apply_diversity(candidates, config)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_diversity_metrics_calculation(self):
        engine = DiversityEngine()
        candidates = self._make_candidates()
        metrics = engine.calculate_metrics(candidates, ['Action', 'Sci-Fi'])
        self.assertGreaterEqual(metrics.intra_diversity, 0.0)
        self.assertLessEqual(metrics.intra_diversity, 1.0)
        self.assertGreaterEqual(metrics.genre_balance, 0.0)


# ──────────────────────────────────────────────────────────────────────────────
# 4. SignalAggregator
# ──────────────────────────────────────────────────────────────────────────────

class SignalAggregatorTests(TestCase):
    """Tests for implicit+explicit signal aggregation."""

    def test_weighted_scores_in_range(self):
        from movies.ml.signal_aggregator import SignalAggregator
        user = _make_user('siguser', 'sig@test.com')

        from movies.models import UserReview
        UserReview.objects.create(user=user, tmdb_id=200, rating=10, media_type='movie', title='Top')
        UserReview.objects.create(user=user, tmdb_id=201, rating=5, media_type='movie', title='Mid')
        UserReview.objects.create(user=user, tmdb_id=202, rating=1, media_type='movie', title='Low')

        aggregator = SignalAggregator()
        signals = aggregator.get_user_signals(user)
        self.assertIsInstance(signals, dict)
        self.assertGreater(len(signals), 0)
        for tmdb_id, score in signals.items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_empty_user_returns_empty(self):
        from movies.ml.signal_aggregator import SignalAggregator
        user = _make_user('emptyuser', 'empty@test.com')
        aggregator = SignalAggregator()
        signals = aggregator.get_user_signals(user)
        self.assertEqual(signals, {})

    def test_get_seed_ids_respects_min_score(self):
        from movies.ml.signal_aggregator import SignalAggregator
        user = _make_user('seeduser', 'seed@test.com')

        from movies.models import UserReview
        UserReview.objects.create(user=user, tmdb_id=300, rating=10, media_type='movie', title='Great')
        UserReview.objects.create(user=user, tmdb_id=301, rating=1, media_type='movie', title='Bad')

        aggregator = SignalAggregator()
        seeds = aggregator.get_seed_ids(user, min_score=0.3)
        self.assertIsInstance(seeds, list)
        for seed_id in seeds:
            self.assertIsInstance(seed_id, int)


# ──────────────────────────────────────────────────────────────────────────────
# 5. FeedbackService
# ──────────────────────────────────────────────────────────────────────────────

class FeedbackServiceTests(TestCase):
    """Tests for feedback loop weight updates."""

    def test_get_default_weights(self):
        from movies.ml.feedback_service import FeedbackService, DEFAULT_WEIGHTS
        user = _make_user('fbuser', 'fb@test.com')
        service = FeedbackService()
        weights = service.get_user_weights(user)
        self.assertIsInstance(weights, dict)
        for key in DEFAULT_WEIGHTS:
            self.assertIn(key, weights)
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=4)

    def _make_recommendation(self, user):
        from movies.models import Recommendation
        return Recommendation.objects.create(
            user=user, tmdb_id=999, media_type='movie', title='Test Movie',
            recommendation_type='collaborative', confidence=0.8,
            relevance_score=0.8, reason='Test recommendation',
        )

    def test_record_outcome_positive_increases_weight(self):
        from movies.ml.feedback_service import FeedbackService, DEFAULT_WEIGHTS
        from movies.models import FeatureWeight
        user = _make_user('fb_pos', 'fbpos@test.com')
        service = FeedbackService()

        rec = self._make_recommendation(user)
        scoring_factors = {'collaborative': 0.8}

        service.record_outcome(user, rec, 'rated_high', scoring_factors)

        fw = FeatureWeight.objects.get(user=user, feature_name='collaborative')
        self.assertGreater(fw.weight, DEFAULT_WEIGHTS['collaborative'])
        self.assertEqual(fw.success_count, 1)
        self.assertEqual(fw.total_count, 1)

    def test_record_outcome_negative_decreases_weight(self):
        from movies.ml.feedback_service import FeedbackService, DEFAULT_WEIGHTS
        from movies.models import FeatureWeight
        user = _make_user('fb_neg', 'fbneg@test.com')
        service = FeedbackService()

        rec = self._make_recommendation(user)
        scoring_factors = {'collaborative': 0.5}

        service.record_outcome(user, rec, 'dismissed', scoring_factors)

        fw = FeatureWeight.objects.get(user=user, feature_name='collaborative')
        self.assertLess(fw.weight, DEFAULT_WEIGHTS['collaborative'])
        self.assertEqual(fw.success_count, 0)
        self.assertEqual(fw.total_count, 1)

    def test_weight_stays_in_bounds(self):
        from movies.ml.feedback_service import FeedbackService
        from movies.models import FeatureWeight
        user = _make_user('fb_bounds', 'fbbounds@test.com')
        service = FeedbackService()

        rec = self._make_recommendation(user)

        for _ in range(50):
            service.record_outcome(user, rec, 'rated_high', {'collaborative': 0.9})

        fw = FeatureWeight.objects.get(user=user, feature_name='collaborative')
        self.assertLessEqual(fw.weight, 1.0)
        self.assertGreaterEqual(fw.weight, 0.05)
