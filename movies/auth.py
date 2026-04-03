import json
from django.http import JsonResponse
from .validation import error_response
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
            return error_response('Email and password are required', 'VALIDATION_ERROR', 400)
        
        if len(password) < 6:
            return error_response('Password must be at least 6 characters', 'VALIDATION_ERROR', 400)
        
        if User.objects.filter(email=email).exists():
            return error_response('Email already registered', 'VALIDATION_ERROR', 400)
        
        if User.objects.filter(username=email).exists():
            return error_response('Email already registered', 'VALIDATION_ERROR', 400)
        
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
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        return error_response('Registration failed', 'INTERNAL_ERROR', 500)


@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return error_response('Email and password are required', 'VALIDATION_ERROR', 400)
        
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
            return error_response('Invalid email or password', 'AUTH_REQUIRED', 401)
            
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        return error_response('Login failed', 'INTERNAL_ERROR', 500)
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
        return error_response('Not authenticated', 'AUTH_REQUIRED', 401)
@require_POST
def forgot_password_view(request):
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return error_response('Email is required', 'VALIDATION_ERROR', 400)
            
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
        
        return JsonResponse({
            'success': True,
            'message': 'If an account exists with this email, you will receive a password reset link.'
        })
        
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)
@require_POST
def reset_password_view(request):
    try:
        data = json.loads(request.body)
        token = data.get('token', '')
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return error_response('Token and new password are required', 'VALIDATION_ERROR', 400)
            
        if len(new_password) < 6:
            return error_response('Password must be at least 6 characters', 'VALIDATION_ERROR', 400)
            
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
            return error_response('Reset link has expired', 'VALIDATION_ERROR', 400)
        except BadSignature:
            return error_response('Invalid reset link', 'VALIDATION_ERROR', 400)
        except User.DoesNotExist:
            return error_response('User not found', 'NOT_FOUND', 404)
            
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 'VALIDATION_ERROR', 400)
    except Exception as e:
        return error_response(str(e), 'INTERNAL_ERROR', 500)
