import logging
from rest_framework.generics import ListAPIView, RetrieveAPIView, CreateAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from movies.models import UserList, ListItem, ListFollow, ListCollaborator, Notification
from movies.serializers.social import (
    UserListSerializer, ListItemSerializer, CreateListSerializer,
    UpdateListSerializer, CreateListItemSerializer,
)
from movies.pagination import StandardPagePagination

logger = logging.getLogger(__name__)


def _get_user_or_404(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


class UserListsView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserListSerializer

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        lists = UserList.objects.filter(user_id=user_id).select_related('user', 'user__profile')
        if not self.request.user.is_authenticated or str(self.request.user.id) != str(user_id):
            lists = lists.filter(is_public=True)
        return lists

    def list(self, request, *args, **kwargs):
        user = _get_user_or_404(self.kwargs['user_id'])
        if not user:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'lists': serializer.data})


class PublicListsView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserListSerializer
    pagination_class = StandardPagePagination

    def get_queryset(self):
        q = self.request.query_params.get('q', '').strip()
        sort = self.request.query_params.get('sort', 'popular')
        lists = UserList.objects.filter(is_public=True).select_related('user', 'user__profile')
        if q:
            lists = lists.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if sort == 'newest':
            lists = lists.order_by('-created_at')
        elif sort == 'most_items':
            lists = lists.annotate(item_cnt=Count('items')).order_by('-item_cnt')
        else:
            lists = lists.order_by('-follower_count', '-created_at')
        return lists

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            resp = self.get_paginated_response(serializer.data)
            resp.data = {
                'lists': serializer.data,
                'total': self.paginator.page.paginator.count,
                'hasMore': self.paginator.page.has_next(),
            }
            return resp
        serializer = self.get_serializer(queryset, many=True)
        return Response({'lists': serializer.data, 'total': len(serializer.data), 'hasMore': False})


class CreateListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id=None):
        uid = user_id or request.user.id
        if str(request.user.id) != str(uid):
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        serializer = CreateListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        lst = UserList.objects.create(
            user=request.user, title=data['title'],
            description=data.get('description', ''),
            is_public=data.get('isPublic', True)
        )
        return Response({
            'success': True,
            'list': UserListSerializer(lst).data,
        })


class ListDetailView(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserListSerializer
    lookup_url_kwarg = 'list_id'
    queryset = UserList.objects.all()

    def retrieve(self, request, *args, **kwargs):
        try:
            lst = UserList.objects.select_related('user', 'user__profile').get(id=self.kwargs['list_id'])
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)
        if not lst.is_public:
            if not request.user.is_authenticated or request.user.id != lst.user.id:
                return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        items = ListItem.objects.filter(list=lst)
        list_data = UserListSerializer(lst).data
        list_data['items'] = ListItemSerializer(items, many=True).data
        return Response({'list': list_data})


class UpdateListView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id, user=request.user)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found or not authorized', 'code': 'NOT_FOUND'}, status=404)
        serializer = UpdateListSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        if 'title' in data:
            lst.title = data['title']
        if 'description' in data:
            lst.description = data['description']
        if 'isPublic' in data:
            lst.is_public = data['isPublic']
        lst.save()
        return Response({
            'success': True,
            'list': {'id': lst.id, 'title': lst.title, 'description': lst.description, 'isPublic': lst.is_public}
        })


class DeleteListView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        deleted, _ = UserList.objects.filter(id=self.kwargs['list_id'], user=request.user).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class AddListItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id, user=request.user)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found or not authorized', 'code': 'NOT_FOUND'}, status=404)
        serializer = CreateListItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'code': 'VALIDATION_ERROR'}, status=400)
        data = serializer.validated_data
        max_pos = ListItem.objects.filter(list=lst).count()
        item, created = ListItem.objects.get_or_create(
            list=lst, tmdb_id=data['tmdbId'], media_type=data.get('mediaType', 'movie'),
            defaults={'title': data.get('title', ''), 'poster_path': data.get('posterPath', ''),
                      'note': data.get('note', ''), 'position': max_pos}
        )
        return Response({
            'success': True, 'created': created,
            'item': ListItemSerializer(item).data,
        })


