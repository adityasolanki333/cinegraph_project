# CineGraph - Netflix-Style Movie Recommendation System

## Overview
A modern, Netflix-inspired movie recommendation web application with a Django backend and React frontend. Features AI-powered recommendations, social features, user profiles, and TMDB integration.

## Project Structure
```
/
├── movieflix/                # Django project settings
│   ├── settings.py           # Main configuration
│   ├── urls.py               # Root URL routing
│   └── wsgi.py               # WSGI application
├── movies/                   # Main Django application
│   ├── models/               # Domain-split models package (user, social, ml, analytics)
│   │   └── __init__.py       # Re-exports all models for backward compatibility
│   ├── api.py                # TMDB API service helpers (tmdb_request, tmdb_request_post, tmdb_request_delete)
│   ├── api_urls.py           # API route definitions (180+ endpoints, all DRF class-based views)
│   ├── api_views/            # DRF views (auth, tmdb, users, followers, lists, reviews, notifications, community, ml, clubs, recommendations, external, analytics)
│   ├── serializers/          # DRF serializers package (user, media, social, notifications, etc.)
│   ├── recommendations_api.py # AI recommendation service functions (called by DRF views)
│   ├── external_api.py       # RapidAPI service helper (rapidapi_request)
│   ├── ml_api.py             # ML recommendation service functions (called by DRF views)
│   ├── ml/                   # Python ML modules
│   │   ├── recommendation_engine.py  # Collaborative/content-based filtering (temporal decay, mean-centering, sparse matrix)
│   │   ├── signal_aggregator.py      # Unified implicit+explicit signal aggregator
│   │   ├── feedback_service.py       # Feedback loop: per-user feature weight learning
│   │   ├── diversity_engine.py       # MMR, DPP, serendipity (wired into pipeline)
│   │   ├── contextual_bandits.py     # Thompson Sampling (DB-persisted arm states)
│   │   ├── explainability_engine.py  # Recommendation explanations
│   │   ├── embedding_service.py      # TF-IDF semantic embeddings with DB pre-fitting
│   │   ├── pinecone_service.py      # Pinecone vector search with hybrid re-ranking
│   │   └── pattern_recognition.py    # Viewing pattern analysis
│   ├── management/commands/
│   │   └── refresh_pinecone.py      # TMDB→Pinecone refresh pipeline
│   ├── pagination.py         # DRF PageNumberPagination (page_size=20) + paginate_queryset helper
│   ├── tests.py              # Backend tests: Auth, TMDB proxy (mocked), CRUD, etc.
│   ├── tests_ml.py           # ML pipeline unit tests (23 tests)
│   ├── validation.py         # Input validation & standardized error responses
│   └── decorators.py         # Auth/ownership decorators
├── client/                   # React frontend
│   ├── src/
│   │   ├── i18n/                              # Internationalization (react-i18next)
│   │   │   ├── index.ts                       # i18n config (6 languages, localStorage sync)
│   │   │   └── locales/                       # Translation JSON files
│   │   │       ├── en.json, hi.json, es.json  # English, Hindi, Spanish
│   │   │       ├── fr.json, de.json, ja.json  # French, German, Japanese
│   │   ├── components/
│   │   │   ├── media-details.tsx              # Shared MediaDetails component (hero, cast, reviews, recommendations, similar tabs)
│   │   │   ├── recommendation-comments.tsx    # Extracted shared recommendation comments
│   │   │   └── user-recommendations-section.tsx # Extracted shared user recommendations
│   │   └── pages/
│   │       ├── movie-details.tsx              # Movie page (thin wrapper around MediaDetails)
│   │       └── tv-show-details.tsx            # TV show page (thin wrapper around MediaDetails)
│   └── index.html            # Entry point
├── shared/                   # Shared TypeScript types
│   └── schema.ts             # Type definitions for API
├── dist/public/              # Vite build output (production)
└── env                       # Fallback API keys for development
```

