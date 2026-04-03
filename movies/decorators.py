from functools import wraps
from django.http import JsonResponse
from django.middleware.csrf import get_token


def api_auth_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(user_id_param='user_id'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            user_id = kwargs.get(user_id_param)
            if user_id is not None and str(request.user.id) != str(user_id):
                return JsonResponse({'error': 'Not authorized to access this resource'}, status=403)
            
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
    
def mock_demo_user_auth(view_func):
    """
    Decorator that injects the demo_user into the request if the target URL 
    parameter user_id is 'demo_user'. This avoids hundreds of redundant code lines.
    """
    @wraps(view_func)
    def _wrapped_view(request, user_id=None, *args, **kwargs):
        if str(user_id) == 'demo_user' or request.headers.get('x-user-id') == 'demo_user':
            from .users_api import get_or_create_demo_user
            demo_user = get_or_create_demo_user()
            request.user = demo_user
            
            # If user_id was passed in args as a positional or keyword, we should replace it with the int id
            if 'user_id' in kwargs and kwargs['user_id'] == 'demo_user':
                kwargs['user_id'] = demo_user.id
            if user_id == 'demo_user':
                return view_func(request, demo_user.id, *args, **kwargs)
                
        return view_func(request, user_id, *args, **kwargs)
    return _wrapped_view
