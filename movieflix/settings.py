import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
from pathlib import Path
env_path = BASE_DIR / '.env'
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

_secret = os.environ.get('SESSION_SECRET')
if not _secret:
    raise ValueError('SESSION_SECRET environment variable must be set')
SECRET_KEY = _secret

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.replit.dev',
    '.repl.co',
    '.replit.app',
    '*',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'movies',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'movieflix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'movieflix.wsgi.application'

_db_url = os.environ.get('DATABASE_URL')
if _db_url:
    _db_config = dj_database_url.parse(_db_url, conn_max_age=600)
    # Ensure SSL for Neon (and other managed Postgres providers)
    if 'OPTIONS' not in _db_config:
        _db_config['OPTIONS'] = {}
    if 'neon.tech' in _db_url or 'sslmode=require' in _db_url:
        _db_config['OPTIONS']['sslmode'] = 'require'
    DATABASES = {'default': _db_config}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    d for d in [
        BASE_DIR / 'dist' / 'public',
    ] if d.exists()
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Serve React build in production
FRONTEND_BUILD_DIR = BASE_DIR / 'dist' / 'public'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'https://*.replit.dev',
    'https://*.repl.co',
    'https://*.replit.app',
] + ([f'https://{_replit_domain}'] if _replit_domain else [])
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = 'Lax'


# CORS: restrict to known origins.
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://.*\.replit\.dev$',
    r'^https://.*\.repl\.co$',
    r'^https://.*\.replit\.app$',
]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '100/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'movies.pagination.StandardPagePagination',
    'PAGE_SIZE': 20,
}

TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY', '')
RAPIDAPI_KEY = os.environ.get('RAPIDAPI_KEY', '')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {name} {module}.{funcName}:{lineno} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'movies': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'movies.ml': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Cache Settings - env-gated backend selection
# Set CACHE_BACKEND=db to use database-backed cache, defaults to file-based
_cache_backend = os.environ.get('CACHE_BACKEND', 'file')
if _cache_backend == 'db':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache_table',
            'TIMEOUT': 86400,
            'OPTIONS': {
                'MAX_ENTRIES': 5000,
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'cinegraph-cache',
            'TIMEOUT': 86400,
        }
    }

# Removed production-only secure settings (SSL/HSTS) as the project is local-only now.

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = f'CineGraph <{os.environ.get("EMAIL_HOST_USER", "")}>'

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}