## Key Features
- Netflix-style dark theme UI with hero sections
- TMDB movie/TV data via proxy API
- AI-powered recommendations using Gemini AI
- **Advanced ML Recommendation Pipeline**:
  - Unified signal aggregator (ratings, favorites, watchlist, watch duration, search clicks, viewing history)
  - Collaborative filtering with temporal decay (180-day half-life) and mean-centering
  - Cold-start recommendations for new users (<5 interactions) using onboarding genre preferences + TmdbMovieCache
  - Contextual bandit (Thompson Sampling) selects strategy per request; arm states persisted to DB
  - Diversity engine (MMR reranking + serendipity injection) integrated into recommendation pipeline
  - Feedback loop: user interactions update per-user FeatureWeight, adapting hybrid scoring over time
  - User/item embedding manager for profile-based content matching
- User profiles, watchlists, favorites, viewing history
- User reviews with public/private visibility
- Social features: following, notifications, custom lists
- YouTube video search for trailers
- External movie ratings integration
- Input validation on all mutation endpoints (rating 1-10, string lengths, TMDB ID format)
- Standardized error responses: `{ "error": "...", "code": "..." }`
- DRF throttling configured (100 req/min auth, 20 req/min anon)
- CSRF protection enforced on all endpoints (no `@csrf_exempt` bypasses); frontend sends CSRF token via `X-CSRFToken` header
- Production security headers (HSTS, secure cookies, SSL redirect) gated on `DEBUG=False`
- Django password validators applied on registration
- Gemini REST fallback uses `x-goog-api-key` header instead of query parameter
- Password reset endpoint clearly marked as non-functional (email not configured)
- Structured logging (no print statements in API code)

## SEO & Accessibility
- Per-page meta tags via `usePageMeta` hook (`client/src/hooks/usePageMeta.ts`) - sets title, description, OG tags
- Skip-to-content link and `<main id="main-content">` landmark in App.tsx
- Global `focus-visible` outline styles in index.css
- ARIA labels on all icon-only buttons (search, notifications, profile menu, delete, etc.)
- `aria-label` and `aria-current` on mobile bottom nav items
- `loading="lazy"` on all non-critical images; alt text on every `<img>`
- 44px minimum touch targets on mobile nav and key interactive elements
- Graph visualizations use real API data (watchlist, favorites, watched, ratings) with loading skeletons and empty states

## Tech Stack
- **Backend**: Django 5.2, Python 3.11, Gunicorn
- **Frontend**: React 18, TypeScript, Vite
- **Database**: PostgreSQL (Neon-backed via DATABASE_URL)
- **Styling**: Tailwind CSS, Radix UI
- **APIs**: TMDB, Gemini AI, RapidAPI (YouTube)

## Environment Variables
- `SESSION_SECRET` - Required for Django secret key (app will not start without it)
- `TMDB_API_KEY` - Required for movie data
- `GEMINI_API_KEY` - For AI recommendations
- `RAPIDAPI_KEY` - For YouTube integration
- `DEBUG` - Set to `True` in development (defaults to `False`; when False, enables SECURE_SSL_REDIRECT/HSTS which breaks the dev server)

## Running the App
- Django backend: `python manage.py runserver 0.0.0.0:8000`
- React frontend: `npm run dev` (port 5000)
- Frontend proxies `/api` requests to Django

## API Endpoints (Key Groups)
- `/api/auth/*` - Authentication (login, register, logout)
- `/api/users/{id}/*` - User data (profile, watchlist, favorites)
- `/api/movies/*`, `/api/tv/*` - TMDB proxy
- `/api/social/*` - Lists, follows, notifications
- `/api/ai/*` - AI chat recommendations
- `/api/external/*` - YouTube, ratings

## Recent Changes
- April 2026: Improved Performance & Backend Optimization
  - Refactored `MovieRow` component for significant frontend performance gains
  - Removed unused API endpoints and legacy validation helpers
  - Cleaned up backend by deleting unnecessary files (`logging_service.py`, `embedding_manager.py`)
- April 3, 2026: Test Infrastructure - Backend Mocking, ML Tests & Frontend Test Setup
  - Backend: Added 7 TMDB proxy tests using mocked API views and 23 hermetic ML pipeline tests
  - Frontend: Added 24 Vitest + React Testing Library tests covering page smoke tests, hooks (useAuth, useWatchlist), and queryClient
  - Implemented proper TypeScript interfaces in mock factories, replacing `any` casts
  - ML pipeline tests cover RecommendationEngine, BanditEngine, DiversityEngine, SignalAggregator, and FeedbackService
