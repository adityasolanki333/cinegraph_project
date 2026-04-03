import hashlib
import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from django.middleware.csrf import get_token
from .validation import error_response


def api_auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return error_response('Authentication required', 'AUTH_REQUIRED', 401)
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(user_id_param='user_id'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return error_response('Authentication required', 'AUTH_REQUIRED', 401)
            
            user_id = kwargs.get(user_id_param)
            if user_id is not None and str(request.user.id) != str(user_id):
                return error_response('Not authorized to access this resource', 'FORBIDDEN', 403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _parse_rate(rate_string):
    num, period = rate_string.split('/')
    num = int(num)
    period_map = {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}
    seconds = period_map.get(period, 60)
    return num, seconds


def rate_limit(rate=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.conf import settings

            if request.user.is_authenticated:
                identity = f'rl_user_{request.user.id}'
                default_rate = getattr(settings, 'REST_FRAMEWORK', {}).get(
                    'DEFAULT_THROTTLE_RATES', {}
                ).get('user', '100/minute')
            else:
                ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
                identity = f'rl_anon_{hashlib.md5(ip.encode()).hexdigest()}'
                default_rate = getattr(settings, 'REST_FRAMEWORK', {}).get(
                    'DEFAULT_THROTTLE_RATES', {}
                ).get('anon', '20/minute')

            chosen_rate = rate or default_rate
            max_requests, window = _parse_rate(chosen_rate)

            cache_key = f'{identity}_{view_func.__name__}'
            now = time.time()
            history = cache.get(cache_key, [])
            history = [ts for ts in history if ts > now - window]

            if len(history) >= max_requests:
                retry_after = int(window - (now - history[0])) + 1
                return JsonResponse(
                    {
                        'error': 'Rate limit exceeded. Please try again later.',
                        'code': 'RATE_LIMITED',
                        'retryAfter': retry_after,
                    },
                    status=429,
                )

            history.append(now)
            cache.set(cache_key, history, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
