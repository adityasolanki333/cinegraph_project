from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UserReview, UserList, ReviewComment, UserFollow, UserActivityStats, UserBadge, ReviewAward

@receiver(post_save, sender=UserReview)
def update_review_stats(sender, instance, created, **kwargs):
    if created:
        stats, _ = UserActivityStats.objects.get_or_create(user=instance.user)
        stats.total_reviews += 1
        stats.experience_points += 20  # XP for reviewing
        stats.user_level = stats.calculate_level()
        stats.save()
        check_badges(instance.user, stats)

    # Sentiment Analysis Update
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        from .models import SentimentAnalytics, UserReview
        
        # We recalculate sentiment for the movie to ensure accuracy on updates as well
        if instance.review_text:
            analyzer = SentimentIntensityAnalyzer()
            reviews = UserReview.objects.filter(
                tmdb_id=instance.tmdb_id, 
                media_type=instance.media_type
            ).exclude(review_text__exact='')
            
            total = 0
            total_score = 0
            pos = 0; neg = 0; neu = 0
            
            for r in reviews:
                score = analyzer.polarity_scores(r.review_text)['compound']
                total_score += score
                total += 1
                if score > 0.05:
                    pos += 1
                elif score < -0.05:
                    neg += 1
                else:
                    neu += 1
            
            if total > 0:
                analytics, _ = SentimentAnalytics.objects.get_or_create(
                    tmdb_id=instance.tmdb_id,
                    media_type=instance.media_type
                )
                analytics.avg_sentiment_score = total_score / total
                analytics.total_reviews = total
                analytics.positive_count = pos
                analytics.negative_count = neg
                analytics.neutral_count = neu
                analytics.save()
    except Exception as e:
        print(f"Failed to process sentiment analysis: {e}")

    # Trigger real-time ML Upsert via Thread
    if created:
        try:
            from .ml.pinecone_service import pinecone_service
            from .models import TmdbTrainingData
            import threading
            
            if pinecone_service and pinecone_service.is_initialized():
                movie = TmdbTrainingData.objects.filter(tmdb_id=instance.tmdb_id).first()
                if movie:
                    movie_data = {
                        'id': movie.tmdb_id,
                        'title': movie.title,
                        'overview': movie.overview,
                        'genres': movie.genres,
                        'director': '', # Missing from basic DB model, but Pinecone handles it gracefully
                        'cast': '',
                        'release_date': movie.release_date,
                        'vote_average': movie.vote_average,
                        'poster_path': movie.poster_path
                    }
                    threading.Thread(target=pinecone_service.upsert_movie, args=(movie_data,)).start()
        except Exception as e:
            print(f"Failed to trigger ML vector upsert on review: {e}")

@receiver(post_delete, sender=UserReview)
def decrement_review_stats(sender, instance, **kwargs):
    try:
        stats = UserActivityStats.objects.get(user=instance.user)
        stats.total_reviews = max(0, stats.total_reviews - 1)
        stats.save()
    except UserActivityStats.DoesNotExist:
        pass

@receiver(post_save, sender=UserList)
def update_list_stats(sender, instance, created, **kwargs):
    if created:
        stats, _ = UserActivityStats.objects.get_or_create(user=instance.user)
        stats.total_lists += 1
        stats.experience_points += 30  # XP for creating a list
        stats.user_level = stats.calculate_level()
        stats.save()
        check_badges(instance.user, stats)

@receiver(post_delete, sender=UserList)
def decrement_list_stats(sender, instance, **kwargs):
    try:
        stats = UserActivityStats.objects.get(user=instance.user)
        stats.total_lists = max(0, stats.total_lists - 1)
        stats.save()
    except UserActivityStats.DoesNotExist:
        pass

@receiver(post_save, sender=ReviewComment)
def update_comment_stats(sender, instance, created, **kwargs):
    if created:
        stats, _ = UserActivityStats.objects.get_or_create(user=instance.user)
        stats.total_comments += 1
        stats.experience_points += 5  # XP for commenting
        stats.user_level = stats.calculate_level()
        stats.save()

@receiver(post_save, sender=UserFollow)
def update_follow_stats(sender, instance, created, **kwargs):
    if created:
        # Update follower's stats (the one doing the following)
        follower_stats, _ = UserActivityStats.objects.get_or_create(user=instance.follower)
        follower_stats.total_following += 1
        follower_stats.save()
        check_badges(instance.follower, follower_stats)

        # Update following user's stats (the one getting followed)
        following_stats, _ = UserActivityStats.objects.get_or_create(user=instance.following)
        following_stats.total_followers += 1
        following_stats.experience_points += 10 # XP for getting a follower
        following_stats.user_level = following_stats.calculate_level()
        following_stats.save()
        check_badges(instance.following, following_stats)

@receiver(post_delete, sender=UserFollow)
def decrement_follow_stats(sender, instance, **kwargs):
    try:
        follower_stats = UserActivityStats.objects.get(user=instance.follower)
        follower_stats.total_following = max(0, follower_stats.total_following - 1)
        follower_stats.save()
    except UserActivityStats.DoesNotExist:
        pass

    try:
        following_stats = UserActivityStats.objects.get(user=instance.following)
        following_stats.total_followers = max(0, following_stats.total_followers - 1)
        following_stats.save()
    except UserActivityStats.DoesNotExist:
        pass

@receiver(post_save, sender=ReviewAward)
def update_award_stats(sender, instance, created, **kwargs):
    if created:
        # Giver
        giver_stats, _ = UserActivityStats.objects.get_or_create(user=instance.user)
        giver_stats.total_awards_given += 1
        giver_stats.experience_points += 5
        giver_stats.user_level = giver_stats.calculate_level()
        giver_stats.save()
        
        # Receiver
        receiver_stats, _ = UserActivityStats.objects.get_or_create(user=instance.review.user)
        receiver_stats.total_awards_received += 1
        receiver_stats.experience_points += 15
        receiver_stats.user_level = receiver_stats.calculate_level()
        receiver_stats.save()


def check_badges(user, stats):
    """Check and award badges based on stats."""
    badges_to_award = []

    # Reviews
    if stats.total_reviews >= 1:
        badges_to_award.append('first_review')
    if stats.total_reviews >= 10:
        badges_to_award.append('review_master')
    if stats.total_reviews >= 50:
        badges_to_award.append('critic')

    # Lists
    if stats.total_lists >= 5:
        badges_to_award.append('list_creator')
    if stats.total_lists >= 20:
        badges_to_award.append('curator')

    # Social
    if stats.total_following >= 10:
        badges_to_award.append('social_butterfly')
    if stats.total_followers >= 20:
        badges_to_award.append('influencer')
    if stats.total_followers >= 100:
        badges_to_award.append('trendsetter')

    for badge_type in badges_to_award:
        UserBadge.objects.get_or_create(user=user, badge_type=badge_type)
