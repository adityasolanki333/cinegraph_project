from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from django.core.cache import cache


class CachedJWTAuthentication(JWTAuthentication):
    """
    Drop-in replacement for JWTAuthentication that caches the User object
    for 60 seconds, eliminating a ~200-1700ms Neon DB round-trip on every
    authenticated request.
    """
    USER_CACHE_TTL = 60

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            return super().get_user(validated_token)

        cache_key = f"jwt:user:{user_id}"
        user = cache.get(cache_key)
        if user is None:
            user = super().get_user(validated_token)
            if user is not None:
                cache.set(cache_key, user, self.USER_CACHE_TTL)
        return user
