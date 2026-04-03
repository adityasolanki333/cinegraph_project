import sys as _sys

_MGMT_COMMANDS = {'migrate', 'makemigrations', 'collectstatic', 'check',
                  'showmigrations', 'sqlmigrate', 'inspectdb', 'shell',
                  'dbshell', 'flush', 'loaddata', 'dumpdata'}
_is_mgmt = len(_sys.argv) > 1 and _sys.argv[1] in _MGMT_COMMANDS

if not _is_mgmt:
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
