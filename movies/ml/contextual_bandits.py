"""
Contextual Bandit Engine using Thompson Sampling
Balances exploration (trying new recommendations) vs exploitation (using known preferences)

Algorithm: Thompson Sampling with Beta posterior
- Maintains Beta(α, β) distribution for each arm (recommendation strategy)
- α = successes + 1, β = failures + 1
- Samples from each distribution and selects arm with highest sample

Arm states are persisted to the database via FeatureWeight model.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class UserContext:
    user_id: str
    time_of_day: str
    day_of_week: str
    session_duration: float
    recent_genres: List[str]
    recent_interaction_count: int
    device_type: Optional[str] = None
    mood: Optional[str] = None


@dataclass
class BanditArm:
    name: str
    alpha: float
    beta: float
    pulls: int
    rewards: int
    success_rate: float


@dataclass
class BanditSelection:
    arm_chosen: str
    sampled_reward: float
    all_arm_scores: List[Dict[str, float]]
    exploration_rate: float


@dataclass
class RewardFeedback:
    experiment_id: str
    reward: float
    outcome_type: str


class ContextualBanditEngine:
    """Thompson Sampling-based contextual bandit for recommendation strategy selection.
    Arm states are persisted to the database via FeatureWeight."""
    
    PRIOR_ALPHA = 1.0
    PRIOR_BETA = 1.0
    
    ARMS = [
        'collaborative',
        'content_based',
        'trending',
        'hybrid_ensemble',
        'exploration_random'
    ]
    
    REWARD_MAP = {
        'clicked': 0.3,
        'watchlisted': 0.6,
        'rated_high': 1.0,
        'rated_medium': 0.4,
        'rated_low': 0.1,
        'ignored': 0.0,
        'dismissed': -0.2,
        'preference_positive': 0.8,
        'preference_negative': -0.1,
    }
    
    CONTEXT_BOOSTS = {
        ('collaborative', 'day_of_week', 'weekend'): {
            'value': 0.2,
            'reason': 'Users engage more with collaborative recs on weekends',
        },
        ('trending', 'time_of_day', 'evening'): {
            'value': 0.25,
            'reason': 'Trending content performs better during evening sessions',
        },
        ('content_based', 'low_interactions', True): {
            'value': 0.4,
            'reason': 'Content-based works better for users with few interactions (cold start)',
        },
        ('exploration_random', 'short_session', True): {
            'value': 0.3,
            'reason': 'Short sessions benefit from exploration to capture interest quickly',
        },
        ('hybrid_ensemble', 'long_session', True): {
            'value': 0.25,
            'reason': 'Long sessions benefit from ensemble blending for sustained engagement',
        },
    }

    def __init__(self):
        self.arm_states: Dict[str, Dict[str, BanditArm]] = defaultdict(dict)

    def _db_key(self, arm_name: str) -> str:
        return f"bandit_arm_{arm_name}"

    def _load_arm_states(self, user_id: str) -> None:
        if user_id in self.arm_states and len(self.arm_states[user_id]) == len(self.ARMS):
            return

        try:
            from django.contrib.auth.models import User
            from movies.models import FeatureWeight

            user = User.objects.filter(id=int(user_id)).first() if str(user_id).isdigit() else None

            for arm_name in self.ARMS:
                db_key = self._db_key(arm_name)
                try:
                    fw = FeatureWeight.objects.get(user=user, feature_name=db_key)
                    alpha = self.PRIOR_ALPHA + fw.success_count
                    beta_val = self.PRIOR_BETA + (fw.total_count - fw.success_count)
                    self.arm_states[user_id][arm_name] = BanditArm(
                        name=arm_name,
                        alpha=alpha,
                        beta=beta_val,
                        pulls=fw.total_count,
                        rewards=fw.success_count,
                        success_rate=fw.success_rate,
                    )
                except FeatureWeight.DoesNotExist:
                    self.arm_states[user_id][arm_name] = BanditArm(
                        name=arm_name,
                        alpha=self.PRIOR_ALPHA,
                        beta=self.PRIOR_BETA,
                        pulls=0,
                        rewards=0,
                        success_rate=0.0,
                    )
                except Exception as e:
                    logger.warning(f"Failed to load arm state for user={user_id} arm={arm_name}: {e}")
                    self.arm_states[user_id][arm_name] = BanditArm(
                        name=arm_name,
                        alpha=self.PRIOR_ALPHA,
                        beta=self.PRIOR_BETA,
                        pulls=0,
                        rewards=0,
                        success_rate=0.0,
                    )
        except Exception as e:
            logger.warning(f"Failed to load arm states from DB for user={user_id}: {e}")
            for arm_name in self.ARMS:
                if arm_name not in self.arm_states[user_id]:
                    self.arm_states[user_id][arm_name] = BanditArm(
                        name=arm_name,
                        alpha=self.PRIOR_ALPHA,
                        beta=self.PRIOR_BETA,
                        pulls=0,
                        rewards=0,
                        success_rate=0.0,
                    )

    def _persist_arm_state(self, user_id: str, arm_name: str) -> None:
        try:
            from django.contrib.auth.models import User
            from movies.models import FeatureWeight

            user = User.objects.filter(id=int(user_id)).first() if str(user_id).isdigit() else None
            arm = self.arm_states[user_id][arm_name]
            db_key = self._db_key(arm_name)

            total = arm.alpha + arm.beta
            weight = arm.alpha / total if total > 0 else 0.5

            FeatureWeight.objects.update_or_create(
                user=user,
                feature_name=db_key,
                defaults={
                    'weight': weight,
                    'success_count': arm.rewards,
                    'total_count': arm.pulls,
                    'success_rate': arm.success_rate,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to persist arm state for user={user_id} arm={arm_name}: {e}")
    
    def extract_context(self, user_id: str, session_duration: float = 0, 
                        device_type: Optional[str] = None, mood: Optional[str] = None) -> UserContext:
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        if 5 <= hour < 12:
            time_of_day = 'morning'
        elif 12 <= hour < 17:
            time_of_day = 'afternoon'
        elif 17 <= hour < 22:
            time_of_day = 'evening'
        else:
            time_of_day = 'night'
        
        is_weekend = 'weekend' if day_of_week >= 5 else 'weekday'
        
        recent_count = 0
        recent_genres = []
        try:
            from movies.models import BanditExperiment
            if str(user_id).isdigit():
                experiments = BanditExperiment.objects.filter(
                    user_id=int(user_id)
                ).order_by('-created_at')
                recent_count = experiments.count()
                for exp in experiments[:10]:
                    ctx = exp.context or {}
                    genres = ctx.get('genres', [])
                    recent_genres.extend(genres)
                recent_genres = list(set(recent_genres))[:5]
        except Exception as e:
            logger.warning(f"Failed to load recent genres for user={user_id}: {e}")
        
        return UserContext(
            user_id=user_id,
            time_of_day=time_of_day,
            day_of_week=is_weekend,
            session_duration=session_duration,
            recent_genres=recent_genres,
            recent_interaction_count=recent_count,
            device_type=device_type,
            mood=mood
        )
    
    def get_arm_states(self, user_id: str) -> List[BanditArm]:
        self._load_arm_states(user_id)
        return [self.arm_states[user_id][arm] for arm in self.ARMS]
    
    def _sample_beta(self, alpha: float, beta: float) -> float:
        return np.random.beta(alpha, beta)
    
    def select_arm(self, context: UserContext) -> BanditSelection:
        arm_states = self.get_arm_states(context.user_id)
        arm_scores = []
        max_score = -1.0
        chosen_arm = self.ARMS[0]
        
        for arm_state in arm_states:
            sampled_reward = self._sample_beta(arm_state.alpha, arm_state.beta)
            arm_scores.append({'arm': arm_state.name, 'score': sampled_reward})
            
            if sampled_reward > max_score:
                max_score = sampled_reward
                chosen_arm = arm_state.name
        
        chosen_arm_state = next((a for a in arm_states if a.name == chosen_arm), None)
        exploration_rate = 1.0 / (1.0 + chosen_arm_state.pulls) if chosen_arm_state else 1.0
        
        return BanditSelection(
            arm_chosen=chosen_arm,
            sampled_reward=max_score,
            all_arm_scores=arm_scores,
            exploration_rate=exploration_rate
        )
    
    def select_contextual_arm(self, context: UserContext) -> BanditSelection:
        arm_states = self.get_arm_states(context.user_id)
        arm_scores = []
        max_score = -1.0
        chosen_arm = self.ARMS[0]
        
        for arm_state in arm_states:
            sampled_reward = self._sample_beta(arm_state.alpha, arm_state.beta)
            
            context_boost = self._get_context_boost(arm_state.name, context)
            sampled_reward = sampled_reward * (1 + context_boost * 0.2)
            
            arm_scores.append({'arm': arm_state.name, 'score': sampled_reward})
            
            if sampled_reward > max_score:
                max_score = sampled_reward
                chosen_arm = arm_state.name
        
        chosen_arm_state = next((a for a in arm_states if a.name == chosen_arm), None)
        exploration_rate = 1.0 / (1.0 + chosen_arm_state.pulls) if chosen_arm_state else 1.0
        
        return BanditSelection(
            arm_chosen=chosen_arm,
            sampled_reward=max_score,
            all_arm_scores=arm_scores,
            exploration_rate=exploration_rate
        )
    
    def _get_context_boost(self, arm_name: str, context: UserContext) -> float:
        boost = 0.0

        conditions = {
            ('collaborative', 'day_of_week', 'weekend'): context.day_of_week == 'weekend',
            ('trending', 'time_of_day', 'evening'): context.time_of_day == 'evening',
            ('content_based', 'low_interactions', True): context.recent_interaction_count < 5,
            ('exploration_random', 'short_session', True): context.session_duration < 5,
            ('hybrid_ensemble', 'long_session', True): context.session_duration > 15,
        }

        for key, is_active in conditions.items():
            if key[0] == arm_name and is_active and key in self.CONTEXT_BOOSTS:
                boost += self.CONTEXT_BOOSTS[key]['value']

        return min(boost, 1.0)
    
    def log_experiment(self, user_id: str, arm_chosen: str, context: UserContext,
                       exploration_rate: float) -> str:
        try:
            from django.contrib.auth.models import User
            from movies.models import BanditExperiment

            user = User.objects.filter(id=int(user_id)).first() if str(user_id).isdigit() else None
            if user is None:
                import uuid
                return str(uuid.uuid4())

            experiment = BanditExperiment.objects.create(
                user=user,
                experiment_type='thompson_sampling',
                arm_chosen=arm_chosen,
                context={
                    'time_of_day': context.time_of_day,
                    'day_of_week': context.day_of_week,
                    'session_duration': context.session_duration,
                    'genres': context.recent_genres,
                    'interaction_count': context.recent_interaction_count,
                },
                exploration_rate=exploration_rate,
            )
            experiment_id = str(experiment.id)
        except Exception as exc:
            import uuid
            import logging
            logging.getLogger(__name__).warning("log_experiment DB persist failed: %s", exc)
            experiment_id = str(uuid.uuid4())

        if user_id in self.arm_states and arm_chosen in self.arm_states[user_id]:
            self.arm_states[user_id][arm_chosen].pulls += 1
            self._persist_arm_state(user_id, arm_chosen)

        return experiment_id
    
    def update_reward(self, feedback: RewardFeedback) -> None:
        try:
            from movies.models import BanditExperiment

            exp_id = feedback.experiment_id
            if not str(exp_id).isdigit():
                return
            experiment = BanditExperiment.objects.filter(id=int(exp_id)).first()
            if experiment is None:
                return

            experiment.reward = feedback.reward
            experiment.save(update_fields=['reward'])

            user_id = str(experiment.user_id)
            arm_chosen = experiment.arm_chosen
        except Exception as exc:
            import logging
            logging.getLogger(__name__).debug("update_reward DB lookup failed: %s", exc)
            return

        self._load_arm_states(user_id)

        if user_id in self.arm_states and arm_chosen in self.arm_states[user_id]:
            arm = self.arm_states[user_id][arm_chosen]
            if feedback.reward >= 0.5:
                arm.alpha += 1
                arm.rewards += 1
            else:
                arm.beta += 1

            total = arm.alpha + arm.beta - 2
            arm.success_rate = arm.rewards / total if total > 0 else 0.0
            self._persist_arm_state(user_id, arm_chosen)

        self._cleanup_old_experiments()
    
    def _cleanup_old_experiments(self) -> None:
        try:
            from movies.models import BanditExperiment
            cutoff = datetime.now() - timedelta(days=30)
            BanditExperiment.objects.filter(
                created_at__lt=cutoff,
                reward__isnull=False,
            ).delete()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("_cleanup_old_experiments failed: %s", exc)

    def calculate_reward(self, outcome_type: str) -> float:
        return self.REWARD_MAP.get(outcome_type, 0.0)
    
    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        arm_states = self.get_arm_states(user_id)
        total_experiments = sum(arm.pulls for arm in arm_states)
        total_rewards = sum(arm.rewards for arm in arm_states)
        average_reward = total_rewards / total_experiments if total_experiments > 0 else 0
        
        best_arm = max(arm_states, key=lambda a: a.success_rate) if arm_states else None
        exploration_rate = 1.0 / np.sqrt(total_experiments) if total_experiments > 0 else 1.0
        
        return {
            'arm_performance': [
                {
                    'name': arm.name,
                    'alpha': arm.alpha,
                    'beta': arm.beta,
                    'pulls': arm.pulls,
                    'rewards': arm.rewards,
                    'success_rate': arm.success_rate
                }
                for arm in arm_states
            ],
            'total_experiments': total_experiments,
            'average_reward': average_reward,
            'best_arm': best_arm.name if best_arm else None,
            'exploration_rate': exploration_rate
        }


contextual_bandit_engine = ContextualBanditEngine()
