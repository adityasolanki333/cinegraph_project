import logging
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q, Avg
from movies.models import (
    UserReview, UserRecommendation, RecommendationVote, RecommendationComment,
    ReviewComment, ReviewAward, ReviewInteraction, Notification, UserActivityStats,
)
from movies.serializers.social import UserReviewSerializer
from movies.pagination import paginate_queryset

logger = logging.getLogger(__name__)


class SentimentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id, media_type):
        from movies.api import tmdb_request
        from movies.ml.sentiment_analyzer import sentiment_analyzer

        endpoint = f"/{'movie' if media_type == 'movie' else 'tv'}/{tmdb_id}/reviews"
        tmdb_data = tmdb_request(endpoint, {"page": 1})
        tmdb_results = tmdb_data.get("results", []) if tmdb_data else []

        analyzed_reviews = []
        tmdb_positive = tmdb_negative = tmdb_neutral = 0
        tmdb_score_sum = 0.0

        for r in tmdb_results:
            content = r.get("content", "").strip()
            if not content:
                continue
            result = sentiment_analyzer.analyze_text(content[:2000])
            tmdb_score_sum += result.compound
            label = result.classification
            if label == "positive":
                tmdb_positive += 1
            elif label == "negative":
                tmdb_negative += 1
            else:
                tmdb_neutral += 1
            analyzed_reviews.append({
                "id": r.get("id"),
                "author": r.get("author", "Anonymous"),
                "authorRating": r.get("author_details", {}).get("rating"),
                "content": content[:500] + ("…" if len(content) > 500 else ""),
                "createdAt": r.get("created_at", ""),
                "sentiment": label,
                "sentimentScore": round(result.compound, 3),
            })

        tmdb_count = len(analyzed_reviews)

        user_qs = UserReview.objects.filter(tmdb_id=tmdb_id, media_type=media_type, is_public=True)
        user_stats = user_qs.aggregate(avg_rating=Avg("rating"), total=Count("id"))
        user_count = user_stats["total"] or 0
        user_avg = user_stats["avg_rating"] or 0
        user_positive = user_qs.filter(rating__gte=7).count()
        user_negative = user_qs.filter(rating__lte=4).count()
        user_neutral = user_qs.filter(rating__gt=4, rating__lt=7).count()
        user_score = (user_avg - 5) / 5 if user_avg else 0.0

        total_pos = tmdb_positive + user_positive
        total_neg = tmdb_negative + user_negative
        total_neu = tmdb_neutral + user_neutral
        total_all = tmdb_count + user_count

        if total_all > 0:
            avg_score = (tmdb_score_sum + user_score * user_count) / total_all
        else:
            avg_score = 0.0

        insights = []
        if total_all > 0:
            pct_pos = round(total_pos / total_all * 100)
            pct_neg = round(total_neg / total_all * 100)
            if pct_pos >= 70:
                insights.append(f"{pct_pos}% of reviewers responded positively.")
            elif pct_neg >= 50:
                insights.append(f"{pct_neg}% of reviewers expressed disappointment.")
            else:
                insights.append("Audience reception is mixed across reviewers.")
            if avg_score > 0.3:
                insights.append("Strong overall positive sentiment from critics and viewers.")
            elif avg_score < -0.2:
                insights.append("Reviewers highlight notable weaknesses or frustrations.")
            if tmdb_count >= 5:
                insights.append(f"Analysis based on {tmdb_count} TMDB critic reviews.")

        ai_summary = None
        if analyzed_reviews:
            try:
                from movies.recommendations_api import call_gemini_api
                snippets = "\n".join(
                    f"- [{r['sentiment'].upper()}] {r['content'][:200]}"
                    for r in analyzed_reviews[:10]
                )
                prompt = (
                    f"Here are audience reviews for a {'movie' if media_type == 'movie' else 'TV show'}. "
                    f"Write a concise 2-sentence summary of overall audience sentiment.\n\n{snippets}"
                )
                ai_summary, _ = call_gemini_api(prompt)
            except Exception:
                pass

        return Response({
            "tmdbId": tmdb_id,
            "mediaType": media_type,
            "summary": {
                "totalReviews": total_all,
                "avgScore": round(avg_score, 3),
                "distribution": {"positive": total_pos, "neutral": total_neu, "negative": total_neg},
            },
            "sources": {"tmdb": tmdb_count, "userReviews": user_count},
            "reviews": analyzed_reviews,
            "insights": insights,
            "aiSummary": ai_summary,
        })


class RatingsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tmdb_id = request.query_params.get('tmdbId')
        media_type = request.query_params.get('mediaType', 'movie')
        if not tmdb_id:
            return Response({'error': 'tmdbId required', 'code': 'VALIDATION_ERROR'}, status=400)
        reviews = UserReview.objects.filter(
            tmdb_id=tmdb_id, media_type=media_type, is_public=True
        ).select_related('user').order_by('-created_at')
        return Response([{
            'id': r.id, 'userId': r.user.id,
            'username': r.user.first_name or r.user.email.split('@')[0],
            'tmdbId': r.tmdb_id, 'mediaType': r.media_type, 'title': r.title,
            'rating': r.rating, 'review': r.review_text,
            'helpfulCount': r.helpful_count, 'createdAt': r.created_at.isoformat()
        } for r in reviews])

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)
        return self._create_rating(request)

    def _create_rating(self, request):
        data = request.data
        tmdb_id = data.get('tmdbId')
        rating = data.get('rating')
        media_type = data.get('mediaType', 'movie')
        title = data.get('title', '')
        review_text = data.get('reviewText', '')

        if not tmdb_id:
            return Response({'error': 'tmdbId is required', 'code': 'VALIDATION_ERROR'}, status=400)
        if not rating or not (1 <= float(rating) <= 10):
            return Response({'error': 'Rating must be between 1 and 10', 'code': 'VALIDATION_ERROR'}, status=400)
        if media_type not in ('movie', 'tv'):
            return Response({'error': 'mediaType must be movie or tv', 'code': 'VALIDATION_ERROR'}, status=400)

        review, created = UserReview.objects.update_or_create(
            user=request.user, tmdb_id=tmdb_id, media_type=media_type,
            defaults={
                'rating': rating, 'review_text': review_text,
                'title': title, 'poster_path': data.get('posterPath', ''),
                'is_public': True
            }
        )
        return Response({
            'id': review.id, 'tmdbId': review.tmdb_id, 'mediaType': review.media_type,
            'rating': review.rating, 'review': review.review_text, 'title': review.title,
            'createdAt': review.created_at.isoformat(), 'created': created
        })


class ManageRatingView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, review_id):
        try:
            review = UserReview.objects.select_related('user').get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Rating not found', 'code': 'NOT_FOUND'}, status=404)
        return Response({
            'id': review.id, 'tmdbId': review.tmdb_id, 'mediaType': review.media_type,
            'title': review.title, 'rating': review.rating, 'review': review.review_text,
            'isPublic': review.is_public, 'helpfulCount': review.helpful_count,
            'createdAt': review.created_at.isoformat(),
            'user': {'id': str(review.user.id), 'firstName': review.user.first_name, 'lastName': review.user.last_name}
        })

    def _require_owner(self, request, review):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)
        if review.user != request.user:
            return Response({'error': 'Not authorized', 'code': 'FORBIDDEN'}, status=403)
        return None

    def patch(self, request, review_id):
        return self._update_rating(request, review_id)

    def put(self, request, review_id):
        return self._update_rating(request, review_id)

    def _update_rating(self, request, review_id):
        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Rating not found', 'code': 'NOT_FOUND'}, status=404)
        err = self._require_owner(request, review)
        if err:
            return err
        data = request.data
        if 'rating' in data:
            r = data['rating']
            if not (1 <= float(r) <= 10):
                return Response({'error': 'Rating must be between 1 and 10', 'code': 'VALIDATION_ERROR'}, status=400)
            review.rating = r
        if 'reviewText' in data:
            review.review_text = data['reviewText']
        if 'isPublic' in data:
            review.is_public = data['isPublic']
        review.save()
        return Response({
            'success': True, 'id': review.id, 'rating': review.rating,
            'review': review.review_text, 'isPublic': review.is_public,
        })

    def delete(self, request, review_id):
        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Rating not found', 'code': 'NOT_FOUND'}, status=404)
        err = self._require_owner(request, review)
        if err:
            return err
        review.delete()
        return Response({'success': True, 'deleted': True})


class CreateRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return RatingsView()._create_rating(request)


class ReviewCommentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, review_id):
        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Review not found', 'code': 'NOT_FOUND'}, status=404)

        comments = ReviewComment.objects.filter(review=review, parent_comment__isnull=True).select_related('user')

        def serialize_comment(comment):
            replies = ReviewComment.objects.filter(parent_comment=comment).select_related('user')
            return {
                'id': comment.id,
                'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment,
                'createdAt': comment.created_at.isoformat(),
                'replies': [serialize_comment(r) for r in replies]
            }

        return Response({'comments': [serialize_comment(c) for c in comments]})

    def post(self, request, review_id):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)
        return _add_comment_to_review(request, review_id)


class AddReviewCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, review_id):
        return _add_comment_to_review(request, review_id)


def _add_comment_to_review(request, review_id):
    try:
        review = UserReview.objects.get(id=review_id)
    except UserReview.DoesNotExist:
        return Response({'error': 'Review not found', 'code': 'NOT_FOUND'}, status=404)

    data = request.data
    comment_text = (data.get('comment') or data.get('content') or '').strip()
    parent_id = data.get('parentCommentId')

    if not comment_text:
        return Response({'error': 'Comment is required', 'code': 'VALIDATION_ERROR'}, status=400)
    if len(comment_text) > 2000:
        return Response({'error': 'Comment too long', 'code': 'VALIDATION_ERROR'}, status=400)

    parent_comment = None
    if parent_id:
        try:
            parent_comment = ReviewComment.objects.get(id=parent_id)
        except ReviewComment.DoesNotExist:
            pass

    comment = ReviewComment.objects.create(
        user=request.user, review=review,
        comment=comment_text, parent_comment=parent_comment
    )

    if review.user != request.user:
        Notification.objects.create(
            user=review.user, notification_type='comment',
            message=f'{request.user.first_name or request.user.email} commented on your review',
            related_user_id=request.user.id,
            related_tmdb_id=review.tmdb_id, related_media_type=review.media_type
        )

    stats, _ = UserActivityStats.objects.get_or_create(user=request.user)
    stats.total_comments += 1
    stats.experience_points += 5
    stats.user_level = stats.calculate_level()
    stats.save()

    return Response({
        'success': True,
        'comment': {
            'id': comment.id,
            'userId': str(comment.user.id),
            'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
            'comment': comment.comment,
            'createdAt': comment.created_at.isoformat(),
        }
    })


class DeleteReviewCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, review_id, comment_id):
        try:
            comment = ReviewComment.objects.get(id=comment_id, review_id=review_id, user=request.user)
            comment.delete()
            return Response({'success': True})
        except ReviewComment.DoesNotExist:
            return Response({'error': 'Comment not found', 'code': 'NOT_FOUND'}, status=404)


class ReviewAwardsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, review_id):
        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Review not found', 'code': 'NOT_FOUND'}, status=404)

        awards = ReviewAward.objects.filter(review=review).select_related('user')
        award_counts = awards.values('award_type').annotate(count=Count('id'))

        return Response({
            'awards': [{
                'id': a.id, 'awardType': a.award_type,
                'userId': str(a.user.id),
                'userName': f"{a.user.first_name} {a.user.last_name}".strip() or a.user.email,
                'createdAt': a.created_at.isoformat(),
            } for a in awards],
            'counts': {item['award_type']: item['count'] for item in award_counts}
        })

    def post(self, request, review_id):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)

        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Review not found', 'code': 'NOT_FOUND'}, status=404)

        if review.user == request.user:
            return Response({'error': 'Cannot give awards to your own review', 'code': 'VALIDATION_ERROR'}, status=400)

        award_type = request.data.get('awardType', '').lower()
        valid_types = ['outstanding', 'perfect', 'great', 'helpful', 'insightful', 'funny']
        if award_type not in valid_types:
            return Response({'error': f'Invalid award type. Must be one of: {", ".join(valid_types)}', 'code': 'VALIDATION_ERROR'}, status=400)

        award, created = ReviewAward.objects.get_or_create(
            user=request.user, review=review, award_type=award_type
        )

        if created and review.user != request.user:
            Notification.objects.create(
                user=review.user, notification_type='like',
                message=f'{request.user.first_name or request.user.email} gave your review a "{award_type}" award',
                related_user_id=request.user.id,
                related_tmdb_id=review.tmdb_id, related_media_type=review.media_type
            )

        return Response({
            'success': True, 'created': created,
            'award': {'id': award.id, 'awardType': award.award_type, 'createdAt': award.created_at.isoformat()}
        })