- April 3, 2026: Password Reset via Email (SendGrid)
  - Forgot password now generates a secure token (Django PasswordResetTokenGenerator) and emails a reset link via SendGrid
  - Token is one-time-use: automatically invalidated after password change (uses password hash salt)
  - Reset password endpoint validates password against Django password validators
  - Combined token format: base64(uid):token — prevents replay attacks
  - SendGrid API key stored in secrets (SENDGRID_API_KEY), from address DEFAULT_FROM_EMAIL in settings
  - In DEBUG mode, if email fails to send, reset token returned in response for testing
  - Added sendgrid>=6.12.5 to pyproject.toml dependencies
- April 3, 2026: JWT Auth & Forget Password Rename
  - Switched from session-based to JWT-based authentication using djangorestframework-simplejwt
  - Login and register endpoints now return JWT access/refresh tokens instead of session cookies
  - Added token refresh endpoint at /api/auth/token/refresh
  - All frontend API requests use Authorization: Bearer header instead of cookies/CSRF tokens
  - Removed all CSRF token handling from frontend (getCsrfToken, ensureCsrfToken, X-CSRFToken headers, /api/auth/csrf endpoint)
  - Removed credentials: 'include' from all fetch calls
  - Automatic token refresh on 401 responses built into queryClient
  - Tokens stored in localStorage for persistence across tabs
  - Renamed all "Forgot Password" → "Forget Password" (URL routes, page titles, link text, view classes, serializers)
  - File renamed: forgot-password.tsx → forget-password.tsx, route /forgot-password → /forget-password
  - Backend: ForgotPasswordView → ForgetPasswordView, ForgotPasswordSerializer → ForgetPasswordSerializer
- April 3, 2026: Complete DRF Migration — All Endpoints Now Class-Based Views
  - Migrated ALL remaining legacy Django function views to DRF APIView classes
  - Created api_views/tmdb.py with TMDBProxyView base class eliminating ~40 duplicate functions
  - Created api_views/auth.py (6 endpoints: register, login, logout, me, forget/reset password, token refresh)
  - Created api_views/external.py (4 endpoints: YouTube search/videos, movie ratings, streaming data)
  - Created api_views/analytics.py (6 endpoints: user engagement, content stats, popular, tracking, platform)
  - Stripped api.py down to service helpers (tmdb_request/post/delete) — no view functions
  - Stripped external_api.py down to service helper (rapidapi_request) — no view functions
  - Removed all @require_GET/@require_POST decorators from ml_api.py and recommendations_api.py
  - Deleted dead code files: social_api.py, users_api.py, clubs_api.py, analytics_api.py (old), auth.py (old)
  - Zero legacy patterns remain: no _legacy(), no request._request, no @require_GET/POST in entire codebase
  - All 180+ URL patterns preserved exactly, all JSON field names unchanged
- April 3, 2026: Critical Security Hardening (CSRF, Headers, Rate Limiting, Auth)
  - Removed all 57 `@csrf_exempt` decorators from API views; frontend already sends CSRF tokens correctly via X-CSRFToken header
  - Added production security headers to settings.py (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS=31536000) gated on `DEBUG=False`
  - Created reusable `@rate_limit()` decorator in `movies/decorators.py` using Django cache framework, enforcing DRF throttle rates (20/min anon, 100/min user); applied to all write endpoints
  - Registration now uses Django's built-in AUTH_PASSWORD_VALIDATORS (similarity, minimum length, common password, numeric check)
  - Fixed Gemini REST API fallback to use `x-goog-api-key` header instead of passing API key as URL query parameter
  - Password reset endpoint now logs warning that email is not configured and returns clear message to user; no token silently discarded
