from django.urls import path
from . import api
from . import auth
from . import users_api
from . import social_api
from . import recommendations_api
from . import external_api
from . import analytics_api
from . import ml_api
from . import clubs_api

urlpatterns = [
    # Auth endpoints
    path('auth/csrf', auth.csrf_token_view, name='api_csrf'),
    path('auth/register', auth.register_view, name='api_register'),
    path('auth/login', auth.login_view, name='api_login'),
    path('auth/logout', auth.logout_view, name='api_logout'),
    path('auth/me', auth.me_view, name='api_me'),

    path('auth/forgot-password', auth.forgot_password_view, name='api_forgot_password'),
    path('auth/reset-password', auth.reset_password_view, name='api_reset_password'),
    
    # TMDB proxy endpoints - trending
    path('tmdb/trending', api.trending, name='api_trending'),
    
    # TMDB proxy endpoints - movies
    path('tmdb/movies/popular', api.movies_popular, name='api_movies_popular'),
    path('tmdb/movies/top-rated', api.movies_top_rated, name='api_movies_top_rated'),
    path('tmdb/movies/now-playing', api.movies_now_playing, name='api_movies_now_playing'),
    path('tmdb/movies/upcoming', api.movies_upcoming, name='api_movies_upcoming'),
    path('tmdb/movies/indian', api.indian_movies, name='api_indian_movies'),
    
    # TMDB proxy endpoints - movie details
    path('tmdb/movie/<int:movie_id>', api.movie_details, name='api_movie_details'),
    path('tmdb/movie/<int:movie_id>/videos', api.movie_videos, name='api_movie_videos'),
    path('tmdb/movie/<int:movie_id>/credits', api.movie_credits, name='api_movie_credits'),
    path('tmdb/movie/<int:movie_id>/watch/providers', api.movie_watch_providers, name='api_movie_watch_providers'),
    path('tmdb/movie/<int:movie_id>/similar', api.movie_similar, name='api_movie_similar'),
    path('tmdb/movie/<int:movie_id>/recommendations', api.movie_recommendations_tmdb, name='api_movie_recommendations'),
    path('tmdb/movie/changes', api.movie_changes, name='api_movie_changes'),
    
    # TMDB proxy endpoints - TV
    path('tmdb/tv/popular', api.tv_popular, name='api_tv_popular'),
    path('tmdb/tv/top-rated', api.tv_top_rated, name='api_tv_top_rated'),
    path('tmdb/tv/airing-today', api.tv_airing_today, name='api_tv_airing_today'),
    path('tmdb/tv/on-the-air', api.tv_on_the_air, name='api_tv_on_the_air'),
    
    # TMDB proxy endpoints - TV details
    path('tmdb/tv/<int:tv_id>', api.tv_details, name='api_tv_details'),
    path('tmdb/tv/<int:tv_id>/watch/providers', api.tv_watch_providers, name='api_tv_watch_providers'),
    path('tmdb/tv/<int:tv_id>/similar', api.tv_similar, name='api_tv_similar'),
    path('tmdb/tv/<int:tv_id>/recommendations', api.tv_recommendations, name='api_tv_recommendations'),
    path('tmdb/tv/<int:tv_id>/season/<int:season_number>', api.tv_season, name='api_tv_season'),
    
    # TMDB proxy endpoints - search
    path('tmdb/search/multi', api.search_multi, name='api_search_multi'),
    path('tmdb/search/movie', api.search_movies, name='api_search_movies'),
    path('tmdb/search/movies', api.search_movies, name='api_search_movies_alt'),
    path('tmdb/search/tv', api.search_tv, name='api_search_tv'),
    path('tmdb/search/person', api.search_people, name='api_search_people'),
    path('tmdb/search/people', api.search_people, name='api_search_people_alt'),
    path('tmdb/search/company', api.search_companies, name='api_search_companies'),
    path('tmdb/search/collection', api.search_collections, name='api_search_collections'),
    
    # Search Interaction Feedback
    path('search/interaction', api.record_interaction, name='api_search_interaction'),
    
    # TMDB proxy endpoints - genres (both singular and plural for compatibility)
    path('tmdb/genres/movie', api.genres_movie, name='api_genres_movie'),
    path('tmdb/genres/movies', api.genres_movie, name='api_genres_movies'),
    path('tmdb/genres/tv', api.genres_tv, name='api_genres_tv'),
    
    # TMDB proxy endpoints - discover (both singular and plural for compatibility)
    path('tmdb/discover/movie', api.discover_movies, name='api_discover_movie'),
    path('tmdb/discover/movies', api.discover_movies, name='api_discover_movies'),
    path('tmdb/discover/tv', api.discover_tv, name='api_discover_tv'),
    
    # TMDB proxy endpoints - person
    path('tmdb/person/<int:person_id>', api.person_details, name='api_person_details'),
    
    # TMDB proxy endpoints - certifications
    path('tmdb/certification/movie/list', api.certification_movie_list, name='api_certification_movie'),
    
    # TMDB proxy endpoints - configuration
    path('tmdb/configuration', api.tmdb_configuration, name='api_tmdb_configuration'),
    
    # TMDB proxy endpoints - additional movie details
    path('tmdb/movie/<int:movie_id>/reviews', api.movie_reviews, name='api_movie_reviews'),
    path('tmdb/movie/<int:movie_id>/images', api.movie_images, name='api_movie_images'),
    path('tmdb/movie/<int:movie_id>/keywords', api.movie_keywords, name='api_movie_keywords'),
    
    # TMDB proxy endpoints - additional TV details
    path('tmdb/tv/<int:tv_id>/reviews', api.tv_reviews, name='api_tv_reviews'),
    path('tmdb/tv/<int:tv_id>/images', api.tv_images, name='api_tv_images'),
    path('tmdb/tv/<int:tv_id>/keywords', api.tv_keywords, name='api_tv_keywords'),
    path('tmdb/tv/<int:tv_id>/videos', api.tv_videos, name='api_tv_videos'),
    path('tmdb/tv/<int:tv_id>/credits', api.tv_credits, name='api_tv_credits'),
    
    # Mood recommendations
    path('recommendations/mood/<str:mood>', api.mood_recommendations, name='api_mood_recommendations'),
    
    # User profile endpoints
    path('users/by-username/<str:username>', users_api.get_user_by_username, name='api_get_user_by_username'),
    path('users/<str:user_id>/profile', users_api.get_profile, name='api_get_profile'),
    path('users/<str:user_id>', users_api.update_profile, name='api_update_profile'),
    
    # Watchlist endpoints
    path('users/<str:user_id>/watchlist', users_api.get_watchlist, name='api_get_watchlist'),
    path('users/<str:user_id>/watchlist/add', users_api.add_to_watchlist, name='api_add_watchlist'),
    path('users/<str:user_id>/watchlist/<int:tmdb_id>', users_api.remove_from_watchlist, name='api_remove_watchlist'),
    path('users/<str:user_id>/watchlist/check/<int:tmdb_id>', users_api.check_watchlist, name='api_check_watchlist'),
    
    # Favorites endpoints
    path('users/<str:user_id>/favorites', users_api.get_favorites, name='api_get_favorites'),
    path('users/<str:user_id>/favorites/add', users_api.add_to_favorites, name='api_add_favorites'),
    path('users/<str:user_id>/favorites/<int:tmdb_id>', users_api.remove_from_favorites, name='api_remove_favorites'),
    path('users/<str:user_id>/favorites/check/<int:tmdb_id>', users_api.check_favorites, name='api_check_favorites'),
    
    # Viewing history endpoints
    path('users/<str:user_id>/watched', users_api.get_viewing_history, name='api_get_history'),
    path('users/<str:user_id>/watched/add', users_api.add_to_viewing_history, name='api_add_history'),
    path('users/<str:user_id>/watched/<int:tmdb_id>', users_api.remove_from_viewing_history, name='api_remove_history'), # Added remove endpoint
    
    # User reviews endpoints
    path('users/<str:user_id>/reviews', users_api.get_user_reviews, name='api_get_user_reviews'),
    path('users/<str:user_id>/reviews/add', users_api.create_review, name='api_create_review'),
    path('users/<str:user_id>/reviews/<int:review_id>', users_api.delete_review, name='api_delete_review'),
    path('reviews/<int:tmdb_id>', users_api.get_reviews_for_content, name='api_get_content_reviews'),
    
    # Follow endpoints
    path('users/<str:user_id>/followers', social_api.get_followers, name='api_get_followers'),
    path('users/<str:user_id>/following', social_api.get_following, name='api_get_following'),
    path('users/<str:user_id>/follow', social_api.follow_user, name='api_follow'),
    path('users/<str:user_id>/follow/<int:target_user_id>', social_api.unfollow_user, name='api_unfollow'),
    path('users/<str:user_id>/is-following/<int:target_user_id>', social_api.is_following, name='api_is_following'),
    
    # User lists endpoints
    path('users/<str:user_id>/lists', social_api.get_user_lists, name='api_get_user_lists'),
    path('users/<str:user_id>/lists/create', social_api.create_list, name='api_create_list'),
    path('lists/<int:list_id>', social_api.get_list_detail, name='api_get_list'),
    path('lists/<int:list_id>/update', social_api.update_list, name='api_update_list'),
    path('lists/<int:list_id>/delete', social_api.delete_list, name='api_delete_list'),
    path('lists/<int:list_id>/items', social_api.add_list_item, name='api_add_list_item'),
    path('lists/<int:list_id>/items/<int:item_id>', social_api.remove_list_item, name='api_remove_list_item'),
    
    # Notifications endpoints
    path('users/<str:user_id>/notifications', social_api.get_notifications, name='api_get_notifications'),
    path('users/<str:user_id>/notifications/read', social_api.mark_notifications_read, name='api_mark_read'),
    
    # Community endpoints
    path('community/notifications/unread/count', social_api.notifications_unread_count, name='api_notifications_count'),
    path('community/lists/containing/<int:tmdb_id>/<str:media_type>', social_api.lists_containing_content, name='api_lists_containing'),
    path('sentiment/<int:tmdb_id>/<str:media_type>', social_api.get_sentiment, name='api_sentiment'),
    path('ratings', social_api.get_ratings, name='api_ratings'),
    path('ratings/<int:review_id>', social_api.manage_rating, name='api_manage_rating'),
    path('ratings/create', social_api.create_rating, name='api_create_rating'),
    path('community/top-reviews', social_api.get_top_reviews, name='api_top_reviews'),
    path('community/lists/public', social_api.get_public_lists, name='api_public_lists'),
    path('community/lists', social_api.create_community_list, name='api_create_list'),
    path('community/lists/<int:list_id>', social_api.manage_community_list, name='api_manage_community_list'),
    path('community/lists/<int:list_id>/items', social_api.add_list_item, name='api_add_list_item'),
    path('community/lists/<int:list_id>/items/<int:item_id>', social_api.remove_list_item, name='api_remove_list_item'),
    path('community/users/<str:user_id>/lists', social_api.get_user_lists, name='api_user_lists'),
    # path('community/community-feed', social_api.get_community_feed, name='api_community_feed'),
    path('community/community-feed', social_api.get_community_feed, name='api_community_feed'),
    path('community/leaderboards', social_api.get_leaderboards, name='api_leaderboards'),
    path('community/trending', social_api.get_trending_content, name='api_trending_content'),
    path('community/activity-prompts/<str:user_id>', social_api.get_activity_prompts, name='api_activity_prompts'),
    path('community/lists/recommended/<str:user_id>', social_api.get_recommended_lists, name='api_recommended_lists'),
    path('community/users/<str:user_id>/similar', social_api.get_similar_users, name='api_similar_users'),
    path('community/personalized-feed/<str:user_id>', social_api.get_personalized_feed, name='api_personalized_feed'),
    
    # AI Recommendations endpoints
    path('ai/chat', recommendations_api.ai_chat, name='api_ai_chat'),
    path('ai/chat/stream', recommendations_api.ai_chat_stream, name='api_ai_chat_stream'),
    path('recommendations/preferences', recommendations_api.save_preferences, name='api_save_preferences'),
    path('users/<str:user_id>/preferences', recommendations_api.get_preferences, name='api_get_preferences'),

    path('recommendations/pattern/analyze/<str:user_id>', recommendations_api.pattern_analyze, name='api_pattern_analyze'),
    path('recommendations/pattern/predict/<str:user_id>', recommendations_api.pattern_predict, name='api_pattern_predict'),
    path('recommendations/explain/gemini', recommendations_api.explain_with_gemini, name='api_explain_gemini'),
    path('users/recommendations/for/<int:tmdb_id>/<str:media_type>', social_api.get_user_recommendations_for_content, name='api_user_recs_for_content'),
    

    # External API endpoints (YouTube, ratings)
    path('external/youtube/search', external_api.youtube_search, name='api_youtube_search'),
    path('external/youtube/videos', external_api.youtube_videos, name='api_youtube_videos'),
    path('external/ratings/<str:imdb_id>', external_api.movie_ratings, name='api_movie_ratings'),
    path('external/youtube/streaming-data/<str:video_id>', external_api.youtube_streaming_data, name='api_youtube_streaming'),
    
    # Review comments and awards endpoints
    path('reviews/<int:review_id>/comments', social_api.get_review_comments, name='api_get_review_comments'),
    path('reviews/<int:review_id>/comments/add', social_api.add_review_comment, name='api_add_review_comment'),
    path('reviews/<int:review_id>/awards', social_api.get_review_awards, name='api_get_review_awards'),
    path('reviews/<int:review_id>/awards/add', social_api.get_review_awards, name='api_give_review_award'),
    
    # Community aliases for review endpoints (frontend compatibility)
    path('community/reviews/<int:review_id>/comments', social_api.get_review_comments, name='api_community_review_comments'),
    path('community/reviews/<int:review_id>/comments/add', social_api.add_review_comment, name='api_community_add_comment'),
    path('community/reviews/<int:review_id>/comments/<int:comment_id>', social_api.delete_review_comment, name='api_community_delete_comment'),
    path('community/reviews/<int:review_id>/awards', social_api.get_review_awards, name='api_community_review_awards'),
    path('community/reviews/<int:review_id>/awards/add', social_api.get_review_awards, name='api_community_give_award'),
    path('community/reviews/<int:review_id>/awards/<int:award_id>', social_api.delete_review_award, name='api_community_delete_award'),
    path('community/reviews/<int:review_id>/user-awards', social_api.get_user_awards_for_review, name='api_community_user_awards'),
    
    # List follows endpoints
    path('lists/<int:list_id>/follow', social_api.follow_list, name='api_follow_list'),
    path('lists/<int:list_id>/unfollow', social_api.unfollow_list, name='api_unfollow_list'),
    path('lists/<int:list_id>/followers', social_api.get_list_followers, name='api_list_followers'),
    path('community/lists/<int:list_id>/is-following', social_api.is_following_list, name='api_is_following_list'),

    # User Impact & Badges (Real Users)
    path('community/users/<str:user_id>/badge-progress', social_api.get_user_badge_progress, name='api_user_badge_progress'),
    path('community/user-impact/<str:user_id>', social_api.get_user_impact, name='api_user_impact'),
    
    # Activity stats endpoints
    path('users/<str:user_id>/stats', social_api.get_activity_stats, name='api_activity_stats'),
    path('community/<str:user_id>/stats', social_api.get_activity_stats, name='api_community_activity_stats'), # Alias for frontend
    
    # User-submitted recommendations endpoints
    path('recommendations/submit', social_api.submit_user_recommendation, name='api_submit_recommendation'),
    path('recommendations/for/<int:tmdb_id>/<str:media_type>', social_api.get_user_recommendations_for_content, name='api_get_user_recommendations'),
    path('recommendations/<int:recommendation_id>/vote', social_api.vote_on_recommendation, name='api_vote_recommendation'),
    
    # User-specific recommendation endpoints (for frontend compatibility)
    path('users/<str:user_id>/recommendations', social_api.submit_user_recommendation, name='api_user_submit_recommendation'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>', social_api.delete_user_recommendation, name='api_user_delete_recommendation'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>/comments', social_api.user_recommendation_comments, name='api_user_rec_comments'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>/vote', social_api.user_recommendation_vote, name='api_user_rec_vote'),
    path('users/recommendations/<int:recommendation_id>/comments', social_api.get_recommendation_comments, name='api_user_rec_comments_alt'),
    
    # Recommendation comments endpoints
    path('recommendations/<int:recommendation_id>/comments', social_api.get_recommendation_comments, name='api_get_rec_comments'),
    path('recommendations/<int:recommendation_id>/comments/add', social_api.add_recommendation_comment, name='api_add_rec_comment'),
    
    # Notification settings endpoints
    path('users/<int:user_id>/notification-settings', social_api.get_notification_settings, name='api_get_notification_settings'),
    path('users/<int:user_id>/notification-settings/update', social_api.update_notification_settings, name='api_update_notification_settings'),
    
    # List collaborators endpoints
    path('lists/<int:list_id>/collaborators', social_api.get_list_collaborators, name='api_get_list_collaborators'),
    path('lists/<int:list_id>/collaborators/invite', social_api.invite_list_collaborator, name='api_invite_collaborator'),
    path('lists/<int:list_id>/collaborators/<int:collaborator_id>', social_api.remove_list_collaborator, name='api_remove_collaborator'),
    
    # User badges endpoints
    path('users/<int:user_id>/badges', social_api.get_user_badges, name='api_get_user_badges'),
    path('users/<int:user_id>/badges/award', social_api.award_badge, name='api_award_badge'),
    
    # TMDB Rating endpoints (POST/DELETE)
    path('tmdb/movie/<int:movie_id>/rating', api.rate_movie, name='api_rate_movie'),
    path('tmdb/tv/<int:tv_id>/rating', api.rate_tv_show, name='api_rate_tv'),
    path('tmdb/authentication/guest_session/new', api.get_guest_session, name='api_guest_session'),
    
    # Analytics API endpoints
    path('analytics/user/<int:user_id>/engagement', analytics_api.get_user_engagement, name='api_user_engagement'),
    path('analytics/content/<int:tmdb_id>/stats', analytics_api.get_content_stats, name='api_content_stats'),
    path('analytics/popular', analytics_api.get_popular_content, name='api_popular_content'),
    path('analytics/track-event', analytics_api.track_event, name='api_track_event'),
    path('analytics/recommendations/<str:user_id>', analytics_api.get_recommendation_metrics, name='api_rec_metrics'),
    path('analytics/platform', analytics_api.get_platform_stats, name='api_platform_stats'),
    
    # ML Recommendation API endpoints
    path('recommendations/hybrid/<str:user_id>', ml_api.get_hybrid_recommendations, name='api_hybrid_recs'),
    path('recommendations/collaborative/<str:user_id>', ml_api.get_collaborative_recommendations, name='api_collab_recs'),
    path('recommendations/similar/<int:tmdb_id>', ml_api.get_similar_items, name='api_similar_items'),
    path('recommendations/users/<str:user_id>/similar', ml_api.get_user_similarity, name='api_user_similarity'),
    path('recommendations/explain/<str:user_id>/<int:tmdb_id>', ml_api.get_recommendation_explanation, name='api_rec_explain'),
    path('recommendations/semantic-search', ml_api.semantic_search, name='api_semantic_search'),
    
    # Contextual Bandits API endpoints
    path('ml/bandit/<str:user_id>/stats', ml_api.get_bandit_statistics, name='api_bandit_stats'),
    path('ml/bandit/<str:user_id>/select', ml_api.select_recommendation_arm, name='api_bandit_select'),
    path('ml/bandit/reward', ml_api.update_bandit_reward, name='api_bandit_reward'),
    
    # Diversity Engine API endpoints
    path('ml/diversity/apply', ml_api.apply_diversity, name='api_apply_diversity'),
    path('ml/diversity/<str:user_id>/metrics', ml_api.get_diversity_metrics, name='api_diversity_metrics'),
    
    # Sentiment Analysis API endpoints
    path('ml/sentiment/<int:tmdb_id>', ml_api.get_sentiment_analytics, name='api_sentiment_analytics'),
    path('ml/sentiment/analyze', ml_api.analyze_text_sentiment, name='api_analyze_sentiment'),
    path('ml/sentiment/update/<int:tmdb_id>', ml_api.update_sentiment_for_content, name='api_update_sentiment'),
    
    # Recommendation History and Interaction Logging API endpoints
    path('ml/recommendations/history/<str:user_id>', ml_api.get_recommendation_history, name='api_rec_history'),
    path('ml/recommendations/interaction', ml_api.log_recommendation_interaction, name='api_rec_interaction'),
    
    # Explainability Engine API endpoints
    path('ml/explainability/global-importance', ml_api.get_global_feature_importance, name='api_global_importance'),
    path('ml/explainability/counterfactual/<str:user_id>/<int:tmdb_id>', ml_api.get_counterfactual_explanation, name='api_counterfactual'),
    path('ml/explainability/local/<str:user_id>/<int:tmdb_id>', ml_api.get_local_explanation, name='api_local_explanation'),
    path('ml/explainability/calibrate', ml_api.calibrate_confidence, name='api_calibrate_confidence'),
    
    # Pattern Recognition API endpoint
    path('ml/patterns/<str:user_id>', ml_api.get_viewing_patterns, name='api_viewing_patterns'),

    # Similar Movies (ChromaDB)
    path('ml/similar/semantic/<int:tmdb_id>', ml_api.get_similar_movies_semantic, name='api_similar_semantic'),

    # Cine-Clubs endpoints
    path('clubs', clubs_api.clubs_list, name='api_clubs_list'),
    path('clubs/<int:club_id>', clubs_api.club_details, name='api_club_details'),
    path('clubs/<int:club_id>/join', clubs_api.join_club, name='api_join_club'),
    path('clubs/<int:club_id>/threads', clubs_api.club_threads, name='api_club_threads'),
    path('clubs/threads/<int:thread_id>', clubs_api.thread_details, name='api_thread_details'),
    path('clubs/threads/<int:thread_id>/posts', clubs_api.create_post, name='api_create_post'),
]

