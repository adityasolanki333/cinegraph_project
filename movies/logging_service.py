import logging
from .models import SearchInteraction
from django.db.models import F

logger = logging.getLogger(__name__)

def log_search_interaction(user, query, tmdb_id, media_type, action='click'):
    """
    Log a user interaction with search results or recommendations.
    
    Args:
        user: User object (can be None)
        query: Search query string (or source identifier like 'recommendation')
        tmdb_id: TMDB ID of the item
        media_type: 'movie' or 'tv'
        action: 'click', 'watch', etc.
    """
    try:
        if not user or not user.is_authenticated:
            # We could log anonymous interactions if needed, but model expects User or null
            # Model definition: user = models.ForeignKey(..., null=True)
            pass

        interaction = SearchInteraction.objects.create(
            user=user if (user and user.is_authenticated) else None,
            query=query.lower().strip() if query else '',
            tmdb_id=tmdb_id,
            media_type=media_type,
            action=action
        )
        logger.info(f"Logged interaction: {user} - {query} -> {tmdb_id} ({action})")
        return interaction
    except Exception as e:
        logger.error(f"Failed to log interaction: {e}")
        return None
