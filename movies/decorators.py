from functools import wraps
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


def csrf_exempt_for_session_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if hasattr(request, '_dont_enforce_csrf_checks'):
            request._dont_enforce_csrf_checks = True
        return view_func(request, *args, **kwargs)
    return wrapper
