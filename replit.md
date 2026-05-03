# CineGraph - Movie & TV Recommendation Platform

## Overview
Full-stack movie/TV recommendation platform with AI-powered suggestions, community features, and social interactions.

## Architecture
- **Frontend**: React + TypeScript + Vite (port 5000)
- **Backend**: Django REST Framework (port 8000)
- **Database**: PostgreSQL (via `DATABASE_URL` secret)
- **Auth**: JWT (djangorestframework-simplejwt)

## Key Services / APIs
- **TMDB**: Movie/TV data (`TMDB_API_KEY`)
- **Gemini AI**: AI chat & recommendations (`GEMINI_API_KEY`)
- **Pinecone**: Vector search for semantic recommendations (`PINECONE_API_KEY`)
- **RapidAPI**: External ratings & YouTube data (`RAPIDAPI_KEY`)

## Project Structure
```
client/         React frontend (Vite)
  src/
    lib/        Shared utilities (queryClient, tmdb, utils, etc.)
    pages/      Route-level page components
    components/ Reusable UI components
    contexts/   React context providers
    hooks/      Custom hooks
movieflix/      Django project settings & config
movies/         Django app (models, views, APIs)
  api_views/    Organized API view modules
  migrations/   Database migrations
  ml/           ML recommendation engine
shared/         Shared TypeScript types
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
- Run: `gunicorn --bind=0.0.0.0:5000 --reuse-port --workers=2 movieflix.wsgi:application`

## Notes
- Vite proxies `/api/*` requests to Django at `127.0.0.1:8000`
- Frontend uses JWT tokens stored in localStorage
- Missing `client/src/lib/` files were recreated during import (queryClient, utils, tmdb, feedback, routePrefetch, defaultAvatars)
