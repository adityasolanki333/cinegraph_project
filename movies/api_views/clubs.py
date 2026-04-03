import logging
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import serializers
from django.shortcuts import get_object_or_404
from django.db.models import Q
from movies.models import Club, ClubMember, ClubThread, ClubPost

logger = logging.getLogger(__name__)


class CreateClubSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=2000, allow_blank=True, default='')
    cover_image_url = serializers.URLField(max_length=500, allow_blank=True, default='')


class CreateThreadSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    content = serializers.CharField(max_length=10000)


class CreatePostSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=10000)


class ClubsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '')
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
                'id': club.id, 'title': club.title, 'description': club.description,
                'cover_image_url': club.cover_image_url, 'member_count': club.member_count,
                'is_member': is_member, 'created_at': club.created_at.isoformat()
            })
        return Response({'clubs': data})

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}, status=401)
        serializer = CreateClubSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        try:
            club = Club.objects.create(
                title=data['title'], description=data.get('description', ''),
                owner=request.user, cover_image_url=data.get('cover_image_url', '')
            )
            ClubMember.objects.create(club=club, user=request.user, role='admin')
            return Response({
                'id': club.id, 'title': club.title, 'message': 'Club created successfully'
            }, status=201)
        except Exception as e:
            logger.error('Error creating club: %s', e)
            return Response({'error': 'An internal error occurred', 'code': 'INTERNAL_ERROR'}, status=500)


class ClubDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        club = get_object_or_404(Club, id=self.kwargs['club_id'])
        is_member = False
        user_role = None
        if request.user.is_authenticated:
            try:
                membership = ClubMember.objects.get(club=club, user=request.user)
                is_member = True
                user_role = membership.role
            except ClubMember.DoesNotExist:
                pass
        threads = club.threads.all().order_by('-pinned', '-updated_at')[:5]
        return Response({
            'id': club.id, 'title': club.title, 'description': club.description,
            'cover_image_url': club.cover_image_url, 'member_count': club.member_count,
            'is_member': is_member, 'role': user_role,
            'owner': {'id': club.owner.id, 'username': club.owner.username},
            'recent_threads': [{
                'id': t.id, 'title': t.title, 'view_count': t.view_count,
                'post_count': t.posts.count(),
                'author': {'id': t.author.id, 'username': t.author.username},
                'updated_at': t.updated_at.isoformat()
            } for t in threads],
            'created_at': club.created_at.isoformat()
        })


class JoinClubView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, club_id):
        club = get_object_or_404(Club, id=club_id)
        try:
            if ClubMember.objects.filter(club=club, user=request.user).exists():
                if club.owner == request.user:
                    return Response({'error': 'Owner cannot leave the club', 'code': 'VALIDATION_ERROR'}, status=400)
                ClubMember.objects.filter(club=club, user=request.user).delete()
                club.member_count = max(0, club.member_count - 1)
                club.save()
                return Response({'message': 'Left club successfully', 'joined': False})
            else:
                ClubMember.objects.create(club=club, user=request.user)
                club.member_count += 1
                club.save()
                return Response({'message': 'Joined club successfully', 'joined': True})
        except Exception as e:
            logger.error('Error joining/leaving club: %s', e)
            return Response({'error': 'An internal error occurred', 'code': 'INTERNAL_ERROR'}, status=500)


class ClubThreadsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, club_id):
        club = get_object_or_404(Club, id=club_id)
        threads = club.threads.all().order_by('-pinned', '-updated_at')
        return Response({
            'threads': [{
                'id': t.id, 'title': t.title,
                'author': {
                    'id': t.author.id, 'username': t.author.username,
                    'avatar': t.author.profile.profile_image_url if hasattr(t.author, 'profile') else None
                },
                'view_count': t.view_count, 'post_count': t.posts.count(),
                'pinned': t.pinned,
                'created_at': t.created_at.isoformat(), 'updated_at': t.updated_at.isoformat()
            } for t in threads]
        })

    def post(self, request, club_id):
        club = get_object_or_404(Club, id=club_id)
        if not ClubMember.objects.filter(club=club, user=request.user).exists():
            return Response({'error': 'Must be a member to post threads', 'code': 'FORBIDDEN'}, status=403)
        serializer = CreateThreadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        thread = ClubThread.objects.create(
            club=club, author=request.user, title=data['title'], content=data['content']
        )
        return Response({
            'id': thread.id, 'club_id': club.id, 'title': thread.title,
            'message': 'Thread created successfully'
        }, status=201)


class ThreadDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        thread = get_object_or_404(ClubThread, id=self.kwargs['thread_id'])
        thread.view_count += 1
        thread.save()
        posts = thread.posts.all().order_by('created_at')
        return Response({
            'id': thread.id,
            'club': {'id': thread.club.id, 'title': thread.club.title},
            'title': thread.title, 'content': thread.content,
            'author': {
                'id': thread.author.id, 'username': thread.author.username,
                'avatar': thread.author.profile.profile_image_url if hasattr(thread.author, 'profile') else None
            },
            'view_count': thread.view_count, 'pinned': thread.pinned,
            'posts': [{
                'id': p.id, 'content': p.content,
                'author': {
                    'id': p.author.id, 'username': p.author.username,
                    'avatar': p.author.profile.profile_image_url if hasattr(p.author, 'profile') else None
                },
                'created_at': p.created_at.isoformat()
            } for p in posts],
            'created_at': thread.created_at.isoformat()
        })


class CreatePostView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CreatePostSerializer

    def create(self, request, *args, **kwargs):
        thread = get_object_or_404(ClubThread, id=self.kwargs['thread_id'])
        if not ClubMember.objects.filter(club=thread.club, user=request.user).exists():
            return Response({'error': 'Must be a member to reply', 'code': 'FORBIDDEN'}, status=403)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        post = ClubPost.objects.create(
            thread=thread, author=request.user, content=serializer.validated_data['content']
        )
        thread.save()
        return Response({
            'id': post.id, 'message': 'Reply posted successfully',
            'post': {
                'id': post.id, 'content': post.content,
                'author': {'id': post.author.id, 'username': post.author.username},
                'created_at': post.created_at.isoformat()
            }
        }, status=201)
