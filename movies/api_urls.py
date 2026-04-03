from django.urls import path
from .api_views import auth as auth_views
from .api_views import tmdb as tmdb_views
from .api_views import users as users_views
from .api_views import followers as followers_views
from .api_views import lists as lists_views
from .api_views import reviews as reviews_views
from .api_views import notifications as notif_views
from .api_views import community as community_views
from .api_views import recommendations as rec_views
from .api_views import external as ext_views
from .api_views import analytics as analytics_views
from .api_views import ml as ml_views
from .api_views import clubs as clubs_views

urlpatterns = [
    path('auth/csrf', auth_views.CsrfTokenView.as_view(), name='api_csrf'),
    path('auth/register', auth_views.RegisterView.as_view(), name='api_register'),
    path('auth/login', auth_views.LoginView.as_view(), name='api_login'),
    path('auth/logout', auth_views.LogoutView.as_view(), name='api_logout'),
    path('auth/me', auth_views.MeView.as_view(), name='api_me'),
    path('auth/delete-account', auth_views.DeleteAccountView.as_view(), name='api_delete_account'),
    path('auth/forgot-password', auth_views.ForgotPasswordView.as_view(), name='api_forgot_password'),
    path('auth/reset-password', auth_views.ResetPasswordView.as_view(), name='api_reset_password'),

    path('tmdb/trending', tmdb_views.TrendingView.as_view(), name='api_trending'),

    path('tmdb/movies/popular', tmdb_views.MoviesPopularView.as_view(), name='api_movies_popular'),
    path('tmdb/movies/top-rated', tmdb_views.MoviesTopRatedView.as_view(), name='api_movies_top_rated'),
    path('tmdb/movies/now-playing', tmdb_views.MoviesNowPlayingView.as_view(), name='api_movies_now_playing'),
    path('tmdb/movies/upcoming', tmdb_views.MoviesUpcomingView.as_view(), name='api_movies_upcoming'),
    path('tmdb/movies/indian', tmdb_views.IndianMoviesView.as_view(), name='api_indian_movies'),

    path('tmdb/movie/<int:movie_id>', tmdb_views.MovieDetailsView.as_view(), name='api_movie_details'),
    path('tmdb/movie/<int:movie_id>/videos', tmdb_views.MovieVideosView.as_view(), name='api_movie_videos'),
    path('tmdb/movie/<int:movie_id>/credits', tmdb_views.MovieCreditsView.as_view(), name='api_movie_credits'),
    path('tmdb/movie/<int:movie_id>/watch/providers', tmdb_views.MovieWatchProvidersView.as_view(), name='api_movie_watch_providers'),
    path('tmdb/movie/<int:movie_id>/similar', tmdb_views.MovieSimilarView.as_view(), name='api_movie_similar'),
    path('tmdb/movie/<int:movie_id>/recommendations', tmdb_views.MovieRecommendationsTmdbView.as_view(), name='api_movie_recommendations'),
    path('tmdb/movie/changes', tmdb_views.MovieChangesView.as_view(), name='api_movie_changes'),

    path('tmdb/tv/popular', tmdb_views.TVPopularView.as_view(), name='api_tv_popular'),
    path('tmdb/tv/top-rated', tmdb_views.TVTopRatedView.as_view(), name='api_tv_top_rated'),
    path('tmdb/tv/airing-today', tmdb_views.TVAiringTodayView.as_view(), name='api_tv_airing_today'),
    path('tmdb/tv/on-the-air', tmdb_views.TVOnTheAirView.as_view(), name='api_tv_on_the_air'),

    path('tmdb/tv/<int:tv_id>', tmdb_views.TVDetailsView.as_view(), name='api_tv_details'),
    path('tmdb/tv/<int:tv_id>/watch/providers', tmdb_views.TVWatchProvidersView.as_view(), name='api_tv_watch_providers'),
    path('tmdb/tv/<int:tv_id>/similar', tmdb_views.TVSimilarView.as_view(), name='api_tv_similar'),
    path('tmdb/tv/<int:tv_id>/recommendations', tmdb_views.TVRecommendationsView.as_view(), name='api_tv_recommendations'),
    path('tmdb/tv/<int:tv_id>/season/<int:season_number>', tmdb_views.TVSeasonView.as_view(), name='api_tv_season'),

    path('tmdb/search/multi', tmdb_views.SearchMultiView.as_view(), name='api_search_multi'),
    path('tmdb/search/movies', tmdb_views.SearchMoviesView.as_view(), name='api_search_movies'),
    path('tmdb/search/tv', tmdb_views.SearchTVView.as_view(), name='api_search_tv'),
    path('tmdb/search/person', tmdb_views.SearchPeopleView.as_view(), name='api_search_people'),
    path('tmdb/search/people', tmdb_views.SearchPeopleView.as_view(), name='api_search_people_alt'),
    path('tmdb/search/company', tmdb_views.SearchCompaniesView.as_view(), name='api_search_companies'),
    path('tmdb/search/collection', tmdb_views.SearchCollectionsView.as_view(), name='api_search_collections'),

    path('search/interaction', tmdb_views.RecordInteractionView.as_view(), name='api_search_interaction'),

    path('tmdb/genres/movies', tmdb_views.GenresMovieView.as_view(), name='api_genres_movies'),
    path('tmdb/genres/tv', tmdb_views.GenresTVView.as_view(), name='api_genres_tv'),

    path('tmdb/discover/movies', tmdb_views.DiscoverMoviesView.as_view(), name='api_discover_movies'),
    path('tmdb/discover/tv', tmdb_views.DiscoverTVView.as_view(), name='api_discover_tv'),

    path('tmdb/person/<int:person_id>', tmdb_views.PersonDetailsView.as_view(), name='api_person_details'),

    path('tmdb/certification/movie/list', tmdb_views.CertificationMovieListView.as_view(), name='api_certification_movie'),

    path('tmdb/configuration', tmdb_views.TMDBConfigurationView.as_view(), name='api_tmdb_configuration'),

    path('tmdb/movie/<int:movie_id>/reviews', tmdb_views.MovieReviewsView.as_view(), name='api_movie_reviews'),
    path('tmdb/movie/<int:movie_id>/images', tmdb_views.MovieImagesView.as_view(), name='api_movie_images'),
    path('tmdb/movie/<int:movie_id>/keywords', tmdb_views.MovieKeywordsView.as_view(), name='api_movie_keywords'),

    path('tmdb/tv/<int:tv_id>/reviews', tmdb_views.TVReviewsView.as_view(), name='api_tv_reviews'),
    path('tmdb/tv/<int:tv_id>/images', tmdb_views.TVImagesView.as_view(), name='api_tv_images'),
    path('tmdb/tv/<int:tv_id>/keywords', tmdb_views.TVKeywordsView.as_view(), name='api_tv_keywords'),
    path('tmdb/tv/<int:tv_id>/videos', tmdb_views.TVVideosView.as_view(), name='api_tv_videos'),
    path('tmdb/tv/<int:tv_id>/credits', tmdb_views.TVCreditsView.as_view(), name='api_tv_credits'),

    path('recommendations/mood/<str:mood>', tmdb_views.MoodRecommendationsView.as_view(), name='api_mood_recommendations'),

    path('users/by-username/<str:username>', users_views.UserByUsernameView.as_view(), name='api_get_user_by_username'),
    path('users/<str:user_id>/profile', users_views.UserProfileView.as_view(), name='api_get_profile'),
    path('users/<str:user_id>', users_views.UpdateProfileView.as_view(), name='api_update_profile'),

    path('users/<str:user_id>/watchlist', users_views.WatchlistView.as_view(), name='api_get_watchlist'),
    path('users/<str:user_id>/watchlist/add', users_views.WatchlistAddView.as_view(), name='api_add_watchlist'),
    path('users/<str:user_id>/watchlist/<int:tmdb_id>', users_views.WatchlistRemoveView.as_view(), name='api_remove_watchlist'),
    path('users/<str:user_id>/watchlist/check/<int:tmdb_id>', users_views.WatchlistCheckView.as_view(), name='api_check_watchlist'),

    path('users/<str:user_id>/favorites', users_views.FavoritesView.as_view(), name='api_get_favorites'),
    path('users/<str:user_id>/favorites/add', users_views.FavoritesAddView.as_view(), name='api_add_favorites'),
    path('users/<str:user_id>/favorites/<int:tmdb_id>', users_views.FavoritesRemoveView.as_view(), name='api_remove_favorites'),
    path('users/<str:user_id>/favorites/check/<int:tmdb_id>', users_views.FavoritesCheckView.as_view(), name='api_check_favorites'),

    path('users/<str:user_id>/watched', users_views.ViewingHistoryView.as_view(), name='api_get_history'),
    path('users/<str:user_id>/watched/add', users_views.ViewingHistoryAddView.as_view(), name='api_add_history'),
    path('users/<str:user_id>/watched/<int:tmdb_id>', users_views.ViewingHistoryRemoveView.as_view(), name='api_remove_history'),

    path('users/<str:user_id>/reviews', users_views.UserReviewsView.as_view(), name='api_get_user_reviews'),
    path('users/<str:user_id>/reviews/add', users_views.CreateReviewView.as_view(), name='api_create_review'),
    path('users/<str:user_id>/reviews/<int:review_id>', users_views.DeleteReviewView.as_view(), name='api_delete_review'),
    path('reviews/<int:tmdb_id>', users_views.ContentReviewsView.as_view(), name='api_get_content_reviews'),

    path('users/<str:user_id>/followers', followers_views.FollowersView.as_view(), name='api_get_followers'),
    path('users/<str:user_id>/following', followers_views.FollowingView.as_view(), name='api_get_following'),
    path('users/<str:user_id>/follow', followers_views.FollowUserView.as_view(), name='api_follow'),
    path('users/<str:user_id>/follow/<int:target_user_id>', followers_views.UnfollowUserView.as_view(), name='api_unfollow'),
    path('users/<str:user_id>/is-following/<int:target_user_id>', followers_views.IsFollowingView.as_view(), name='api_is_following'),

    path('users/<str:user_id>/lists', lists_views.UserListsView.as_view(), name='api_get_user_lists'),
    path('users/<str:user_id>/lists/create', lists_views.CreateListView.as_view(), name='api_create_list'),
    path('lists/<int:list_id>', lists_views.ListDetailView.as_view(), name='api_get_list'),
    path('lists/<int:list_id>/update', lists_views.UpdateListView.as_view(), name='api_update_list'),
    path('lists/<int:list_id>/delete', lists_views.DeleteListView.as_view(), name='api_delete_list'),
    path('lists/<int:list_id>/items', lists_views.AddListItemView.as_view(), name='api_add_list_item'),
    path('lists/<int:list_id>/items/<int:item_id>', lists_views.RemoveListItemView.as_view(), name='api_remove_list_item'),

    path('users/<str:user_id>/notifications', notif_views.NotificationsView.as_view(), name='api_get_notifications'),
    path('users/<str:user_id>/notifications/read', notif_views.MarkNotificationsReadView.as_view(), name='api_mark_read'),

    path('community/notifications/unread/count', notif_views.UnreadCountView.as_view(), name='api_notifications_count'),
    path('community/notifications/read-all', notif_views.CommunityMarkAllReadView.as_view(), name='api_community_mark_all_read'),
    path('community/notifications/<int:notification_id>/read', notif_views.CommunityMarkNotificationReadView.as_view(), name='api_community_mark_read'),
    path('community/notifications/<int:notification_id>', notif_views.CommunityDeleteNotificationView.as_view(), name='api_community_delete_notification'),
    path('community/notifications', notif_views.CommunityNotificationsView.as_view(), name='api_community_get_notifications'),
    path('community/lists/containing/<int:tmdb_id>/<str:media_type>', lists_views.ListsContainingView.as_view(), name='api_lists_containing'),
    path('sentiment/<int:tmdb_id>/<str:media_type>', reviews_views.SentimentView.as_view(), name='api_sentiment'),
    path('ratings', reviews_views.RatingsView.as_view(), name='api_ratings'),
    path('ratings/<int:review_id>', reviews_views.ManageRatingView.as_view(), name='api_manage_rating'),
    path('ratings/create', reviews_views.CreateRatingView.as_view(), name='api_create_rating'),
    path('community/top-reviews', reviews_views.TopReviewsView.as_view(), name='api_top_reviews'),
    path('community/lists/search', lists_views.ListSearchView.as_view(), name='api_list_search'),
    path('community/lists/public', lists_views.PublicListsView.as_view(), name='api_public_lists'),
    path('community/lists', lists_views.CreateListView.as_view(), name='api_create_community_list'),
    path('community/lists/<int:list_id>/similar', lists_views.SimilarListsView.as_view(), name='api_similar_lists'),
    path('community/lists/<int:list_id>', lists_views.ManageCommunityListView.as_view(), name='api_manage_community_list'),
    path('community/lists/<int:list_id>/items', lists_views.AddListItemView.as_view(), name='api_community_add_list_item'),
    path('community/lists/<int:list_id>/items/<int:item_id>', lists_views.RemoveListItemView.as_view(), name='api_community_remove_list_item'),
    path('community/users/search', community_views.UserSearchView.as_view(), name='api_user_search'),
    path('community/users/<str:user_id>/lists', lists_views.UserListsView.as_view(), name='api_user_lists'),
    path('community/community-feed', community_views.CommunityFeedView.as_view(), name='api_community_feed'),
    path('community/leaderboards', community_views.LeaderboardsView.as_view(), name='api_leaderboards'),
    path('community/trending', community_views.TrendingContentView.as_view(), name='api_trending_content'),
    path('community/activity-prompts/<str:user_id>', community_views.ActivityPromptsView.as_view(), name='api_activity_prompts'),
    path('community/lists/recommended/<str:user_id>', lists_views.RecommendedListsView.as_view(), name='api_recommended_lists'),
    path('community/users/<str:user_id>/similar', community_views.SimilarUsersView.as_view(), name='api_similar_users'),
    path('community/personalized-feed/<str:user_id>', community_views.PersonalizedFeedView.as_view(), name='api_personalized_feed'),

    path('ai/chat', rec_views.AiChatView.as_view(), name='api_ai_chat'),
    path('ai/chat/stream', rec_views.AiChatStreamView.as_view(), name='api_ai_chat_stream'),
    path('recommendations/preferences', rec_views.SavePreferencesView.as_view(), name='api_save_preferences'),
    path('users/<str:user_id>/preferences', rec_views.GetPreferencesView.as_view(), name='api_get_preferences'),

    path('recommendations/pattern/analyze/<str:user_id>', rec_views.PatternAnalyzeView.as_view(), name='api_pattern_analyze'),
    path('recommendations/pattern/predict/<str:user_id>', rec_views.PatternPredictView.as_view(), name='api_pattern_predict'),
    path('recommendations/explain/gemini', rec_views.ExplainWithGeminiView.as_view(), name='api_explain_gemini'),
    path('users/recommendations/for/<int:tmdb_id>/<str:media_type>', reviews_views.UserRecommendationsForContentView.as_view(), name='api_user_recs_for_content'),

    path('external/youtube/search', ext_views.YouTubeSearchView.as_view(), name='api_youtube_search'),
    path('external/youtube/videos', ext_views.YouTubeVideosView.as_view(), name='api_youtube_videos'),
    path('external/ratings/<str:imdb_id>', ext_views.MovieRatingsView.as_view(), name='api_movie_ratings'),
    path('external/youtube/streaming-data/<str:video_id>', ext_views.YouTubeStreamingDataView.as_view(), name='api_youtube_streaming'),

    path('community/reviews/<int:review_id>/comments', reviews_views.ReviewCommentsView.as_view(), name='api_community_review_comments'),
    path('community/reviews/<int:review_id>/comments/add', reviews_views.AddReviewCommentView.as_view(), name='api_community_add_comment'),
    path('community/reviews/<int:review_id>/comments/<int:comment_id>', reviews_views.DeleteReviewCommentView.as_view(), name='api_community_delete_comment'),
    path('community/reviews/<int:review_id>/awards', reviews_views.ReviewAwardsView.as_view(), name='api_community_review_awards'),
    path('community/reviews/<int:review_id>/awards/add', reviews_views.ReviewAwardsView.as_view(), name='api_community_give_award'),
    path('community/reviews/<int:review_id>/awards/<int:award_id>', reviews_views.DeleteReviewAwardView.as_view(), name='api_community_delete_award'),
    path('community/reviews/<int:review_id>/user-awards', reviews_views.UserAwardsForReviewView.as_view(), name='api_community_user_awards'),

    path('lists/<int:list_id>/follow', lists_views.ListFollowView.as_view(), name='api_follow_list'),
    path('lists/<int:list_id>/unfollow', lists_views.ListUnfollowView.as_view(), name='api_unfollow_list'),
    path('lists/<int:list_id>/followers', lists_views.ListFollowersView.as_view(), name='api_list_followers'),
    path('community/lists/<int:list_id>/is-following', lists_views.IsFollowingListView.as_view(), name='api_is_following_list'),

    path('community/users/<str:user_id>/badge-progress', community_views.UserBadgeProgressView.as_view(), name='api_user_badge_progress'),
    path('community/user-impact/<str:user_id>', community_views.UserImpactView.as_view(), name='api_user_impact'),

    path('users/<str:user_id>/stats', community_views.ActivityStatsView.as_view(), name='api_activity_stats'),

    path('users/<str:user_id>/recommendations', reviews_views.SubmitRecommendationView.as_view(), name='api_user_submit_recommendation'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>', reviews_views.DeleteUserRecommendationView.as_view(), name='api_user_delete_recommendation'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>/comments', reviews_views.UserRecommendationCommentsView.as_view(), name='api_user_rec_comments'),
    path('users/<str:user_id>/recommendations/<int:recommendation_id>/vote', reviews_views.UserRecommendationVoteView.as_view(), name='api_user_rec_vote'),
    path('users/recommendations/<int:recommendation_id>/comments', reviews_views.RecommendationCommentsView.as_view(), name='api_user_rec_comments_alt'),

    path('users/<int:user_id>/notification-settings', notif_views.NotificationSettingsView.as_view(), name='api_get_notification_settings'),
    path('users/<int:user_id>/notification-settings/update', notif_views.UpdateNotificationSettingsView.as_view(), name='api_update_notification_settings'),

    path('lists/<int:list_id>/collaborators', lists_views.ListCollaboratorsView.as_view(), name='api_get_list_collaborators'),
    path('lists/<int:list_id>/collaborators/invite', lists_views.InviteCollaboratorView.as_view(), name='api_invite_collaborator'),
    path('lists/<int:list_id>/collaborators/<int:collaborator_id>', lists_views.RemoveCollaboratorView.as_view(), name='api_remove_collaborator'),

    path('users/<int:user_id>/badges', community_views.UserBadgesView.as_view(), name='api_get_user_badges'),
    path('users/<int:user_id>/badges/award', community_views.AwardBadgeView.as_view(), name='api_award_badge'),

    path('tmdb/movie/<int:movie_id>/rating', tmdb_views.RateMovieView.as_view(), name='api_rate_movie'),
    path('tmdb/tv/<int:tv_id>/rating', tmdb_views.RateTVShowView.as_view(), name='api_rate_tv'),
    path('tmdb/authentication/guest_session/new', tmdb_views.GuestSessionView.as_view(), name='api_guest_session'),

    path('analytics/user/<int:user_id>/engagement', analytics_views.UserEngagementView.as_view(), name='api_user_engagement'),
    path('analytics/content/<int:tmdb_id>/stats', analytics_views.ContentStatsView.as_view(), name='api_content_stats'),
    path('analytics/popular', analytics_views.PopularContentView.as_view(), name='api_popular_content'),
    path('analytics/track-event', analytics_views.TrackEventView.as_view(), name='api_track_event'),
    path('analytics/recommendations/<str:user_id>', analytics_views.RecommendationMetricsView.as_view(), name='api_rec_metrics'),
    path('analytics/platform', analytics_views.PlatformStatsView.as_view(), name='api_platform_stats'),

    path('recommendations/hybrid/<str:user_id>', ml_views.HybridRecommendationsView.as_view(), name='api_hybrid_recs'),
    path('recommendations/collaborative/<str:user_id>', ml_views.CollaborativeRecommendationsView.as_view(), name='api_collab_recs'),
    path('recommendations/similar/<int:tmdb_id>', ml_views.SimilarItemsView.as_view(), name='api_similar_items'),
    path('recommendations/users/<str:user_id>/similar', ml_views.UserSimilarityView.as_view(), name='api_user_similarity'),
    path('recommendations/explain/<str:user_id>/<int:tmdb_id>', ml_views.RecommendationExplanationView.as_view(), name='api_rec_explain'),
    path('recommendations/semantic-search', ml_views.SemanticSearchView.as_view(), name='api_semantic_search'),

    path('ml/bandit/<str:user_id>/stats', ml_views.BanditStatisticsView.as_view(), name='api_bandit_stats'),
    path('ml/bandit/<str:user_id>/select', ml_views.BanditSelectView.as_view(), name='api_bandit_select'),
    path('ml/bandit/reward', ml_views.BanditRewardView.as_view(), name='api_bandit_reward'),

    path('ml/diversity/apply', ml_views.ApplyDiversityView.as_view(), name='api_apply_diversity'),
    path('ml/diversity/<str:user_id>/metrics', ml_views.DiversityMetricsView.as_view(), name='api_diversity_metrics'),

    path('ml/sentiment/<int:tmdb_id>', ml_views.SentimentAnalyticsView.as_view(), name='api_sentiment_analytics'),
    path('ml/sentiment/analyze', ml_views.AnalyzeTextSentimentView.as_view(), name='api_analyze_sentiment'),
    path('ml/sentiment/update/<int:tmdb_id>', ml_views.UpdateSentimentView.as_view(), name='api_update_sentiment'),

    path('ml/recommendations/history/<str:user_id>', ml_views.RecommendationHistoryView.as_view(), name='api_rec_history'),
    path('ml/recommendations/interaction', ml_views.LogRecommendationInteractionView.as_view(), name='api_rec_interaction'),

    path('ml/explainability/global-importance', ml_views.GlobalFeatureImportanceView.as_view(), name='api_global_importance'),
    path('ml/explainability/counterfactual/<str:user_id>/<int:tmdb_id>', ml_views.CounterfactualExplanationView.as_view(), name='api_counterfactual'),
    path('ml/explainability/local/<str:user_id>/<int:tmdb_id>', ml_views.LocalExplanationView.as_view(), name='api_local_explanation'),
    path('ml/explainability/calibrate', ml_views.CalibrateConfidenceView.as_view(), name='api_calibrate_confidence'),

    path('ml/patterns/<str:user_id>', ml_views.ViewingPatternsView.as_view(), name='api_viewing_patterns'),

    path('ml/similar/semantic/<int:tmdb_id>', ml_views.SimilarMoviesSemanticView.as_view(), name='api_similar_semantic'),

    path('clubs', clubs_views.ClubsListView.as_view(), name='api_clubs_list'),
    path('clubs/<int:club_id>', clubs_views.ClubDetailView.as_view(), name='api_club_details'),
    path('clubs/<int:club_id>/join', clubs_views.JoinClubView.as_view(), name='api_join_club'),
    path('clubs/<int:club_id>/threads', clubs_views.ClubThreadsView.as_view(), name='api_club_threads'),
    path('clubs/threads/<int:thread_id>', clubs_views.ThreadDetailView.as_view(), name='api_thread_details'),
    path('clubs/threads/<int:thread_id>/posts', clubs_views.CreatePostView.as_view(), name='api_create_post'),
]
