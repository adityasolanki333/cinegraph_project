# MovieFlix Comprehensive App Evaluation Report

**Generated:** December 17, 2025  
**Version:** 2.0 (Complete Review)  
**Status:** Full Assessment with ML Improvement Roadmap

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Code Quality Review](#code-quality-review)
3. [Unnecessary Code & Files to Remove](#unnecessary-code--files-to-remove)
4. [ML Implementation Analysis](#ml-implementation-analysis)
5. [ML Improvement Roadmap for Real Data Recommendations](#ml-improvement-roadmap-for-real-data-recommendations)
6. [Explainability Feature Plan](#explainability-feature-plan)
7. [Security Review](#security-review)
8. [Feature Assessment: Conceptual vs Practical](#feature-assessment-conceptual-vs-practical)
9. [Frontend/Backend API Mismatches](#frontendbackend-api-mismatches)
10. [Critical Bugs & Errors](#critical-bugs--errors)
11. [Implementation Roadmap](#implementation-roadmap)
12. [Priority Matrix](#priority-matrix)

---

## Executive Summary

### Overall Health Score: 6.5/10

**Strengths:**
- Well-structured Django backend with proper app separation
- React frontend with modern stack (TanStack Query, Tailwind, shadcn/ui)
- TMDB integration working correctly
- Basic ML infrastructure code in place
- Shared types between frontend/backend
- MovieLens seeding script available (requires running `python manage.py seed_movielens_data`)

**Critical Issues:**
- Hardcoded API key in recommendations_api.py (security vulnerability)
- Mock data file still exists and used in some paths
- ML models are conceptual (no trained artifacts/weights)
- API contract mismatches between frontend/backend (snake_case vs camelCase)
- 139 LSP errors across 5 files

**Recommended Actions:**
1. **Immediate:** Remove hardcoded API keys, fix security issues
2. **Short-term:** Remove dead code, fix API mismatches
3. **Medium-term:** Implement real ML pipeline with trained models
4. **Long-term:** Add proper A/B testing and monitoring

---

## Code Quality Review

### LSP Errors Summary

*Note: These counts are from live LSP diagnostics at time of evaluation.*

| File | Error Count | Severity |
|------|-------------|----------|
| `movies/recommendations_api.py` | 76 | High |
| `movies/ml_api.py` | 28 | Medium |
| `movies/ml/explainability_engine.py` | 23 | Medium |
| `client/src/lib/mock-data.ts` | 9 | Low |
| `shared/api-types.ts` | 3 | Low |

**Total: 139 diagnostics across 5 files** (verified via LSP)

### Code Smells Identified

1. **Inconsistent Naming Conventions**
   - Backend uses `snake_case`: `poster_path`, `tmdb_id`, `media_type`
   - Frontend expects `camelCase`: `posterPath`, `tmdbId`, `mediaType`
   - This causes runtime errors and requires constant translation

2. **Redundant Code Patterns**
   - Genre mapping duplicated in 5+ files (recommendations_api.py, ml_api.py, etc.)
   - User context gathering repeated across multiple API endpoints
   - TMDB request wrapper called inconsistently

3. **Missing Type Safety**
   - Python files lack proper type hints in many places
   - TypeScript `any` types used extensively in recommendations page

4. **Dead Imports**
   - Multiple unused imports in ML files
   - Circular import risks in `movies/ml/` modules

---

## Unnecessary Code & Files to Remove

### Files to Delete

| File/Directory | Reason | Impact |
|---------------|--------|--------|
| `client/src/lib/mock-data.ts` | Mock data should not exist in production | Low - requires refactoring components using it |
| `movies/management/commands/populate_movies.py` | Redundant - overlaps with seed_demo_data | None |
| `db.sqlite3` | Development artifact - using PostgreSQL | None |

### Commands to Consolidate

Currently there are **3 seeding commands**:
```
movies/management/commands/
├── populate_movies.py      # DELETE - redundant
├── seed_demo_data.py       # KEEP - primary seeder
└── seed_movielens_data.py  # KEEP - ML dataset
```

**Recommendation:** Merge `populate_movies.py` into `seed_demo_data.py`

### Unused/Conceptual UI Components (Verify Usage Before Removing)

| Component | Status | Action |
|-----------|--------|--------|
| `graph-visualizations.tsx` | Imported but not wired to backend | Review - likely remove |
| `ab-experiment-creator.tsx` | UI exists, no backend persistence | Keep - wire to backend OR remove |
| `ab-experiment-results.tsx` | UI exists, uses mock data | Keep - wire to backend OR remove |
| `video-reviews.tsx` | Conceptual only | Review - likely remove |
| `milestone-celebration.tsx` | Partially wired | Keep |

### Dead Code in ML Module

```python
# movies/ml/recommendation_engine.py
# Line 28-34: build_user_item_matrix() ignores ratings_data parameter
# This suggests incomplete refactoring

# movies/ml/contextual_bandits.py
# All state is in-memory - experiments dict lost on restart
# Either persist to DB or document as demo-only
```

---

## ML Implementation Analysis

### Current State Assessment

| Component | File | Status | Data Source |
|-----------|------|--------|-------------|
| Collaborative Filtering | `recommendation_engine.py` | ⚠️ Partial | User reviews (sparse) |
| Content-Based Filtering | `recommendation_engine.py` | ⚠️ Partial | TMDB metadata |
| Hybrid Recommender | `recommendation_engine.py` | ⚠️ Partial | Combined |
| Explainability Engine | `explainability_engine.py` | ✅ Complete | Heuristic-based |
| Contextual Bandits | `contextual_bandits.py` | ⚠️ Conceptual | In-memory only |
| Diversity Engine | `diversity_engine.py` | ✅ Complete | N/A |
| Sentiment Analyzer | `sentiment_analyzer.py` | ✅ Complete | VADER |
| Embedding Service | `embedding_service.py` | ⚠️ Partial | TF-IDF |
| Pattern Recognition | `pattern_recognition.py` | ⚠️ Conceptual | Limited |

### Why Recommendations Are Not Truly "Real Data" Based

1. **No Trained Model Artifacts:** No `.pkl`, `.h5`, or model weights exist
2. **Sparse User Data:** Few actual user ratings means collaborative filtering often returns empty
3. **Fallback to TMDB:** Most recommendations come directly from TMDB trending/popular APIs
4. **No Feature Store:** User features not pre-computed or cached
5. **No Offline Evaluation:** No A/B test results or offline metrics
6. **Cold Start Problem:** New users get generic recommendations

---

## ML Improvement Roadmap for Real Data Recommendations

### Phase 1: Data Pipeline Foundation (Week 1-2)

#### 1.1 Establish Robust Data Sources
```
Priority Data Sources:
1. MovieLens Dataset (seed script available)
   - Status: Script exists but data needs to be seeded
   - Required Action: Run `python manage.py seed_movielens_data`
   - Goal: 100k+ ratings for effective collaborative filtering

2. User Interaction Data (already captured)
   - Reviews: UserReview model ✅
   - Watchlist: UserWatchlist model ✅
   - History: ViewingHistory model ✅
   - Favorites: UserFavorites model ✅

3. TMDB Metadata (needs caching)
   - Genres, cast, crew, keywords
   - Cache in database for offline training
   - Currently fetched on-demand (slow)
```

#### 1.2 Feature Engineering Schema
```python
# Required features for real recommendations:

User Features:
- genre_preference_vector: [28 dimensions for TMDB genres]
- avg_rating_given: float
- rating_variance: float
- preferred_decades: List[str]
- viewing_velocity: movies_per_week
- binge_score: 0-1
- active_hours: preferred watching times

Item Features:
- genre_vector: [28 dimensions]
- popularity_score: normalized 0-1
- recency_score: decay function from release
- quality_score: vote_average normalized
- cast_embedding: averaged actor features
- director_style_embedding: director feature vector
```

#### 1.3 Database Schema Additions
```python
# Add to movies/models.py

class MLUserFeatures(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    genre_vector = models.JSONField(default=list)
    avg_rating = models.FloatField(default=0.0)
    rating_variance = models.FloatField(default=0.0)
    feature_version = models.CharField(max_length=20, default='v1.0')
    computed_at = models.DateTimeField(auto_now=True)

class MLItemFeatures(models.Model):
    tmdb_id = models.IntegerField(primary_key=True)
    media_type = models.CharField(max_length=10)
    genre_vector = models.JSONField(default=list)
    embedding = models.JSONField(default=list)
    feature_version = models.CharField(max_length=20, default='v1.0')
    computed_at = models.DateTimeField(auto_now=True)

class MLModelArtifact(models.Model):
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=20)
    model_path = models.CharField(max_length=500)
    metrics = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

### Phase 2: Model Training Pipeline (Week 3-4)

#### 2.1 Baseline Model: Matrix Factorization
```python
# movies/ml/training/matrix_factorization.py (NEW FILE)

from sklearn.decomposition import TruncatedSVD
import numpy as np
import joblib

class MatrixFactorizationTrainer:
    def __init__(self, n_factors=50):
        self.n_factors = n_factors
        self.model = TruncatedSVD(n_components=n_factors)
    
    def train(self, user_item_matrix):
        """Train SVD model on user-item matrix"""
        self.user_factors = self.model.fit_transform(user_item_matrix)
        self.item_factors = self.model.components_.T
        return self
    
    def predict(self, user_idx, item_idx):
        """Predict rating for user-item pair"""
        return np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
    
    def get_recommendations(self, user_idx, n=20, exclude_seen=None):
        """Get top-n recommendations for a user"""
        scores = np.dot(self.user_factors[user_idx], self.item_factors.T)
        if exclude_seen:
            scores[list(exclude_seen)] = -np.inf
        top_indices = np.argsort(scores)[::-1][:n]
        return [(idx, scores[idx]) for idx in top_indices]
    
    def save(self, path):
        """Save trained model artifacts"""
        joblib.dump({
            'user_factors': self.user_factors,
            'item_factors': self.item_factors,
            'model': self.model
        }, path)
    
    def load(self, path):
        """Load trained model artifacts"""
        data = joblib.load(path)
        self.user_factors = data['user_factors']
        self.item_factors = data['item_factors']
        self.model = data['model']
        return self
```

#### 2.2 Training Management Command
```python
# movies/management/commands/train_models.py (NEW FILE)

from django.core.management.base import BaseCommand
from movies.ml.training.matrix_factorization import MatrixFactorizationTrainer
from movies.models import UserReview, MLModelArtifact
import numpy as np
import os

class Command(BaseCommand):
    help = 'Train ML recommendation models'
    
    def add_arguments(self, parser):
        parser.add_argument('--model', type=str, default='collaborative')
        parser.add_argument('--version', type=str, default='v1.0')
    
    def handle(self, *args, **options):
        model_name = options['model']
        version = options['version']
        
        if model_name == 'collaborative':
            self.train_collaborative(version)
    
    def train_collaborative(self, version):
        # Build user-item matrix from reviews
        reviews = UserReview.objects.all().values('user_id', 'tmdb_id', 'rating')
        
        user_ids = sorted(set(r['user_id'] for r in reviews))
        item_ids = sorted(set(r['tmdb_id'] for r in reviews))
        
        user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        item_to_idx = {iid: idx for idx, iid in enumerate(item_ids)}
        
        matrix = np.zeros((len(user_ids), len(item_ids)))
        for r in reviews:
            ui = user_to_idx[r['user_id']]
            ii = item_to_idx[r['tmdb_id']]
            matrix[ui, ii] = r['rating']
        
        # Train model
        trainer = MatrixFactorizationTrainer(n_factors=50)
        trainer.train(matrix)
        
        # Save artifacts
        model_dir = 'models/'
        os.makedirs(model_dir, exist_ok=True)
        model_path = f'{model_dir}collaborative_{version}.pkl'
        trainer.save(model_path)
        
        # Record in database
        MLModelArtifact.objects.update_or_create(
            model_name='collaborative',
            model_version=version,
            defaults={
                'model_path': model_path,
                'is_active': True,
                'metrics': {'n_users': len(user_ids), 'n_items': len(item_ids)}
            }
        )
        
        self.stdout.write(f'Trained collaborative model {version}')
```

#### 2.3 Hybrid Model Pipeline Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   RECOMMENDATION PIPELINE                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         STAGE 1: CANDIDATE GENERATION                │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │   │
│  │  │Collaborative│ │Content-Based│ │  Trending   │    │   │
│  │  │   Top 100   │ │   Top 100   │ │   Top 50    │    │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           STAGE 2: PRECISION RANKING                 │   │
│  │  • Combine & deduplicate candidates                  │   │
│  │  • Apply user preference weights                     │   │
│  │  • Score with trained ranking model                  │   │
│  │  • Return top 50 candidates                          │   │
│  └──────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          STAGE 3: RE-RANKING & DIVERSITY             │   │
│  │  • Apply MMR diversity algorithm                     │   │
│  │  • Apply business rules (recency, popularity)        │   │
│  │  • Generate explanations for each item               │   │
│  │  • Return final top 20 with explanations             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Phase 3: Model Serving & Integration (Week 5-6)

#### 3.1 Inference Pipeline
```python
# movies/ml/inference_pipeline.py (NEW FILE)

class RecommendationPipeline:
    def __init__(self):
        self.model_registry = ModelRegistry()
        self.feature_store = FeatureStore()
        self.explainer = ExplainabilityEngine()
    
    def get_recommendations(self, user_id, n=20, explain=True):
        # Load user features
        user_features = self.feature_store.get_user_features(user_id)
        
        # Handle cold start
        if not user_features:
            return self._get_cold_start_recommendations(n)
        
        # Get active model
        model = self.model_registry.get_active_model('hybrid')
        
        # Generate candidates from multiple sources
        candidates = self._generate_candidates(user_id, user_features)
        
        # Rank candidates with trained model
        ranked = model.rank(user_features, candidates)
        
        # Apply diversity
        diversified = self._apply_diversity(ranked)
        
        # Generate explanations
        if explain:
            for item in diversified[:n]:
                item['explanation'] = self.explainer.explain(
                    user_id, item['tmdb_id'], 
                    model_contributions=item.get('feature_contributions')
                )
        
        return diversified[:n]
    
    def _get_cold_start_recommendations(self, n):
        """Fallback for new users without history"""
        # Use trending + high-rated as baseline
        from movies.api import tmdb_request
        trending = tmdb_request("/trending/all/week")
        return [{
            'tmdb_id': item['id'],
            'title': item.get('title') or item.get('name'),
            'score': 0.5,
            'reason': 'Popular right now',
            'strategy': 'cold_start'
        } for item in trending.get('results', [])[:n]]
```

#### 3.2 API Response with Model Metadata
```python
# Updated API response format

{
    "recommendations": [
        {
            "tmdbId": 123,
            "title": "Movie Title",
            "score": 0.87,
            "explanation": {
                "primaryReason": "Similar to movies you loved",
                "factors": [
                    {"name": "Genre Match", "percentage": 35},
                    {"name": "Rating Quality", "percentage": 25},
                    {"name": "Similar Users", "percentage": 20}
                ]
            }
        }
    ],
    "metadata": {
        "modelVersion": "hybrid_v1.2",
        "modelTrainedAt": "2025-12-15T02:00:00Z",
        "inferenceTimeMs": 45,
        "candidateCount": 500,
        "diversityScore": 0.72,
        "strategy": "hybrid"
    }
}
```

---

## Explainability Feature Plan

### Current Implementation Status
The `explainability_engine.py` is well-designed with:
- ✅ Feature importance calculation
- ✅ Template-based explanations
- ✅ Visual breakdown for UI
- ✅ Confidence scoring

### What's Missing for Real Explainability

1. **Integration with Real Model Scores**
   - Currently uses heuristics, not actual model weights
   - Need SHAP values or feature contributions from trained models

2. **Personalized Explanation Templates**
   ```python
   # Current: Generic templates
   "Matches your love for {genres}"
   
   # Improved: Personalized based on user history
   "You gave 5 stars to 'Inception' - this has similar mind-bending themes"
   "87% of users who loved 'Breaking Bad' also loved this"
   ```

3. **"Why This?" Feature in UI**
   - Add button on each movie card to show explanation
   - Visual charts for feature contribution breakdown
   - Similar items comparison

### Implementation Steps

#### Step 1: Connect to Trained Model Features
```python
# movies/ml/explainability_engine.py - Enhancement

def explain_with_model_features(self, user_id, tmdb_id, model_version):
    """Generate explanation using actual model feature contributions"""
    
    from .training.feature_store import FeatureStore
    
    # Get feature contributions from the trained model
    contributions = self._get_model_contributions(
        user_id=user_id,
        item_id=tmdb_id,
        model_version=model_version
    )
    
    # Convert to human-readable explanations
    explanations = []
    for feature, contribution in sorted(
        contributions.items(), 
        key=lambda x: abs(x[1]), 
        reverse=True
    )[:5]:
        explanations.append({
            'feature': self.FEATURE_DISPLAY_NAMES.get(feature, feature),
            'contribution': contribution,
            'direction': 'positive' if contribution > 0 else 'negative',
            'human_readable': self._feature_to_text(feature, contribution)
        })
    
    return explanations
```

#### Step 2: Add Dedicated Explanation Endpoint
```python
# movies/recommendations_api.py - Add new endpoint

@require_GET
def explain_recommendation(request, tmdb_id):
    """Get detailed explanation for why an item is recommended"""
    user = request.user if request.user.is_authenticated else None
    media_type = request.GET.get('media_type', 'movie')
    
    if not user:
        return JsonResponse({
            'tmdbId': tmdb_id,
            'explanation': {
                'primaryReason': 'This is a popular title',
                'factors': [],
                'confidence': 0.5
            }
        })
    
    explanation = explainability_engine.explain_recommendation(
        user_id=str(user.id),
        tmdb_id=int(tmdb_id),
        media_type=media_type
    )
    
    return JsonResponse({
        'tmdbId': tmdb_id,
        'mediaType': media_type,
        'explanation': explainability_engine.to_dict(explanation)
    })
```

#### Step 3: Frontend "Why This?" Component
```typescript
// client/src/components/recommendation-explanation.tsx

interface ExplanationProps {
  tmdbId: number;
  mediaType: string;
}

export function RecommendationExplanation({ tmdbId, mediaType }: ExplanationProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['/api/recommendations/explain', tmdbId],
    queryFn: () => fetch(`/api/recommendations/explain/${tmdbId}?media_type=${mediaType}`)
      .then(res => res.json())
  });
  
  if (isLoading) return <Skeleton className="h-32" />;
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="h-5 w-5" />
          Why We Recommend This
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-lg font-medium">{data?.explanation?.primaryReason}</p>
        
        <div className="space-y-2">
          {data?.explanation?.factors?.map((factor: any) => (
            <div key={factor.name} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{factor.name}</span>
                <span className="font-medium">{factor.percentage}%</span>
              </div>
              <Progress value={factor.percentage} className="h-2" />
            </div>
          ))}
        </div>
        
        <div className="text-sm text-muted-foreground">
          Confidence: {Math.round((data?.explanation?.confidence || 0) * 100)}%
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Security Review

### Critical Issues 🔴

#### 1. Hardcoded API Key (CRITICAL)
```python
# movies/recommendations_api.py:15-16
GEMINI_API_KEY_FALLBACK = "AIzaSyBGMLjZAhyfNyQc5OoJscmaBS8zJEwEDqo"
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '') or GEMINI_API_KEY_FALLBACK

# FIX: Remove hardcoded key entirely
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY not configured - AI features disabled")
```

#### 2. Missing Rate Limiting
```python
# ML endpoints have no rate limiting - vulnerable to abuse

# FIX: Add django-ratelimit
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user_or_ip', rate='30/m', block=True)
@require_POST
def unified_recommendations(request):
    ...
```

#### 3. CSRF Token Inconsistency
```python
# Some endpoints have @csrf_exempt, others don't
# This creates security gaps

# RECOMMENDATION: Standardize approach
# Either: All mutation endpoints require CSRF
# Or: Use token-based auth for API clients
```

### Medium Issues 🟡

| Issue | File | Fix |
|-------|------|-----|
| Input not validated | ml_api.py | Add try/except for int conversions |
| No auth on some endpoints | recommendations_api.py | Add @login_required or document intent |
| demo_user fallback | Multiple | Document security implications |

### Recommendations

| Issue | Priority | Effort | Action |
|-------|----------|--------|--------|
| Remove hardcoded API key | Critical | 10 min | Delete line 15-16, verify env var |
| Add rate limiting | High | 2 hrs | Install django-ratelimit |
| Input validation | Medium | 4 hrs | Add validation across all endpoints |
| CSRF consistency | Medium | 2 hrs | Audit and standardize |

---

## Feature Assessment: Conceptual vs Practical

### Feature Status Matrix

| Feature | Frontend | Backend | Database | ML Model | Status |
|---------|----------|---------|----------|----------|--------|
| User Authentication | ✅ | ✅ | ✅ | N/A | **Practical** |
| Movie/TV Browsing | ✅ | ✅ | N/A | N/A | **Practical** |
| TMDB Search | ✅ | ✅ | N/A | N/A | **Practical** |
| AI Chat Recommendations | ✅ | ✅ | ✅ | N/A | **Practical** (Gemini) |
| User Reviews | ✅ | ✅ | ✅ | N/A | **Practical** |
| Watchlist | ✅ | ✅ | ✅ | N/A | **Practical** |
| Mood-Based Recommendations | ✅ | ✅ | N/A | N/A | **Practical** |
| User Impact Dashboard | ✅ | ✅ | ✅ | N/A | **Practical** |
| Social Features | ✅ | ✅ | ✅ | N/A | **Practical** |
| Notifications | ✅ | ✅ | ✅ | N/A | **Practical** |
| Collaborative Filtering | ✅ | ⚠️ | ✅ | ❌ | **Partial** - needs training |
| Content-Based Filtering | ⚠️ | ✅ | N/A | ⚠️ | **Partial** |
| Hybrid Recommendations | ✅ | ⚠️ | N/A | ❌ | **Partial** |
| Explainability | ✅ | ✅ | N/A | ⚠️ | **Partial** - heuristic |
| Contextual Bandits | ❌ | ✅ | ❌ | ⚠️ | **Conceptual** |
| A/B Experiments UI | ✅ | ❌ | ❌ | N/A | **Conceptual** |
| Graph Visualizations | ✅ | ❌ | N/A | N/A | **Conceptual** |
| Video Reviews | ✅ | ❌ | ❌ | N/A | **Conceptual** |
| Pattern Insights | ✅ | ⚠️ | ⚠️ | ❌ | **Partial** |

### Legend
- ✅ Fully implemented
- ⚠️ Partially implemented
- ❌ Not implemented
- N/A Not applicable

---

## Frontend/Backend API Mismatches

### Field Naming Inconsistencies

| Frontend Expects | Backend Returns | Impact |
|-----------------|-----------------|--------|
| `tmdbId` | `tmdb_id` | Runtime errors, manual mapping required |
| `posterPath` | `poster_path` | Images don't load |
| `mediaType` | `media_type` | Type discrimination fails |
| `voteAverage` | `vote_average` | Rating display issues |
| `releaseDate` | `release_date` | Date parsing fails |
| `firstName` | `first_name` | User display issues |

### Recommended Fix: Serialization Layer
```python
# movies/serializers.py (CREATE NEW FILE)

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def serialize_response(data):
    """Convert all keys to camelCase for frontend"""
    if isinstance(data, dict):
        return {to_camel_case(k): serialize_response(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [serialize_response(item) for item in data]
    return data

# Usage in views:
return JsonResponse(serialize_response({
    'tmdb_id': 123,
    'poster_path': '/path.jpg',
    'vote_average': 8.5
}))
# Returns: {"tmdbId": 123, "posterPath": "/path.jpg", "voteAverage": 8.5}
```

---

## Critical Bugs & Errors

### Bug #1: Collaborative Filtering Returns Empty for New Users
**Location:** `movies/ml/recommendation_engine.py:94-147`
**Issue:** New users not in matrix get no recommendations
**Fix:** Add cold-start fallback
```python
if user_id not in self.user_id_to_idx:
    return self._get_cold_start_recommendations(n_recommendations)
```

### Bug #2: Explainability Import Error
**Location:** `movies/ml/explainability_engine.py:509`
**Issue:** `models.Q` referenced without import
**Fix:** Add `from django.db.models import Q` at top

### Bug #3: Async Function Not Awaited
**Location:** `movies/recommendations_api.py:159`
**Issue:** `search_tmdb_for_movies` is async but called synchronously
**Fix:** Remove async or properly await

### Bug #4: Hardcoded API Key
**Location:** `movies/recommendations_api.py:15`
**Issue:** Security vulnerability - API key exposed
**Fix:** Remove hardcoded fallback

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1) - Security & Stability

| Task | Effort | Priority |
|------|--------|----------|
| Remove hardcoded API key | 30 min | P0 |
| Fix import errors in explainability_engine.py | 30 min | P0 |
| Add input validation to ML endpoints | 2 hrs | P1 |
| Create serialization layer for API responses | 4 hrs | P1 |
| Fix async function issue | 1 hr | P1 |

### Phase 2: Code Cleanup (Week 2)

| Task | Effort | Priority |
|------|--------|----------|
| Remove mock-data.ts and update components | 4 hrs | P1 |
| Consolidate seed commands | 2 hrs | P2 |
| Remove/hide conceptual features | 3 hrs | P2 |
| Fix all LSP errors | 4 hrs | P2 |

### Phase 3: ML Foundation (Week 3-4)

| Task | Effort | Priority |
|------|--------|----------|
| Create ML feature tables | 4 hrs | P1 |
| Implement feature computation pipeline | 8 hrs | P1 |
| Train baseline matrix factorization | 8 hrs | P1 |
| Add model serving infrastructure | 6 hrs | P1 |
| Implement cold-start fallback | 4 hrs | P1 |

### Phase 4: Explainability Enhancement (Week 5)

| Task | Effort | Priority |
|------|--------|----------|
| Connect explainability to trained models | 8 hrs | P2 |
| Add "Why This?" API endpoint | 4 hrs | P2 |
| Build visual explanation component | 6 hrs | P2 |

### Phase 5: Advanced Features (Week 6-8)

| Task | Effort | Priority |
|------|--------|----------|
| Persist contextual bandit experiments | 8 hrs | P3 |
| Build proper A/B testing framework | 16 hrs | P3 |
| Add recommendation feedback loop | 8 hrs | P3 |

---

## Priority Matrix

### Quick Wins (< 2 hours, High Value)
1. ⬜ Remove hardcoded API key
2. ⬜ Fix import errors in explainability_engine.py
3. ⬜ Add cold-start fallback for new users
4. ⬜ Create basic serialization functions

### Strategic Investments (> 8 hours, High Value)
1. ⬜ ML training pipeline with model artifacts
2. ⬜ Feature store implementation
3. ⬜ Model-connected explainability

### Technical Debt (Variable Time)
1. ⬜ Remove mock data
2. ⬜ Consolidate seeding commands
3. ⬜ Standardize error handling
4. ⬜ Fix all 139 LSP errors

---

## Summary

### Immediate Actions Required
1. **Security:** Remove hardcoded API key from recommendations_api.py
2. **Stability:** Fix LSP errors causing runtime issues
3. **Data Quality:** Ensure ML models use real trained weights

### Key Metrics to Track
- Recommendation click-through rate
- User engagement with explained recommendations
- Cold-start user retention
- Model inference latency

### Success Criteria for Real Recommendations
1. Trained model artifacts exist and are versioned
2. User gets personalized (not generic) recommendations
3. Explanations reference actual model factors
4. New users get reasonable cold-start experience
5. Recommendations improve with user feedback

---

*Document Version: 2.0*  
*Last Updated: December 17, 2025*  
*Next Review: After Phase 1 completion*
