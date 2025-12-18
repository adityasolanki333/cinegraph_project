"""
Contextual Bandit Engine using Thompson Sampling
Balances exploration (trying new recommendations) vs exploitation (using known preferences)

Algorithm: Thompson Sampling with Beta posterior
- Maintains Beta(α, β) distribution for each arm (recommendation strategy)
- α = successes + 1, β = failures + 1
- Samples from each distribution and selects arm with highest sample
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class UserContext:
    user_id: str
    time_of_day: str  # 'morning', 'afternoon', 'evening', 'night'
    day_of_week: str  # 'weekday', 'weekend'
    session_duration: float  # minutes
    recent_genres: List[str]
    recent_interaction_count: int
    device_type: Optional[str] = None
    mood: Optional[str] = None


@dataclass
class BanditArm:
    name: str
    alpha: float  # success count + 1
    beta: float   # failure count + 1
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
    reward: float  # 0-1 scale
    outcome_type: str  # 'clicked', 'watchlisted', 'rated_high', 'ignored', etc.


class ContextualBanditEngine:
    """Thompson Sampling-based contextual bandit for recommendation strategy selection"""
    
    PRIOR_ALPHA = 1.0  # Prior belief in success
    PRIOR_BETA = 1.0   # Prior belief in failure
    
    ARMS = [
        'collaborative',         # Collaborative filtering
        'content_based',         # Genre/metadata matching
        'trending',              # Popular/trending items
        'hybrid_ensemble',       # Ensemble of multiple strategies
        'exploration_random'     # Pure exploration (random)
    ]
    
    REWARD_MAP = {
        'clicked': 0.3,
        'watchlisted': 0.6,
        'rated_high': 1.0,      # Rating >= 7
        'rated_medium': 0.4,    # Rating 5-6
        'rated_low': 0.1,       # Rating <= 4
        'ignored': 0.0,
        'dismissed': -0.2,      # Negative signal
        'preference_positive': 0.8,
        'preference_negative': -0.1,
    }
    
    def __init__(self):
        self.arm_states: Dict[str, Dict[str, BanditArm]] = defaultdict(dict)
        self.experiments: Dict[str, Dict] = {}
    
    def extract_context(self, user_id: str, session_duration: float = 0, 
                        device_type: Optional[str] = None, mood: Optional[str] = None) -> UserContext:
        """Extract user context features from current session"""
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Determine time of day
        if 5 <= hour < 12:
            time_of_day = 'morning'
        elif 12 <= hour < 17:
            time_of_day = 'afternoon'
        elif 17 <= hour < 22:
            time_of_day = 'evening'
        else:
            time_of_day = 'night'
        
        # Weekday vs weekend
        is_weekend = 'weekend' if day_of_week >= 5 else 'weekday'
        
        # Get recent interactions from stored experiments
        user_experiments = [exp for exp_id, exp in self.experiments.items() 
                          if exp.get('user_id') == user_id]
        recent_count = len(user_experiments)
        
        # Extract recent genres (simplified - would normally come from database)
        recent_genres = []
        for exp in user_experiments[-10:]:
            context = exp.get('context', {})
            genres = context.get('genres', [])
            recent_genres.extend(genres)
        recent_genres = list(set(recent_genres))[:5]
        
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
        """Get current state of all bandit arms for a user"""
        arm_states = []
        
        for arm_name in self.ARMS:
            # Get or initialize arm state for this user
            if arm_name not in self.arm_states[user_id]:
                self.arm_states[user_id][arm_name] = BanditArm(
                    name=arm_name,
                    alpha=self.PRIOR_ALPHA,
                    beta=self.PRIOR_BETA,
                    pulls=0,
                    rewards=0,
                    success_rate=0.0
                )
            arm_states.append(self.arm_states[user_id][arm_name])
        
        return arm_states
    
    def _sample_beta(self, alpha: float, beta: float) -> float:
        """Sample from Beta distribution using numpy"""
        return np.random.beta(alpha, beta)
    
    def select_arm(self, context: UserContext) -> BanditSelection:
        """
        Select best arm using Thompson Sampling
        Samples from Beta distribution for each arm and picks highest
        """
        arm_states = self.get_arm_states(context.user_id)
        arm_scores = []
        max_score = -1.0
        chosen_arm = self.ARMS[0]
        
        # Sample from each arm's posterior distribution
        for arm_state in arm_states:
            sampled_reward = self._sample_beta(arm_state.alpha, arm_state.beta)
            arm_scores.append({'arm': arm_state.name, 'score': sampled_reward})
            
            if sampled_reward > max_score:
                max_score = sampled_reward
                chosen_arm = arm_state.name
        
        # Calculate exploration rate (how uncertain we are)
        chosen_arm_state = next((a for a in arm_states if a.name == chosen_arm), None)
        exploration_rate = 1.0 / (1.0 + chosen_arm_state.pulls) if chosen_arm_state else 1.0
        
        return BanditSelection(
            arm_chosen=chosen_arm,
            sampled_reward=max_score,
            all_arm_scores=arm_scores,
            exploration_rate=exploration_rate
        )
    
    def select_contextual_arm(self, context: UserContext) -> BanditSelection:
        """
        Contextual arm selection with feature-based weighting
        Adjusts arm probabilities based on context features
        """
        arm_states = self.get_arm_states(context.user_id)
        arm_scores = []
        max_score = -1.0
        chosen_arm = self.ARMS[0]
        
        # Sample from each arm's posterior and adjust for context
        for arm_state in arm_states:
            sampled_reward = self._sample_beta(arm_state.alpha, arm_state.beta)
            
            # Context-based boosting
            context_boost = self._get_context_boost(arm_state.name, context)
            sampled_reward = sampled_reward * (1 + context_boost * 0.2)  # Up to 20% boost
            
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
        """
        Calculate context-based boost for an arm
        Returns 0-1 multiplier based on how well context matches arm strength
        """
        boost = 0.0
        
        # Collaborative filtering works better on weekends (more browsing)
        if arm_name == 'collaborative' and context.day_of_week == 'weekend':
            boost += 0.2
        
        # Trending works well in evening (leisure time)
        if arm_name == 'trending' and context.time_of_day == 'evening':
            boost += 0.25
        
        # Content-based good for new users (cold start)
        if arm_name == 'content_based' and context.recent_interaction_count < 5:
            boost += 0.4
        
        # Exploration during short sessions (user exploring)
        if arm_name == 'exploration_random' and context.session_duration < 5:
            boost += 0.3
        
        # Hybrid good for engaged users
        if arm_name == 'hybrid_ensemble' and context.session_duration > 15:
            boost += 0.25
        
        return min(boost, 1.0)
    
    def log_experiment(self, user_id: str, arm_chosen: str, context: UserContext,
                       exploration_rate: float) -> str:
        """Log a bandit experiment (arm selection)"""
        import uuid
        experiment_id = str(uuid.uuid4())
        
        self.experiments[experiment_id] = {
            'user_id': user_id,
            'experiment_type': 'thompson_sampling',
            'arm_chosen': arm_chosen,
            'context': {
                'time_of_day': context.time_of_day,
                'day_of_week': context.day_of_week,
                'session_duration': context.session_duration,
                'genres': context.recent_genres,
                'interaction_count': context.recent_interaction_count
            },
            'exploration_rate': exploration_rate,
            'reward': None,
            'created_at': datetime.now().isoformat()
        }
        
        # Update arm pulls
        if user_id in self.arm_states and arm_chosen in self.arm_states[user_id]:
            self.arm_states[user_id][arm_chosen].pulls += 1
        
        return experiment_id
    
    def update_reward(self, feedback: RewardFeedback) -> None:
        """Update experiment with reward (user feedback)"""
        if feedback.experiment_id not in self.experiments:
            return
        
        experiment = self.experiments[feedback.experiment_id]
        experiment['reward'] = feedback.reward
        experiment['outcome_type'] = feedback.outcome_type
        
        user_id = experiment['user_id']
        arm_chosen = experiment['arm_chosen']
        
        # Update arm state
        if user_id in self.arm_states and arm_chosen in self.arm_states[user_id]:
            arm = self.arm_states[user_id][arm_chosen]
            if feedback.reward >= 0.5:
                arm.alpha += 1
                arm.rewards += 1
            else:
                arm.beta += 1
            
            # Recalculate success rate
            total = arm.alpha + arm.beta - 2  # Subtract priors
            arm.success_rate = arm.rewards / total if total > 0 else 0.0
    
    def calculate_reward(self, outcome_type: str) -> float:
        """
        Calculate reward from user interaction
        Converts user actions to 0-1 reward signal
        """
        return self.REWARD_MAP.get(outcome_type, 0.0)
    
    def get_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get bandit statistics for monitoring"""
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


# Singleton instance
contextual_bandit_engine = ContextualBanditEngine()
