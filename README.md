# CineGraph

A Netflix-inspired movie and TV show recommendation platform with AI-powered suggestions, social features, and an advanced ML recommendation engine.

![CineGraph Homepage](screenshots/homepage.jpg)

## Features

- **Browse & Discover** - Explore trending, top-rated, now playing, upcoming, and Indian movies with a Netflix-style UI
- **AI Recommendations** - Get personalized movie suggestions powered by Google Gemini AI with streaming chat
- **ML Recommendation Engine** - Collaborative filtering, contextual bandits (Thompson Sampling), diversity engine (MMR + serendipity), and per-user feedback learning
- **TV Shows** - Browse airing today, on the air, popular, and top-rated TV series
- **User Profiles** - Custom avatars, bios, viewing history, and activity graphs
- **Social Features** - Follow users, create and share custom lists, join movie clubs
- **Reviews & Ratings** - Write reviews, vote on reviews, award badges
- **Watchlist & Favorites** - Track movies you want to watch and ones you love
- **Trailer Playback** - Watch YouTube trailers directly from movie details
- **Internationalization** - Available in 6 languages (English, Hindi, Spanish, French, German, Japanese)
- **Password Reset** - Secure email-based password reset via SendGrid

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.2, Django REST Framework, Python 3.11 |
| **Frontend** | React 18, TypeScript, Vite |
| **Database** | PostgreSQL (Neon) |
| **Styling** | Tailwind CSS, Radix UI, Framer Motion |
| **Auth** | JWT (djangorestframework-simplejwt) |
| **AI** | Google Gemini API |
| **ML** | scikit-learn, NumPy, Pandas |
| **APIs** | TMDB, RapidAPI (YouTube), SendGrid |

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL database (or SQLite for local development)

## Environment Variables

Create a `.env` file in the project root or set these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SESSION_SECRET` | Yes | Django secret key (app will not start without this) |
| `DATABASE_URL` | Yes | PostgreSQL connection string (falls back to SQLite if not set) |
| `TMDB_API_KEY` | Yes | TMDB API key for movie/TV data ([get one here](https://www.themoviedb.org/settings/api)) |
| `GEMINI_API_KEY` | No | Google Gemini API key for AI recommendations |
| `RAPIDAPI_KEY` | No | RapidAPI key for YouTube trailer search |
| `SENDGRID_API_KEY` | No | SendGrid API key for password reset emails |
| `DEFAULT_FROM_EMAIL` | No | Sender email address for password reset |
| `DEBUG` | No | Set to `True` for development (defaults to `False`) |

## Getting Started

### 1. Clone the repository

```bash
git clone <repository-url>
cd cinegraph
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Or if using `uv` (recommended):

```bash
uv sync
```

### 3. Install Node.js dependencies

```bash
npm install
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys and database URL
```

Or export them directly:

```bash
export SESSION_SECRET="your-secret-key-here"
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
export TMDB_API_KEY="your-tmdb-api-key"
export DEBUG="True"
```

### 5. Run database migrations

```bash
python manage.py migrate
```

### 6. (Optional) Seed ML training data

```bash
python manage.py seed_movielens_data
```

This imports the MovieLens small dataset (5,000 ratings from 32 users) to power the collaborative filtering engine.

### 7. Start the development servers

**Backend** (Django on port 8000):

```bash
python manage.py runserver 0.0.0.0:8000
```

**Frontend** (Vite dev server on port 5000):

```bash
npm run dev
```

The frontend proxies all `/api` requests to the Django backend automatically.

### Running on Replit

Both servers are configured as workflows and start automatically:
- **MovieFlix Server** - runs `python manage.py runserver 0.0.0.0:8000`
- **React Frontend** - runs `npm run dev`

## Project Structure

```
cinegraph/
├── movieflix/                  # Django project configuration
│   ├── settings.py            # App settings (DB, auth, security, CORS)
│   ├── urls.py                # Root URL routing
│   └── wsgi.py                # WSGI entry point
├── movies/                    # Main Django app
│   ├── models/                # Database models (user, social, ml, analytics)
│   ├── api_views/             # DRF class-based views (180+ endpoints)
│   │   ├── auth.py            # Login, register, JWT refresh, password reset
│   │   ├── tmdb.py            # TMDB proxy with base class
│   │   ├── users.py           # User profiles, watchlist, favorites
│   │   ├── reviews.py         # Reviews, comments, awards
│   │   ├── community.py       # Clubs, community lists, feeds
│   │   ├── recommendations.py # AI/ML recommendation endpoints
│   │   ├── ml.py              # ML pipeline endpoints
│   │   └── analytics.py       # User engagement & platform stats
│   ├── ml/                    # ML recommendation modules
│   │   ├── recommendation_engine.py   # Collaborative + content-based filtering
│   │   ├── contextual_bandits.py      # Thompson Sampling strategy selection
│   │   ├── diversity_engine.py        # MMR reranking + serendipity
│   │   ├── signal_aggregator.py       # Unified user signal collection
│   │   ├── feedback_service.py        # Per-user feature weight learning
│   │   └── explainability_engine.py   # Recommendation explanations
│   ├── serializers/           # DRF serializers
│   ├── api.py                 # TMDB API service helpers
│   ├── recommendations_api.py # Gemini AI recommendation logic
│   ├── ml_api.py              # ML pipeline orchestration
│   └── validation.py          # Input validation & error responses
├── client/                    # React frontend
│   ├── src/
│   │   ├── pages/             # Route pages (home, movies, tv-shows, etc.)
│   │   ├── components/        # Shared UI components
│   │   ├── hooks/             # Custom React hooks (useAuth, useWatchlist, etc.)
│   │   ├── lib/               # Utilities (API client, query config)
│   │   └── i18n/              # Internationalization (6 languages)
│   └── index.html
├── shared/                    # Shared TypeScript types
└── ml-latest-small/           # MovieLens dataset for ML engine
```

## API Overview

All endpoints are under `/api/` and use JWT Bearer token authentication.

| Group | Endpoints | Description |
|-------|-----------|-------------|
| **Auth** | `/api/auth/login`, `/api/auth/register`, `/api/auth/token/refresh` | JWT authentication |
| **Users** | `/api/users/{id}/profile`, `/api/users/{id}/watchlist` | User data & lists |
| **Movies** | `/api/movies/trending`, `/api/movies/top-rated`, `/api/movies/{id}` | TMDB movie proxy |
| **TV** | `/api/tv/popular`, `/api/tv/airing-today`, `/api/tv/{id}` | TMDB TV proxy |
| **AI** | `/api/ai/chat`, `/api/ai/chat/stream` | Gemini AI chat (SSE streaming) |
| **Recommendations** | `/api/recommendations/hybrid/{id}` | ML-powered recommendations |
| **Social** | `/api/social/lists`, `/api/social/follow/{id}` | Lists & follows |
| **Community** | `/api/community/clubs`, `/api/community/feed` | Clubs & community |
| **Reviews** | `/api/reviews/{tmdb_id}` | Movie/TV reviews |

## Running Tests

**Backend tests:**

```bash
python manage.py test movies
```

**Frontend tests:**

```bash
npm test
```

## Production Deployment

Build the frontend for production:

```bash
npm run build
```

Run with Gunicorn:

```bash
gunicorn movieflix.wsgi:application --bind 0.0.0.0:8000
```

Django will serve the built React SPA from the `dist/public/` directory in production mode.

## License

This project is for educational and personal use.
