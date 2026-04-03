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
                'username': user.username,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'createdAt': user.date_joined.isoformat(),
            }
        })
    else:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
@require_POST
def forgot_password_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)
            
        user = User.objects.filter(email=email).first()
        if not user:
            # Don't reveal user existence, just pretend success
            # But for this demo we'll just return success
            return JsonResponse({
                'success': True, 
                'message': 'If an account exists with this email, you will receive a password reset link.'
            })
            
        from django.core.signing import TimestampSigner
        signer = TimestampSigner()
        token = signer.sign(str(user.id))
        
        # In a real app, send email here.
        # For this demo, we return the token/link in the response so the user can test user flow
        return JsonResponse({
            'success': True,
            'message': 'Password reset link sent (check console/response for demo)',
            'demo_reset_token': token,
            'demo_reset_link': f'/reset-password?token={token}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@require_POST
def reset_password_view(request):
    try:
        data = json.loads(request.body)
        token = data.get('token', '')
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return JsonResponse({'error': 'Token and new password are required'}, status=400)
            
        if len(new_password) < 6:
            return JsonResponse({'error': 'Password must be at least 6 characters'}, status=400)
            
        from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
        signer = TimestampSigner()
        
        try:
            # Token valid for 1 hour (3600 seconds)
            user_id = signer.unsign(token, max_age=3600)
            user = User.objects.get(id=user_id)
            
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({'success': True, 'message': 'Password successfully reset'})
            
        except SignatureExpired:
            return JsonResponse({'error': 'Reset link has expired'}, status=400)
        except BadSignature:
            return JsonResponse({'error': 'Invalid reset link'}, status=400)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