class DeleteReviewAwardView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, review_id, award_id):
        try:
            award = ReviewAward.objects.get(id=award_id, review_id=review_id, user=request.user)
            award.delete()
            return Response({'success': True})
        except ReviewAward.DoesNotExist:
            return Response({'error': 'Award not found', 'code': 'NOT_FOUND'}, status=404)


class UserAwardsForReviewView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, review_id):
        try:
            review = UserReview.objects.get(id=review_id)
        except UserReview.DoesNotExist:
            return Response({'error': 'Review not found', 'code': 'NOT_FOUND'}, status=404)

        if not request.user.is_authenticated:
            return Response({'userAwards': []})

        user_awards = ReviewAward.objects.filter(review=review, user=request.user)
        return Response({'userAwards': [a.award_type for a in user_awards]})


class TopReviewsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        sort_by = request.query_params.get('sortBy', 'awards')
        reviews = UserReview.objects.filter(is_public=True).select_related('user')

        if sort_by == 'awards':
            reviews = reviews.annotate(award_count=Count('awards')).order_by('-award_count', '-created_at')
        elif sort_by == 'helpful':
            reviews = reviews.order_by('-helpful_count', '-created_at')
        else:
            reviews = reviews.order_by('-created_at')

        paginated_reviews, pagination = paginate_queryset(request, reviews)

        return Response({
            'reviews': [{
                'id': r.id, 'userId': str(r.user.id),
                'userName': r.user.first_name or r.user.email,
                'tmdbId': r.tmdb_id, 'mediaType': r.media_type,
                'title': r.title, 'posterPath': r.poster_path,
                'rating': r.rating, 'review': r.review_text,
                'helpfulCount': r.helpful_count,
                'awardCount': getattr(r, 'award_count', r.awards.count()),
                'createdAt': r.created_at.isoformat(),
            } for r in paginated_reviews],
            **pagination
        })


class SubmitRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id=None):
        data = request.data
        for_tmdb_id = data.get('forTmdbId')
        recommended_tmdb_id = data.get('recommendedTmdbId')

        if not for_tmdb_id or not recommended_tmdb_id:
            return Response({'error': 'forTmdbId and recommendedTmdbId are required', 'code': 'VALIDATION_ERROR'}, status=400)

        for_media_type = data.get('forMediaType', 'movie')
        recommended_media_type = data.get('recommendedMediaType', 'movie')
        if for_media_type not in ('movie', 'tv') or recommended_media_type not in ('movie', 'tv'):
            return Response({'error': 'mediaType must be movie or tv', 'code': 'VALIDATION_ERROR'}, status=400)

        rec = UserRecommendation.objects.create(
            user=request.user,
            for_tmdb_id=for_tmdb_id, for_media_type=for_media_type,
            recommended_tmdb_id=recommended_tmdb_id, recommended_media_type=recommended_media_type,
            recommended_title=data.get('recommendedTitle', ''),
            recommended_poster_path=data.get('recommendedPosterPath', ''),
            reason=data.get('reason', '')
        )

        stats, _ = UserActivityStats.objects.get_or_create(user=request.user)
        stats.experience_points += 15
        stats.user_level = stats.calculate_level()
        stats.save()

        return Response({
            'success': True,
            'recommendation': {
                'id': rec.id, 'forTmdbId': rec.for_tmdb_id,
                'recommendedTmdbId': rec.recommended_tmdb_id,
                'recommendedTitle': rec.recommended_title,
                'reason': rec.reason, 'createdAt': rec.created_at.isoformat(),
            }
        })


class UserRecommendationsForContentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, tmdb_id, media_type):
        current_user = request.user if request.user.is_authenticated else None

        recs = UserRecommendation.objects.filter(
            for_tmdb_id=tmdb_id, for_media_type=media_type
        ).select_related('user').annotate(
            like_count_db=Count('votes', filter=Q(votes__vote_type='like')),
            dislike_count_db=Count('votes', filter=Q(votes__vote_type='dislike'))
        ).order_by('-like_count_db', 'dislike_count_db', '-created_at')[:20]

        result = []
        for r in recs:
            user_vote = None
            if current_user:
                try:
                    vote = RecommendationVote.objects.get(recommendation=r, user=current_user)
                    user_vote = vote.vote_type
                except RecommendationVote.DoesNotExist:
                    pass
            result.append({
                'id': r.id, 'userId': str(r.user.id),
                'userName': f"{r.user.first_name} {r.user.last_name}".strip() or r.user.email,
                'recommendedTmdbId': r.recommended_tmdb_id,
                'recommendedMediaType': r.recommended_media_type,
                'recommendedTitle': r.recommended_title,
                'recommendedPosterPath': r.recommended_poster_path,
                'reason': r.reason,
                'likeCount': r.votes.filter(vote_type='like').count(),
                'dislikeCount': r.votes.filter(vote_type='dislike').count(),
                'userVote': user_vote,
                'createdAt': r.created_at.isoformat(),
            })

        return Response({'recommendations': result})


class VoteOnRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, recommendation_id):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        vote_type = request.data.get('voteType', '').lower()
        if vote_type not in ['like', 'dislike']:
            return Response({'error': 'voteType must be "like" or "dislike"', 'code': 'VALIDATION_ERROR'}, status=400)

        vote, created = RecommendationVote.objects.update_or_create(
            user=request.user, recommendation=rec,
            defaults={'vote_type': vote_type}
        )
        return Response({'success': True, 'created': created, 'voteType': vote.vote_type})


class DeleteUserRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, recommendation_id):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id, user=request.user)
            rec.delete()
            return Response({'success': True})
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)


class UserRecommendationCommentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id=None, recommendation_id=None):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        comments = RecommendationComment.objects.filter(recommendation=rec).select_related('user')
        return Response({
            'comments': [{
                'id': c.id, 'userId': str(c.user.id),
                'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
                'comment': c.comment, 'createdAt': c.created_at.isoformat(),
            } for c in comments]
        })

    def post(self, request, user_id=None, recommendation_id=None):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}, status=401)

        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        comment_text = (request.data.get('comment') or request.data.get('content') or '').strip()
        if not comment_text:
            return Response({'error': 'Comment is required', 'code': 'VALIDATION_ERROR'}, status=400)

        comment = RecommendationComment.objects.create(
            user=request.user, recommendation=rec, comment=comment_text
        )
        return Response({
            'success': True,
            'comment': {
                'id': comment.id, 'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment, 'createdAt': comment.created_at.isoformat(),
            }
        })


class UserRecommendationVoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, recommendation_id):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        vote_type = request.data.get('voteType', '').lower()
        if vote_type not in ['like', 'dislike']:
            return Response({'error': 'voteType must be "like" or "dislike"', 'code': 'VALIDATION_ERROR'}, status=400)

        vote, created = RecommendationVote.objects.update_or_create(
            user=request.user, recommendation=rec,
            defaults={'vote_type': vote_type}
        )
        return Response({'success': True, 'created': created, 'voteType': vote.vote_type})


class RecommendationCommentsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, recommendation_id):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        comments = RecommendationComment.objects.filter(recommendation=rec).select_related('user')
        return Response({
            'comments': [{
                'id': c.id, 'userId': str(c.user.id),
                'userName': f"{c.user.first_name} {c.user.last_name}".strip() or c.user.email,
                'comment': c.comment, 'createdAt': c.created_at.isoformat(),
            } for c in comments]
        })


class AddRecommendationCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, recommendation_id):
        try:
            rec = UserRecommendation.objects.get(id=recommendation_id)
        except UserRecommendation.DoesNotExist:
            return Response({'error': 'Recommendation not found', 'code': 'NOT_FOUND'}, status=404)

        comment_text = (request.data.get('comment') or request.data.get('content') or '').strip()
        if not comment_text:
            return Response({'error': 'Comment is required', 'code': 'VALIDATION_ERROR'}, status=400)

        comment = RecommendationComment.objects.create(
            user=request.user, recommendation=rec, comment=comment_text
        )
        return Response({
            'success': True,
            'comment': {
                'id': comment.id, 'userId': str(comment.user.id),
                'userName': f"{comment.user.first_name} {comment.user.last_name}".strip() or comment.user.email,
                'comment': comment.comment, 'createdAt': comment.created_at.isoformat(),
            }
        })