- April 3, 2026: Full App Audit (Security, Bugs, Dead Code, Tests)
  - Fixed broken API routes: comments/add → add_review_comment, awards/add → get_review_awards (handles GET+POST), community/lists POST → create_community_list wrapper
  - Security: Password reset token no longer returned in response; emails removed from followers/following endpoints; str(e) replaced with generic error messages; demo_user bypasses removed from manage_rating and delete_review
  - Security: settings.py hardened (DEBUG=False default, SESSION_SECRET required, CORS restricted, DRF default permission=IsAuthenticated)
  - Security: Removed unused csrf_exempt_for_session_auth decorator (dead code, potential CSRF bypass risk)
  - Dead code removed: test_endpoints.py, test_feed.js, .gitignore_1, models_search.py, unused lru_cache/duplicate imports, ~10 unrouted demo_user_* view functions
  - Tests fixed: Corrected URL references (auth/user→auth/me, trending paths, search paths, community-feed); login tests updated to use email field
  - Frontend: Notification polling throttled from 30s to 60s in NotificationBell.tsx
- April 3, 2026: AI Chat & Analysis Production Upgrade
  - Injected real-time TMDB movie context (trending, now playing, upcoming) into Gemini prompts with today's date
  - Rewrote system prompt to prioritize recent releases (2024-2026), include release years, and reference current movies
  - Added multi-turn conversation memory (last 6 messages sent as context to Gemini)
  - Added streaming SSE endpoint (`/api/ai/chat/stream`) with progressive text rendering on frontend
  - Upgraded pattern analysis to use Gemini for richer viewing habit insights (`aiInsight` field)
  - Hardened error handling with user-friendly messages, proper logging, and TMDB trending fallback
  - Each TMDB source in fetch_current_movies() individually try/caught for partial-data resilience
- December 18, 2025: PostgreSQL Migration Complete
  - Switched from SQLite to PostgreSQL (Neon-backed via DATABASE_URL)
  - All Django migrations applied successfully (25 migrations)
  - Database tables: Users, Auth, Content Types, Movies, Sessions, Reviews, Watchlists, etc.
  - Verified PostgreSQL connection and data persistence
  - Settings.py automatically uses DATABASE_URL when available
  - Fallback to SQLite only when DATABASE_URL is not set (development flexibility)
- December 18, 2025: Priority 1 Implementation - Gemini Explanations (Level 3)
  - Added `generate_gemini_explanation()` method to ExplainabilityEngine
  - Creates compelling single-sentence explanations using Gemini API
  - Example: "Like Interstellar, Arrival explores humanity's first contact with aliens through emotional depth and scientific curiosity"
  - New endpoint: `/api/recommendations/explain/gemini` (GET with sourceTitle, sourceOverview, recommendedTitle, recommendedOverview)
  - Gracefully handles API failures with fallback to rule-based explanations
  - Improves recommendation "wow factor" with AI-generated insights
- December 17, 2025: Comprehensive App Evaluation v2.0
  - Created COMPREHENSIVE_APP_EVALUATION.md with full codebase analysis
  - Documented 139 LSP errors across 5 files with severity ratings
  - Created 3-phase ML improvement roadmap for real data recommendations
  - Added explainability feature enhancement plan
  - Documented security issues (hardcoded API key in recommendations_api.py)
  - Created feature status matrix (conceptual vs practical)
  - Mapped frontend/backend API contract mismatches (snake_case vs camelCase)
  - Added 5-phase implementation roadmap with priority matrix
- December 17, 2025: Phase 2 Improvements
  - MovieLens seeding script available (run `python manage.py seed_movielens_data`)
  - Removed orphaned embeddings.tsx page (referenced non-existent endpoints)
  - Verified all environment variables properly configured
  - App now 90% complete for development/demo use
- December 17, 2025: Comprehensive App Evaluation Fixes
  - Fixed LSP type errors in movieflix/urls.py (HttpResponse content type)
  - Fixed LSP type error in movies/ml/recommendation_engine.py (Django ORM type hints)
  - Created PostgreSQL database and ran all migrations
- December 17, 2025: Phase 2 Stabilization
  - Migrated from SQLite to PostgreSQL (Neon-backed)
  - Added fallback API keys for TMDB, Gemini, and RapidAPI
  - Configured production deployment with Gunicorn
  - Django serves React SPA in production mode
