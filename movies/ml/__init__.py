# ML recommendation package
from .recommendation_engine import (
    RecommendationEngine,
    ContentBasedRecommender,
    HybridRecommender,
    recommendation_engine,
    content_recommender,
    hybrid_recommender
)

from .contextual_bandits import (
    ContextualBanditEngine,
    UserContext,
    BanditArm,
    BanditSelection,
    RewardFeedback,
    contextual_bandit_engine
)

from .diversity_engine import (
    DiversityEngine,
    DiversityCandidate,
    DiversityConfig,
    DiversityMetrics,
    MMRDiversifier,
    DPPDiversifier,
    GenreBalancer,
    EpsilonGreedyExplorer,
    SerendipityInjector,
    diversity_engine
)

from .explainability_engine import (
    ExplainabilityEngine,
    FeatureImportance,
    Explanation,
    ExplanationContext,
    explainability_engine
)

from .sentiment_analyzer import (
    SentimentAnalyzer,
    SentimentResult,
    sentiment_analyzer
)

from .embedding_service import (
    SemanticEmbeddingService,
    EmbeddingResult,
    semantic_embedding_service
)

from .pattern_recognition import (
    ViewingPatternAnalyzer,
    GenrePreference,
    ViewingTimePattern,
    BingePattern,
    RatingTrend,
    PatternSummary,
    viewing_pattern_analyzer
)
