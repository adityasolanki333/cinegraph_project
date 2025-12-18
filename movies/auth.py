import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token


@ensure_csrf_cookie
@require_GET
def csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
def register_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        password = data.get('password', '')
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        
        if len(password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        if User.objects.filter(username=email).exists():
            return JsonResponse({'error': 'Email already registered'}, status=400)
        
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'createdAt': user.date_joined.isoformat(),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Registration failed'}, status=500)


@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return JsonResponse({'error': 'Email and password are required'}, status=400)
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'firstName': user.first_name,
                    'lastName': user.last_name,
                    'createdAt': user.date_joined.isoformat(),
                }
            })
        else:
            return JsonResponse({'error': 'Invalid email or password'}, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Login failed'}, status=500)


@csrf_exempt
@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'success': True})


@ensure_csrf_cookie
@require_GET
def me_view(request):
    if request.user.is_authenticated:
        user = request.user
        return JsonResponse({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'createdAt': user.date_joined.isoformat(),
            }
        })
    else:
        return JsonResponse({'error': 'Not authenticated'}, status=401)


@ensure_csrf_cookie
@require_POST
def demo_login_view(request):
    import uuid
    import random
    import string
    
    demo_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    demo_email = f'demo_{demo_suffix}@cinesuggest.com'
    demo_password = str(uuid.uuid4())
    
    user = User.objects.create_user(
        username=demo_email,
        email=demo_email,
        password=demo_password,
        first_name='Demo',
        last_name='User'
    )
    
    login(request, user)
    
    return JsonResponse({
        'success': True,
        'user': {
            'id': str(user.id),
            'email': user.email,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'createdAt': user.date_joined.isoformat(),
        },
        'isDemo': True
    })
