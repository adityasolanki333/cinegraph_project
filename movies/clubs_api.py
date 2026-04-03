from .decorators import api_auth_required
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Count, Q
from .models import Club, ClubMember, ClubThread, ClubPost


@require_http_methods(["GET", "POST"])
@csrf_exempt
def clubs_list(request):
    """
    GET: List all clubs (with optional search) — public
    POST: Create a new club — requires auth
    """
    if request.method == "POST" and not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)

    if request.method == "GET":
        query = request.GET.get('q', '')
        clubs = Club.objects.filter(is_public=True)

        if query:
            clubs = clubs.filter(Q(title__icontains=query) | Q(description__icontains=query))

        clubs = clubs.order_by('-member_count')

        data = []
        for club in clubs:
            is_member = False
            if request.user.is_authenticated:
                is_member = ClubMember.objects.filter(club=club, user=request.user).exists()

            data.append({
                'id': club.id,
                'title': club.title,
                'description': club.description,
                'cover_image_url': club.cover_image_url,
                'member_count': club.member_count,
                'is_member': is_member,
                'created_at': club.created_at.isoformat()
            })

        return JsonResponse({'clubs': data})

    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            title = body.get('title')
            description = body.get('description', '')
            cover_image_url = body.get('cover_image_url', '')

            if not title:
                return JsonResponse({'error': 'Title is required'}, status=400)

            club = Club.objects.create(
                title=title,
                description=description,
                owner=request.user,
                cover_image_url=cover_image_url
            )

            # Add owner as admin member
            ClubMember.objects.create(
                club=club,
                user=request.user,
                role='admin'
            )

            return JsonResponse({
                'id': club.id,
                'title': club.title,
                'message': 'Club created successfully'
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@require_http_methods(["GET"])
def club_details(request, club_id):
    """Get details for a specific club"""
    club = get_object_or_404(Club, id=club_id)

    is_member = False
    user_role = None
    if request.user.is_authenticated:
        try:
            membership = ClubMember.objects.get(club=club, user=request.user)
            is_member = True
            user_role = membership.role
        except ClubMember.DoesNotExist:
            pass

    # Get recent threads
    threads = club.threads.all().order_by('-pinned', '-updated_at')[:5]
    threads_data = [{
        'id': t.id,
        'title': t.title,
        'view_count': t.view_count,
        'post_count': t.posts.count(),
        'author': {
            'id': t.author.id,
            'username': t.author.username
        },
        'updated_at': t.updated_at.isoformat()
    } for t in threads]

    return JsonResponse({
        'id': club.id,
        'title': club.title,
        'description': club.description,
        'cover_image_url': club.cover_image_url,
        'member_count': club.member_count,
        'is_member': is_member,
        'role': user_role,
        'owner': {
            'id': club.owner.id,
            'username': club.owner.username
        },
        'recent_threads': threads_data,
        'created_at': club.created_at.isoformat()
    })


@require_http_methods(["POST"])
@api_auth_required
def join_club(request, club_id):
    """Join or leave a club"""
    club = get_object_or_404(Club, id=club_id)

    try:
        # Check if already a member
        if ClubMember.objects.filter(club=club, user=request.user).exists():
            # Leave club (unless owner)
            if club.owner == request.user:
                return JsonResponse({'error': 'Owner cannot leave the club'}, status=400)

            ClubMember.objects.filter(club=club, user=request.user).delete()
            club.member_count = max(0, club.member_count - 1)
            club.save()
            return JsonResponse({'message': 'Left club successfully', 'joined': False})
        else:
            # Join club
            ClubMember.objects.create(club=club, user=request.user)
            club.member_count += 1
            club.save()
            return JsonResponse({'message': 'Joined club successfully', 'joined': True})

    except Exception as e:
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@require_http_methods(["GET", "POST"])
@api_auth_required
def club_threads(request, club_id):
    """
    GET: List all threads for a club
    POST: Create a new thread
    """
    club = get_object_or_404(Club, id=club_id)

    if request.method == "GET":
        threads = club.threads.all().order_by('-pinned', '-updated_at')

        data = []
        for thread in threads:
            data.append({
                'id': thread.id,
                'title': thread.title,
                'author': {
                    'id': thread.author.id,
                    'username': thread.author.username,
                    'avatar': thread.author.profile.profile_image_url if hasattr(thread.author, 'profile') else None
                },
                'view_count': thread.view_count,
                'post_count': thread.posts.count(),
                'pinned': thread.pinned,
                'created_at': thread.created_at.isoformat(),
                'updated_at': thread.updated_at.isoformat()
            })

        return JsonResponse({'threads': data})

    elif request.method == "POST":
        # Verify membership
        if not ClubMember.objects.filter(club=club, user=request.user).exists():
            return JsonResponse({'error': 'Must be a member to post threads'}, status=403)

        try:
            body = json.loads(request.body)
            title = body.get('title')
            content = body.get('content')

            if not title or not content:
                return JsonResponse({'error': 'Title and content are required'}, status=400)

            thread = ClubThread.objects.create(
                club=club,
                author=request.user,
                title=title,
                content=content
            )

            return JsonResponse({
                'id': thread.id,
                'club_id': club.id,
                'title': thread.title,
                'message': 'Thread created successfully'
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_http_methods(["GET"])
def thread_details(request, thread_id):
    """Get thread details and posts"""
    thread = get_object_or_404(ClubThread, id=thread_id)

    # Increment view count
    thread.view_count += 1
    thread.save()

    posts = thread.posts.all().order_by('created_at')

    posts_data = [{
        'id': post.id,
        'content': post.content,
        'author': {
            'id': post.author.id,
            'username': post.author.username,
            'avatar': post.author.profile.profile_image_url if hasattr(post.author, 'profile') else None
        },
        'created_at': post.created_at.isoformat()
    } for post in posts]

    return JsonResponse({
        'id': thread.id,
        'club': {
            'id': thread.club.id,
            'title': thread.club.title
        },
        'title': thread.title,
        'content': thread.content,
        'author': {
            'id': thread.author.id,
            'username': thread.author.username,
            'avatar': thread.author.profile.profile_image_url if hasattr(thread.author, 'profile') else None
        },
        'view_count': thread.view_count,
        'pinned': thread.pinned,
        'posts': posts_data,
        'created_at': thread.created_at.isoformat()
    })


@require_http_methods(["POST"])
@api_auth_required
def create_post(request, thread_id):
    """Reply to a thread"""
    thread = get_object_or_404(ClubThread, id=thread_id)

    # Verify membership in parent club
    if not ClubMember.objects.filter(club=thread.club, user=request.user).exists():
        return JsonResponse({'error': 'Must be a member to reply'}, status=403)

    try:
        body = json.loads(request.body)
        content = body.get('content')

        if not content:
            return JsonResponse({'error': 'Content is required'}, status=400)

        post = ClubPost.objects.create(
            thread=thread,
            author=request.user,
            content=content
        )

        # Update thread's updated_at timestamp
        thread.save()

        return JsonResponse({
            'id': post.id,
            'message': 'Reply posted successfully',
            'post': {
                'id': post.id,
                'content': post.content,
                'author': {
                    'id': post.author.id,
                    'username': post.author.username
                },
                'created_at': post.created_at.isoformat()
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
