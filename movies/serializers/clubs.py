from rest_framework import serializers
from movies.models import Club, ClubMember, ClubThread, ClubPost


class ClubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Club
        fields = ['id', 'title', 'description', 'cover_image_url', 'is_public', 'member_count', 'created_at']


class ClubMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubMember
        fields = ['id', 'club', 'user', 'role', 'joined_at']


class ClubThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubThread
        fields = ['id', 'club', 'author', 'title', 'content', 'view_count', 'pinned', 'created_at', 'updated_at']


class ClubPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClubPost
        fields = ['id', 'thread', 'author', 'content', 'created_at']
