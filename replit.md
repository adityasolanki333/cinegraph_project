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
│   ├── validation.py         # Input validation & standardized error responses (error_response helper)
│   ├── ml/                   # Python ML modules
│   │   ├── recommendation_engine.py  # Collaborative/content-based filtering
│   │   ├── signal_aggregator.py      # Unified implicit+explicit signal aggregator
│   │   ├── feedback_service.py       # Per-user feature weight learning
│   │   ├── diversity_engine.py       # MMR, DPP, serendipity
│   │   ├── contextual_bandits.py     # Thompson Sampling
│   │   ├── explainability_engine.py  # Recommendation explanations
│   │   ├── embedding_service.py      # TF-IDF semantic embeddings
│   │   ├── pinecone_service.py       # Pinecone vector search
│   │   └── pattern_recognition.py    # Viewing pattern analysis
│   ├── management/commands/
│   │   └── refresh_pinecone.py      # TMDB→Pinecone refresh pipeline
│   ├── pagination.py         # DRF PageNumberPagination (page_size=20)
│   ├── tests.py              # Backend tests
│   ├── tests_ml.py           # ML pipeline unit tests (23 tests)
│   └── decorators.py         # Auth/ownership decorators
├── client/                   # React frontend
│   ├── src/
│   │   ├── i18n/             # Internationalization (react-i18next, 6 languages)
│   │   ├── components/       # Shared components (media-details, recommendation-comments, etc.)
│   │   ├── pages/            # Route pages
│   │   ├── hooks/            # Custom hooks (useAuth, useWatchlist, usePageMeta, etc.)
│   │   └── lib/              # Utilities (queryClient, api, defaultAvatars)
│   └── index.html
├── shared/                   # Shared TypeScript types (schema.ts, api-types.ts)
├── ml-latest-small/          # MovieLens dataset for ML engine
└── scripts/                  # Utility scripts (ingest_pinecone.py, post-merge.sh)
```

## Key Features
- Netflix-style dark theme UI with hero sections
- TMDB movie/TV data via proxy API
- AI-powered recommendations using Gemini AI (streaming SSE, multi-turn memory)
- Advanced ML pipeline: collaborative filtering, contextual bandits, diversity engine, feedback loop
- User profiles, watchlists, favorites, viewing history
- User reviews with public/private visibility
- Social features: following, notifications, custom lists, clubs
- YouTube video search for trailers
- JWT authentication with token refresh
- Password reset via SendGrid email
- Internationalization (6 languages)
- Movies page with tabs: discover, trending, top-rated, now-playing, upcoming, indian

## Security
- JWT auth (djangorestframework-simplejwt) with auto-refresh on 401
- DRF throttling (100 req/min auth, 20 req/min anon)
- Production security headers (HSTS, secure cookies, SSL redirect) gated on `DEBUG=False`
- Django password validators on registration
- No hardcoded secrets; SESSION_SECRET required to start
- Structured logging (no print statements in API code)

## Tech Stack
- **Backend**: Django 5.2, Python 3.11, DRF, Gunicorn
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Radix UI
- **Database**: PostgreSQL (Neon-backed via DATABASE_URL)
- **APIs**: TMDB, Gemini AI, RapidAPI (YouTube), Pinecone, SendGrid

## Environment Variables
- `SESSION_SECRET` - Required for Django secret key
- `TMDB_API_KEY` - Required for movie data
- `GEMINI_API_KEY` - For AI recommendations
- `RAPIDAPI_KEY` - For YouTube integration
- `DEBUG` - Set to `True` in development (defaults to `False`)
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` - For email functionality

## Running the App
- Django backend: `python manage.py runserver 0.0.0.0:8000`
- React frontend: `npm run dev` (port 5000)
- Frontend proxies `/api` requests to Django

## API Endpoints (Key Groups)
- `/api/auth/*` - Authentication (login, register, logout, token refresh)
- `/api/users/{id}/*` - User data (profile, watchlist, favorites)
- `/api/movies/*`, `/api/tv/*` - TMDB proxy
- `/api/social/*` - Lists, follows, notifications
- `/api/ai/*` - AI chat recommendations (streaming SSE)
- `/api/recommendations/*` - ML-powered recommendations
- `/api/external/*` - YouTube, ratings
- `/api/community/*` - Clubs, community features

## Key Patterns
- **Auth**: `getAuthHeaders()` → `Authorization: Bearer <token>` from localStorage
- **User profile**: `UserProfile` model with `profile_image_url` (TextField) and `bio`; always use `get_or_create`
- **Default avatars**: `client/src/lib/defaultAvatars.ts` uses `btoa(svg)` for data URI avatars with emoji + gradient backgrounds
- **Movies tabs**: URL param `?tab=` support (discover, trending, top-rated, now-playing, upcoming, indian)
- **Diversity slider**: `onValueChange` → visual only, `onValueCommit` → triggers API refetch via `pipelineRefreshKey`
- **Management command guard**: `sys.argv[1] in {'migrate',...}` before heavy ML init in apps.py
- **Gemini rate limits**: `gemini-2.0-flash` often 429; fallback to `gemma-3-12b-it`
