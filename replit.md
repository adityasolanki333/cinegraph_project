# CineGraph - Movie & TV Recommendation Platform

## Overview
Full-stack movie/TV recommendation platform with AI-powered suggestions, community features, and social interactions.

## Architecture
- **Frontend**: React + TypeScript + Vite (port 5000)
- **Backend**: Django REST Framework (port 8000)
- **Database**: PostgreSQL (via `DATABASE_URL` secret)
- **Auth**: JWT (djangorestframework-simplejwt) — 15-min access / 7-day refresh; `CachedJWTAuthentication` caches user object 60s
- **Cache**: File-based by default (`.cache/` dir); switch via `CACHE_BACKEND=db` or `CACHE_BACKEND=locmem`

## Key Services / APIs
- **TMDB**: Movie/TV data (`TMDB_API_KEY`)
- **Gemini AI**: AI chat & recommendations (`GEMINI_API_KEY`), model `gemma-3-27b-it`
- **Pinecone**: Vector search for semantic recommendations (`PINECONE_API_KEY`)
- **RapidAPI**: External ratings & YouTube data (`RAPIDAPI_KEY`)

## Project Structure
```
client/         React frontend (Vite)
  src/
    lib/        Shared utilities (queryClient, tmdb, utils, etc.)
    pages/      Route-level page components
    components/ Reusable UI components (ai-chat.tsx — SSE chat with AbortController)
    contexts/   React context providers
    hooks/      Custom hooks
movieflix/      Django project settings & config
movies/         Django app (models, views, APIs)
  api.py        TMDB HTTP client — persistent requests.Session, connection pooling, retry adapter
  recommendations_api.py  AI chat (SSE), voice chat, pattern analysis
  api_views/    Organized API view modules
  migrations/   Database migrations
  ml/           ML recommendation engine
shared/         Shared TypeScript types
gunicorn.conf.py  Production WSGI server config
```

## Workflows
- **Start application**: `npm run dev` — Vite frontend on port 5000 (webview)
- **Backend**: `python3 manage.py runserver 127.0.0.1:8000` — Django API on port 8000 (console)

## Required Secrets
- `SESSION_SECRET` — Django secret key
- `DATABASE_URL` — PostgreSQL connection string
- `TMDB_API_KEY` — The Movie Database API key
- `GEMINI_API_KEY` — Google Gemini AI key
- `PINECONE_API_KEY` — Pinecone vector DB key
- `RAPIDAPI_KEY` — RapidAPI key for external services

## Deployment
- Target: `autoscale`
- Build: `npm run build && python3 manage.py collectstatic --noinput`
- Run: `gunicorn -c gunicorn.conf.py movieflix.wsgi:application`
- Note: `DEBUG` defaults to `False` in production; set `DEBUG=True` in `.env` for local dev

## Production Hardening (applied)
- `DEBUG=False` in production; `DEBUG=True` in `.env` for dev
- `ALLOWED_HOSTS` — no wildcard; only Replit domains + localhost
- WhiteNoise middleware for compressed static files (production-only `CompressedManifestStaticFilesStorage`)
- Security headers: HSTS, secure cookies, X-Frame-Options, XSS filter (all gated on `DEBUG=False`)
- `SECURE_PROXY_SSL_HEADER` set; `SECURE_SSL_REDIRECT=False` (Replit terminates SSL at proxy)
- File-based cache persists across restarts; correct backend selected via `CACHE_BACKEND` env var

## Performance Optimisations (applied)
- `movies/api.py`: persistent `requests.Session` with HTTPAdapter (pool_connections=10, pool_maxsize=20) and Retry (3 retries on 429/5xx)
- `recommendations_api.py`: `get_user_context` runs 5 DB queries in parallel (ThreadPoolExecutor)
- `recommendations_api.py`: `pattern_analyze` evaluates querysets to lists once, reuses counts — eliminates 6 redundant COUNT queries
- `recommendations_api.py`: SSE keep-alive ping yielded before Gemini call to prevent proxy timeout on cold-start
- `ai-chat.tsx`: `AbortController` cancels in-flight SSE stream on new message or unmount; sessionStorage writes debounced 500ms
- Composite DB indexes on (user, timestamp) for `ViewingHistory`, `UserReview`, `UserWatchlist`, `UserFavorites` (migration 0013)

## Notes
- Vite proxies `/api/*` requests to Django at `127.0.0.1:8000`
- Frontend uses JWT tokens stored in localStorage
- Mood queries (`happy`, `sad`, etc.) always bypass cache and hit TMDB live; scan pages 1+2 trending + pages 1-3 discover to guarantee 4 movie cards
- AI chat cache key prefix: `chat:v3`; mood queries bypass both read and write cache
- `gunicorn.conf.py`: 2 workers, 120s timeout, 1000 max_requests with jitter, preload_app=True