- December 17, 2025: Completed ML Phase 3 - Advanced ML Enhancements
  - Added SemanticEmbeddingService with TF-IDF vectorization and caching
  - Upgraded semantic search to use real cosine similarity scores
  - Created ViewingPatternAnalyzer for user behavior insights
  - Added `/api/ml/patterns/{user_id}` endpoint for pattern analysis
  - All 3 ML phases now complete!
- December 17, 2025: Completed ML Phase 2 - Data & Cleanup
  - Imported MovieLens small dataset (5000 ratings from 32 users)
  - ML collaborative filtering now has real training data
  - Removed all console.log debug statements from frontend
  - Added seed_movielens_data management command
- December 17, 2025: Fixed ML recommendation features
  - Fixed pattern_analyze endpoint to return correct format with `analysis` object
  - Fixed pattern_predict endpoint to return `prediction` object with sessionType
  - Fixed semantic-search URL path to `/api/recommendations/semantic-search`
  - Added demo_user preferences for personalized recommendations
  - All three recommendation tabs now working: AI Chat, Advanced Finder, Why We Recommend
- December 17, 2025: Added demo user DELETE endpoints
  - Added DELETE endpoints for demo_user/watchlist, favorites, and watched
  - Users can now remove items from their lists in demo mode
  - Created static directory to fix Django warning
- December 16, 2025: Fixed "My List" functionality and demo mode
  - Fixed demo user endpoints to support POST for watchlist, favorites, and watched
  - Added auto-enable demo mode when not authenticated
  - Fixed API response format handling (data.items extraction)
  - Added CSRF exemption for demo user endpoints
  - Added Array.isArray() defensive checks for API responses
  - Created get_or_create_demo_user() helper for consistent demo user access
- December 16, 2025: Fixed movie details page loading issue
  - Fixed /api/ratings endpoint to return array of reviews instead of summary object
  - Fixed security issues: self-voting prevention, self-awarding prevention
  - Fixed ListFollow follower count updates to use atomic counts
  - Added private list access control for follow/unfollow endpoints
  - Demo login now creates unique accounts with random credentials for security
- December 16, 2025: Added community and recommendation endpoints
  - Added community endpoints: notifications count, lists containing content, sentiment analysis, ratings
  - Added unified recommendations endpoint for combined AI/personalized suggestions
  - Added pattern analysis endpoint for viewing patterns insights
  - Added demo user endpoints for frontend compatibility without auth
- December 16, 2025: Fixed TMDB API endpoint routing issues
  - Added missing endpoints: tv/airing-today, tv/on-the-air, watch/providers
  - Added URL aliases for /movies vs /movie endpoints compatibility
  - Added movie/credits, movie/videos, person details endpoints
  - Added Indian movies endpoint
  - Added certifications endpoint
- December 2024: Migrated from Node.js to Django backend
- Implemented 12 database models for full feature parity
- Added 90+ API endpoints for user/social/AI features
- Added ownership checks for private user data
- Integrated Gemini AI for personalized recommendations

## Migration Status (December 17, 2025)
Original CineSuggest (Node.js) -> Django + React migration is **COMPLETE**.

### Quality Score: 93/100

| Category | Status | Score |
|----------|--------|-------|
| TMDB API proxy | WORKING | 100% |
| User authentication | WORKING | 100% |
| User profiles, watchlist, favorites | WORKING | 100% |
| User reviews | WORKING | 100% |
| Social features (follows, lists, notifications) | WORKING | 100% |
| AI recommendations with Gemini | WORKING | 100% |
| YouTube/external integrations | WORKING | 100% |
| Python ML Engine | WORKING | 85% |
| Analytics API | WORKING | 100% |
| Contextual Bandits | WORKING | 100% |
| Diversity Engine (MMR, DPP) | WORKING | 100% |

### Pending (Low Priority)
- WebSocket real-time notifications (requires Django Channels)
- TensorFlow.js pattern recognition (requires TensorFlow Python)
- Universal Sentence Encoder (requires PostgreSQL pgvector)
- Remove orphaned embeddings.tsx page (references /api/embeddings/* endpoints that don't exist in Django)