class RemoveListItemView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        list_id = self.kwargs['list_id']
        item_id = self.kwargs['item_id']
        try:
            lst = UserList.objects.get(id=list_id, user=request.user)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found or not authorized', 'code': 'NOT_FOUND'}, status=404)
        deleted, _ = ListItem.objects.filter(list=lst, id=item_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class ListsContainingView(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserListSerializer

    def list(self, request, *args, **kwargs):
        tmdb_id = self.kwargs['tmdb_id']
        media_type = self.kwargs['media_type']
        cache_key = f"lists:containing:{tmdb_id}:{media_type}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        items = ListItem.objects.filter(
            tmdb_id=tmdb_id, media_type=media_type, list__is_public=True
        ).select_related('list', 'list__user', 'list__user__profile')[:10]
        lists = [item.list for item in items]
        serializer = self.get_serializer(lists, many=True)
        payload = {'lists': serializer.data}
        cache.set(cache_key, payload, 300)
        return Response(payload)


class ListFollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, list_id):
        try:
            user_list = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        if not user_list.is_public and user_list.user != request.user:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        if user_list.user == request.user:
            return Response({'error': 'Cannot follow your own list', 'code': 'VALIDATION_ERROR'}, status=400)

        follow, created = ListFollow.objects.get_or_create(user=request.user, list=user_list)

        if created:
            actual_count = ListFollow.objects.filter(list=user_list).count()
            user_list.follower_count = actual_count
            user_list.save()
            Notification.objects.create(
                user=user_list.user, notification_type='list_follow',
                message=f'{request.user.first_name or request.user.email} started following your list "{user_list.title}"',
                related_user_id=request.user.id
            )

        return Response({'success': True, 'created': created, 'followerCount': user_list.follower_count})


class ListUnfollowView(APIView):
    permission_classes = [IsAuthenticated]

    def _do_unfollow(self, request, list_id):
        try:
            user_list = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        deleted, _ = ListFollow.objects.filter(user=request.user, list=user_list).delete()

        if deleted:
            actual_count = ListFollow.objects.filter(list=user_list).count()
            user_list.follower_count = actual_count
            user_list.save()

        return Response({'success': True, 'deleted': deleted > 0, 'followerCount': user_list.follower_count})

    def post(self, request, list_id):
        return self._do_unfollow(request, list_id)

    def delete(self, request, list_id):
        return self._do_unfollow(request, list_id)


class ListFollowersView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, list_id):
        try:
            user_list = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        followers = ListFollow.objects.filter(list=user_list).select_related('user')
        return Response({
            'followers': [{
                'id': str(f.user.id),
                'email': f.user.email,
                'firstName': f.user.first_name,
                'lastName': f.user.last_name,
                'followedAt': f.created_at.isoformat(),
            } for f in followers]
        })


class IsFollowingListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, list_id):
        if not request.user.is_authenticated:
            return Response({'isFollowing': False})
        exists = ListFollow.objects.filter(user=request.user, list_id=list_id).exists()
        return Response({'isFollowing': exists})


class ListCollaboratorsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        collaborators = ListCollaborator.objects.filter(list=lst).select_related('user')
        return Response({
            'collaborators': [{
                'id': c.id,
                'userId': str(c.user.id),
                'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
                'email': c.user.email,
                'permission': c.permission,
                'accepted': c.accepted,
                'invitedAt': c.invited_at.isoformat(),
            } for c in collaborators]
        })


class InviteCollaboratorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id, user=request.user)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found or not authorized', 'code': 'NOT_FOUND'}, status=404)

        user_id = request.data.get('userId')
        permission = request.data.get('permission', 'view')

        if not user_id:
            return Response({'error': 'userId is required', 'code': 'VALIDATION_ERROR'}, status=400)

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found', 'code': 'NOT_FOUND'}, status=404)

        if target_user == request.user:
            return Response({'error': 'Cannot invite yourself', 'code': 'VALIDATION_ERROR'}, status=400)

        collaborator, created = ListCollaborator.objects.get_or_create(
            list=lst, user=target_user,
            defaults={'permission': permission}
        )

        if not created:
            collaborator.permission = permission
            collaborator.save()

        Notification.objects.create(
            user=target_user, notification_type='list_follow',
            message=f'{request.user.first_name or request.user.email} invited you to collaborate on "{lst.title}"',
            related_user_id=request.user.id
        )

        return Response({
            'success': True, 'created': created,
            'collaborator': {
                'id': collaborator.id,
                'userId': str(collaborator.user.id),
                'permission': collaborator.permission,
                'accepted': collaborator.accepted,
            }
        })


class RemoveCollaboratorView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, list_id, collaborator_id):
        try:
            lst = UserList.objects.get(id=list_id, user=request.user)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found or not authorized', 'code': 'NOT_FOUND'}, status=404)

        deleted, _ = ListCollaborator.objects.filter(list=lst, id=collaborator_id).delete()
        return Response({'success': True, 'deleted': deleted > 0})


class ManageCommunityListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, list_id):
        try:
            lst = UserList.objects.select_related('user').get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        if not lst.is_public:
            if not request.user.is_authenticated or request.user.id != lst.user.id:
                return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        items = ListItem.objects.filter(list=lst)
        return Response({
            'list': {
                'id': lst.id, 'title': lst.title, 'description': lst.description,
                'isPublic': lst.is_public, 'followerCount': lst.follower_count,
                'createdAt': lst.created_at.isoformat(),
                'updatedAt': lst.updated_at.isoformat(),
                'user': {'id': str(lst.user.id), 'firstName': lst.user.first_name, 'lastName': lst.user.last_name},
                'items': [{
                    'id': item.id, 'tmdbId': item.tmdb_id, 'mediaType': item.media_type,
                    'title': item.title, 'posterPath': item.poster_path,
                    'note': item.note, 'position': item.position,
                    'addedAt': item.added_at.isoformat(),
                } for item in items]
            }
        })

    def put(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        if not request.user.is_authenticated or lst.user != request.user:
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        data = request.data
        if 'title' in data:
            lst.title = data['title']
        if 'description' in data:
            lst.description = data['description']
        if 'isPublic' in data:
            lst.is_public = data['isPublic']
        lst.save()
        return Response({
            'success': True,
            'list': {'id': lst.id, 'title': lst.title, 'description': lst.description, 'isPublic': lst.is_public}
        })

    def delete(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        if not request.user.is_authenticated or lst.user != request.user:
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)

        lst.delete()
        return Response({'success': True})


class ListSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response([])

        lists = (
            UserList.objects.filter(is_public=True)
            .filter(Q(title__icontains=q) | Q(description__icontains=q))
            .select_related('user', 'user__profile')
            .order_by('-follower_count', '-created_at')[:20]
        )

        serializer = UserListSerializer(lists, many=True)
        return Response(serializer.data)


class SimilarListsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, list_id):
        try:
            lst = UserList.objects.get(id=list_id, is_public=True)
        except UserList.DoesNotExist:
            return Response({'error': 'List not found', 'code': 'NOT_FOUND'}, status=404)

        source_items = list(ListItem.objects.filter(list=lst).values('tmdb_id', 'media_type', 'title', 'poster_path'))
        item_tmdb_ids = set(si['tmdb_id'] for si in source_items)
        if not item_tmdb_ids:
            return Response([])

        similar_list_ids = (
            ListItem.objects.filter(tmdb_id__in=item_tmdb_ids, list__is_public=True)
            .exclude(list=lst)
            .values_list('list_id', flat=True)
        )
        similar_lists = (
            UserList.objects.filter(id__in=similar_list_ids, is_public=True)
            .select_related('user', 'user__profile')
            .annotate(overlap=Count('items', filter=Q(items__tmdb_id__in=item_tmdb_ids)))
            .order_by('-overlap', '-follower_count')[:6]
        )

        source_item_map = {si['tmdb_id']: si for si in source_items}

        result = []
        for sl in similar_lists:
            sl_items = list(ListItem.objects.filter(list=sl))
            sl_tmdb_ids = set(item.tmdb_id for item in sl_items)
            shared_tmdb_ids = item_tmdb_ids & sl_tmdb_ids
            shared_count = len(shared_tmdb_ids)
            total_unique = len(item_tmdb_ids | sl_tmdb_ids)
            overlap_pct = round((shared_count / total_unique * 100) if total_unique else 0)

            shared_items = []
            for tmdb_id in list(shared_tmdb_ids)[:5]:
                si = source_item_map.get(tmdb_id, {})
                matching = next((i for i in sl_items if i.tmdb_id == tmdb_id), None)
                shared_items.append({
                    'id': str(matching.id) if matching else str(tmdb_id),
                    'tmdbId': tmdb_id,
                    'mediaType': si.get('media_type', matching.media_type if matching else 'movie'),
                    'title': si.get('title', matching.title if matching else ''),
                    'posterPath': si.get('poster_path', matching.poster_path if matching else None),
                })

            profile_url = None
            if hasattr(sl.user, 'profile'):
                profile_url = sl.user.profile.profile_image_url

            preview_items = sl_items[:4]
            result.append({
                'id': sl.id,
                'userId': str(sl.user.id),
                'title': sl.title,
                'description': sl.description[:100] if sl.description else '',
                'isPublic': sl.is_public,
                'followerCount': sl.follower_count,
                'itemCount': len(sl_items),
                'createdAt': sl.created_at.isoformat(),
                'sharedItemCount': shared_count,
                'overlapPercentage': overlap_pct,
                'sharedItems': shared_items,
                'user': {
                    'id': str(sl.user.id),
                    'firstName': sl.user.first_name or sl.user.username,
                    'lastName': sl.user.last_name,
                    'profileImageUrl': profile_url,
                },
                'items': [{
                    'id': str(item.id),
                    'posterPath': item.poster_path,
                    'title': item.title,
                } for item in preview_items],
            })

        return Response(result)


class RecommendedListsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        lists = UserList.objects.filter(is_public=True).select_related('user', 'user__profile').order_by('-follower_count')[:10]
        result = []
        for lst in lists:
            profile_url = None
            if hasattr(lst.user, 'profile'):
                profile_url = lst.user.profile.profile_image_url
            result.append({
                'id': lst.id,
                'title': lst.title,
                'description': lst.description[:100] if lst.description else '',
                'isPublic': lst.is_public,
                'followerCount': lst.follower_count,
                'itemCount': lst.items.count(),
                'createdAt': lst.created_at.isoformat(),
                'user': {
                    'id': str(lst.user.id),
                    'firstName': lst.user.first_name or lst.user.username,
                    'lastName': lst.user.last_name,
                    'profileImageUrl': profile_url,
                },
            })
        return Response(result)
