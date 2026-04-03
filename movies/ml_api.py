"""
ML Recommendation API endpoints
Provides Python-based ML recommendation services
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    UserReview, ViewingHistory, UserWatchlist, UserFavorites,
    Recommendation, RecommendationMetrics, FeatureContribution
)


def _fetch_tmdb_metadata(tmdb_id, media_type='movie'):
    """Fetch a single movie/tv item's metadata from TMDB."""
    try:
        from . import api as tmdb_api
        endpoint = f"/{media_type}/{tmdb_id}"
        data = tmdb_api.tmdb_request(endpoint)
        if data and 'id' in data:
            return tmdb_id, data
        # Try the other type if first fails
        alt = 'tv' if media_type == 'movie' else 'movie'
        data = tmdb_api.tmdb_request(f"/{alt}/{tmdb_id}")
        if data and 'id' in data:
            return tmdb_id, {**data, '_resolved_type': alt}
    except Exception:
        pass
    return tmdb_id, None


def enrich_recommendations_with_tmdb(recommendations, default_media_type='movie', max_workers=8):
    """
    Given a list of recommendation dicts with at least 'tmdb_id', fetch
    TMDB metadata for each and merge title, poster_path, overview, etc.
    Items whose metadata cannot be fetched are dropped from the result.
    """
    if not recommendations:
        return recommendations

    # Build a map from tmdb_id → rec dict
    id_to_rec = {r['tmdb_id']: r for r in recommendations}
    ids = list(id_to_rec.keys())

    enriched = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(ids))) as executor:
        futures = {
            executor.submit(_fetch_tmdb_metadata, tmdb_id, id_to_rec[tmdb_id].get('media_type', default_media_type)): tmdb_id
            for tmdb_id in ids
        }
        for future in as_completed(futures):
            tmdb_id, meta = future.result()
            if not meta:
                continue
            rec = dict(id_to_rec[tmdb_id])
            resolved_type = meta.pop('_resolved_type', None) or rec.get('media_type', default_media_type)
            rec['media_type'] = resolved_type
            rec['title'] = meta.get('title') or meta.get('name', '')
            rec['poster_path'] = meta.get('poster_path')
            rec['backdrop_path'] = meta.get('backdrop_path')
            rec['overview'] = meta.get('overview', '')
            rec['vote_average'] = round(meta.get('vote_average', 0), 1)
            rec['vote_count'] = meta.get('vote_count', 0)
            rec['release_date'] = meta.get('release_date') or meta.get('first_air_date', '')
            rec['genre_ids'] = [g['id'] for g in meta.get('genres', [])] or meta.get('genre_ids', [])
            rec['popularity'] = meta.get('popularity', 0)
            rec['runtime'] = meta.get('runtime')
            rec['number_of_seasons'] = meta.get('number_of_seasons')
            enriched[tmdb_id] = rec

    # Preserve original ordering, skip items without metadata
    return [enriched[r['tmdb_id']] for r in recommendations if r['tmdb_id'] in enriched]


@require_GET
def get_hybrid_recommendations(request, user_id):
    """Get hybrid recommendations combining collaborative and content-based filtering"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        from .ml.recommendation_engine import hybrid_recommender, recommendation_engine
        
        try:
            recommendation_engine.build_user_item_matrix(None)
            recommendations = hybrid_recommender.get_recommendations(user_id, limit)
        except Exception as e:
            recommendations = []
        
        if not recommendations:
            from . import api
            trending = api.tmdb_request("/trending/all/week")
            if 'results' in trending:
                recommendations = [
                    {
                        'tmdb_id': item['id'],
                        'media_type': item.get('media_type', 'movie'),
                        'title': item.get('title') or item.get('name', ''),
                        'poster_path': item.get('poster_path'),
                        'backdrop_path': item.get('backdrop_path'),
                        'overview': item.get('overview', ''),
                        'vote_average': round(item.get('vote_average', 0), 1),
                        'release_date': item.get('release_date') or item.get('first_air_date', ''),
                        'genre_ids': item.get('genre_ids', []),
                        'score': item.get('vote_average', 7.0) / 10,
                        'type': 'trending',
                        'reason': 'Trending this week'
                    }
                    for item in trending['results'][:limit]
                ]
        else:
            # Enrich ML-generated recommendations with TMDB metadata
            recommendations = enrich_recommendations_with_tmdb(recommendations)

        return JsonResponse({
            "user_id": user_id,
            "recommendations": recommendations,
            "type": "hybrid",
            "count": len(recommendations)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_collaborative_recommendations(request, user_id):
    """Get recommendations using collaborative filtering"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        from .ml.recommendation_engine import recommendation_engine
        
        try:
            recommendation_engine.build_user_item_matrix(None)
            recommendation_engine.compute_user_similarity()
            raw_recs = recommendation_engine.get_collaborative_recommendations(user_id, limit)
            
            raw_list = [
                {
                    'tmdb_id': tmdb_id,
                    'predicted_rating': round(score, 2),
                    'score': round(score / 5, 4),
                    'type': 'collaborative',
                    'reason': 'Users with similar taste loved this'
                }
                for tmdb_id, score in raw_recs
            ]
            recommendations = enrich_recommendations_with_tmdb(raw_list)
        except Exception as e:
            recommendations = []

        return JsonResponse({
            "user_id": user_id,
            "recommendations": recommendations,
            "type": "collaborative",
            "count": len(recommendations)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_similar_items(request, tmdb_id):
    """Get similar items using item-based collaborative filtering"""
    try:
        limit = min(int(request.GET.get('limit', 10)), 50)
        media_type = request.GET.get('media_type', 'movie')
        
        from .ml.recommendation_engine import recommendation_engine
        
        try:
            recommendation_engine.build_user_item_matrix(None)
            recommendation_engine.compute_item_similarity()
            similar = recommendation_engine.get_similar_items(tmdb_id, limit)
            
            similar_items = [
                {
                    'tmdb_id': item_id,
                    'similarity_score': round(score, 3),
                    'type': 'item_similarity'
                }
                for item_id, score in similar
            ]
        except Exception as e:
            similar_items = []
        
        if not similar_items:
            from . import api
            endpoint = f"/{media_type}/{tmdb_id}/similar"
            result = api.tmdb_request(endpoint)
            if 'results' in result:
                similar_items = [
                    {
                        'tmdb_id': item['id'],
                        'title': item.get('title') or item.get('name', ''),
                        'poster_path': item.get('poster_path'),
                        'similarity_score': item.get('vote_average', 7.0) / 10,
                        'type': 'tmdb_similar'
                    }
                    for item in result['results'][:limit]
                ]
        
        return JsonResponse({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "similar_items": similar_items,
            "count": len(similar_items)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_user_similarity(request, user_id):
    """Find users with similar taste"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        from .ml.recommendation_engine import recommendation_engine
        import numpy as np
        
        try:
            recommendation_engine.build_user_item_matrix(None)
            recommendation_engine.compute_user_similarity()
            
            if user_id in recommendation_engine.user_id_to_idx:
                user_idx = recommendation_engine.user_id_to_idx[user_id]
                similarities = recommendation_engine.user_similarity_matrix[user_idx]
                
                similar_indices = np.argsort(similarities)[::-1][1:limit+1]
                
                similar_users = []
                for idx in similar_indices:
                    similar_user_id = recommendation_engine.idx_to_user_id[idx]
                    try:
                        similar_user = User.objects.get(id=similar_user_id)
                        similar_users.append({
                            'user_id': similar_user_id,
                            'username': similar_user.username,
                            'similarity_score': round(float(similarities[idx]), 3)
                        })
                    except User.DoesNotExist:
                        continue
            else:
                similar_users = []
                
        except Exception as e:
            similar_users = []
        
        return JsonResponse({
            "user_id": user_id,
            "similar_users": similar_users,
            "count": len(similar_users)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def semantic_search(request):
    """Semantic search for movies/TV shows with TF-IDF similarity scores"""
    if request.method not in ['POST', 'GET']:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    import time
    start_time = time.time()
    
    try:
        if request.method == 'POST':
            body = json.loads(request.body)
            query = body.get('query', '')
            limit = min(body.get('limit', 20), 100)
            filters = body.get('filters', {})
        else:
            query = request.GET.get('query', '')
            try:
                limit = min(int(request.GET.get('limit', 20)), 100)
            except ValueError:
                limit = 20
            filters = {}
        
        if not query:
            return JsonResponse({"error": "query is required"}, status=400)
        from .ml.pinecone_service import pinecone_service
        if pinecone_service.is_initialized():
            pinecone_results = pinecone_service.search(query, k=limit)
            if pinecone_results:
                formatted_results = []
                for item in pinecone_results:
                    formatted_results.append({
                        'tmdbId': item.get('id'),
                        'title': item.get('title'),
                        'overview': item.get('overview'),
                        'posterPath': item.get('poster_path'),
                        'releaseDate': item.get('release_date'),
                        'voteAverage': item.get('vote_average'),
                        'genres': [],
                        'mediaType': 'movie',
                        'similarity': item.get('similarity'),
                        'explanation': item.get('explanation')
                    })

                # Enrich all items from TMDB to get complete metadata
                from . import api as tmdb_api
                import concurrent.futures

                def fetch_tmdb_full(idx):
                    tmdb_id = formatted_results[idx].get('tmdbId')
                    if not tmdb_id:
                        return idx, {}
                    try:
                        detail = tmdb_api.tmdb_request(f'/movie/{tmdb_id}')
                        return idx, detail
                    except Exception:
                        return idx, {}

                needs_enrich = [i for i, r in enumerate(formatted_results)
                                if not r.get('posterPath') or r.get('voteAverage', 0) == 0]
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    for idx, detail in executor.map(fetch_tmdb_full, needs_enrich):
                        if detail:
                            formatted_results[idx]['posterPath'] = detail.get('poster_path') or formatted_results[idx].get('posterPath', '')
                            formatted_results[idx]['voteAverage'] = detail.get('vote_average') or 0
                            formatted_results[idx]['overview'] = detail.get('overview') or formatted_results[idx].get('overview', '')
                            formatted_results[idx]['releaseDate'] = detail.get('release_date') or formatted_results[idx].get('releaseDate', '')
                            formatted_results[idx]['genres'] = [g['name'] for g in detail.get('genres', [])]

                # Filter out items with no poster
                formatted_results = [r for r in formatted_results if r.get('posterPath')]

                return JsonResponse({
                    'results': formatted_results,
                    'query': query,
                    'count': len(formatted_results)
                })

        from . import api
        from .ml.embedding_service import semantic_embedding_service
        
        params = {"query": query, "page": 1}
        
        media_types = filters.get('mediaType', [])
        if media_types and len(media_types) == 1:
            if 'movie' in media_types:
                endpoint = "/search/movie"
            elif 'tv' in media_types:
                endpoint = "/search/tv"
            else:
                endpoint = "/search/multi"
        else:
            endpoint = "/search/multi"
        
        result = api.tmdb_request(endpoint, params)
        
        if 'results' in result:
            raw_results = result['results'][:limit * 2]
            
            filtered_results = []
            for item in raw_results:
                item_type = item.get('media_type', 'movie')
                if item_type == 'person':
                    continue
                    
                year_range = filters.get('yearRange')
                if year_range:
                    release_date = item.get('release_date') or item.get('first_air_date', '')
                    if release_date:
                        try:
                            year = int(release_date[:4])
                            if year < year_range[0] or year > year_range[1]:
                                continue
                        except (ValueError, IndexError):
                            pass
                
                min_rating = filters.get('minRating', 0)
                max_rating = filters.get('maxRating', 10)
                vote_avg = item.get('vote_average', 0)
                if vote_avg < min_rating or vote_avg > max_rating:
                    continue
                
                filtered_results.append(item)
            
            ranked_results = semantic_embedding_service.search_with_similarity(
                query, filtered_results, top_k=limit
            )
            
            formatted_results = []
            for item, similarity in ranked_results:
                title = item.get('title') or item.get('name', '')
                overview = item.get('overview', '')
                
                query_lower = query.lower()
                title_boost = 0.15 if query_lower in title.lower() else 0
                final_similarity = min(1.0, similarity + title_boost)
                
                formatted_results.append({
                    'tmdbId': item.get('id'),
                    'title': title,
                    'overview': overview,
                    'posterPath': item.get('poster_path'),
                    'releaseDate': item.get('release_date') or item.get('first_air_date'),
                    'voteAverage': item.get('vote_average'),
                    'popularity': item.get('popularity'),
                    'genres': item.get('genre_ids', []),
                    'mediaType': item.get('media_type', 'movie'),
                    'similarity': round(final_similarity, 3),
                    'explanation': f"TF-IDF semantic match for '{query}'"
                })
            
            search_time = time.time() - start_time
            
            return JsonResponse({
                "query": query,
                "results": formatted_results,
                "totalMatches": len(formatted_results),
                "searchTime": round(search_time, 3),
                "searchMethod": "tfidf_semantic",
                "queryAnalysis": {
                    "originalQuery": query,
                    "filters": filters
                }
            })
        else:
            return JsonResponse({
                "query": query,
                "results": [],
                "totalMatches": 0,
                "searchTime": 0,
                "searchMethod": "tfidf_semantic",
                "queryAnalysis": {"originalQuery": query, "filters": filters}
            })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_recommendation_explanation(request, user_id, tmdb_id):
    """Explain why a recommendation was made for a user using the explainability engine"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        media_type = request.GET.get('media_type', 'movie')
        
        from .ml.explainability_engine import explainability_engine, ExplanationContext
        from . import api
        
        user_reviews = list(UserReview.objects.filter(user=user).values())
        user_preferences_obj = None
        
        try:
            from .models import UserPreferences
            prefs = UserPreferences.objects.filter(user=user).first()
            if prefs:
                user_preferences_obj = {
                    'preferred_genres': prefs.preferred_genres or [],
                    'preferred_decades': prefs.preferred_decades or [],
                    'language_preferences': prefs.language_preferences or [],
                }
        except Exception:
            pass
        
        content_details = api.tmdb_request(f"/{media_type}/{tmdb_id}")
        
        highly_rated = [r['title'] for r in user_reviews if r.get('rating', 0) >= 8][:3]
        
        context = ExplanationContext(
            user_id=str(user_id),
            tmdb_id=int(tmdb_id),
            media_type=media_type,
            user_ratings=user_reviews,
            user_preferences=user_preferences_obj,
            item_details=content_details,
            similar_movies=highly_rated
        )
        
        explanation = explainability_engine.explain_recommendation(
            user_id=str(user_id),
            tmdb_id=int(tmdb_id),
            media_type=media_type,
            context=context
        )
        
        return JsonResponse(explainability_engine.to_dict(explanation))
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_bandit_statistics(request, user_id):
    """Get contextual bandit statistics for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        from .ml.contextual_bandits import contextual_bandit_engine
        
        stats = contextual_bandit_engine.get_statistics(str(user_id))
        
        return JsonResponse({
            "user_id": user_id,
            "bandit_statistics": stats
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def select_recommendation_arm(request, user_id):
    """Select a recommendation strategy using contextual bandits"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        body = json.loads(request.body) if request.body else {}
        session_duration = body.get('session_duration', 0)
        device_type = body.get('device_type')
        mood = body.get('mood')
        
        from .ml.contextual_bandits import contextual_bandit_engine
        
        context = contextual_bandit_engine.extract_context(
            str(user_id),
            session_duration=session_duration,
            device_type=device_type,
            mood=mood
        )
        
        selection = contextual_bandit_engine.select_contextual_arm(context)
        
        experiment_id = contextual_bandit_engine.log_experiment(
            str(user_id),
            selection.arm_chosen,
            context,
            selection.exploration_rate
        )
        
        return JsonResponse({
            "user_id": user_id,
            "experiment_id": experiment_id,
            "arm_chosen": selection.arm_chosen,
            "sampled_reward": round(selection.sampled_reward, 4),
            "exploration_rate": round(selection.exploration_rate, 4),
            "all_arm_scores": selection.all_arm_scores
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def update_bandit_reward(request):
    """Update bandit experiment with user feedback reward"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        experiment_id = body.get('experiment_id')
        outcome_type = body.get('outcome_type')
        
        if not experiment_id or not outcome_type:
            return JsonResponse({"error": "experiment_id and outcome_type are required"}, status=400)
        
        from .ml.contextual_bandits import contextual_bandit_engine, RewardFeedback
        
        reward = contextual_bandit_engine.calculate_reward(outcome_type)
        
        feedback = RewardFeedback(
            experiment_id=experiment_id,
            reward=reward,
            outcome_type=outcome_type
        )
        
        contextual_bandit_engine.update_reward(feedback)
        
        return JsonResponse({
            "experiment_id": experiment_id,
            "outcome_type": outcome_type,
            "calculated_reward": round(reward, 3),
            "status": "updated"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def apply_diversity(request):
    """Apply diversity algorithms to a list of recommendations"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        candidates = body.get('candidates', [])
        config = body.get('config', {})
        user_genre_preferences = body.get('user_genre_preferences', [])
        
        if not candidates:
            return JsonResponse({"error": "candidates is required"}, status=400)
        
        from .ml.diversity_engine import diversity_engine, DiversityCandidate, DiversityConfig
        
        diversity_config = DiversityConfig(
            lambda_param=config.get('lambda', 0.7),
            epsilon_exploration=config.get('epsilon_exploration', 0.1),
            max_consecutive_same_genre=config.get('max_consecutive_same_genre', 3),
            serendipity_rate=config.get('serendipity_rate', 0.15),
            diversity_metric=config.get('diversity_metric', 'mmr')
        )
        
        diversity_candidates = [
            DiversityCandidate(
                id=str(c.get('id', c.get('tmdb_id'))),
                tmdb_id=c.get('tmdb_id'),
                media_type=c.get('media_type', 'movie'),
                score=c.get('score', 0.5),
                genres=c.get('genres', []),
                embeddings=c.get('embeddings'),
                metadata=c.get('metadata')
            )
            for c in candidates
        ]
        
        diversified = diversity_engine.apply_diversity(
            diversity_candidates,
            diversity_config,
            user_genre_preferences
        )
        
        metrics = diversity_engine.calculate_metrics(diversified, user_genre_preferences)
        
        # Build a lookup map from the original candidates to restore metadata
        candidate_meta = {str(c.get('id', c.get('tmdb_id'))): c for c in candidates}

        return JsonResponse({
            "diversified_results": [
                {
                    **candidate_meta.get(c.id, {}),
                    "id": c.id,
                    "tmdb_id": c.tmdb_id,
                    "media_type": c.media_type,
                    "score": round(c.score, 4),
                    "genres": c.genres,
                }
                for c in diversified
            ],
            "metrics": {
                "intra_diversity": round(metrics.intra_diversity, 4),
                "genre_balance": round(metrics.genre_balance, 4),
                "serendipity_score": round(metrics.serendipity_score, 4),
                "exploration_rate": round(metrics.exploration_rate, 4),
                "coverage_score": round(metrics.coverage_score, 4)
            },
            "count": len(diversified)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_diversity_metrics(request, user_id):
    """Get diversity metrics for a user's recommendation history"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        from .ml.diversity_engine import diversity_engine, DiversityCandidate
        from .models import UserPreferences
        
        history = ViewingHistory.objects.filter(user=user).order_by('-watched_at')[:50]
        
        if not history:
            return JsonResponse({
                "user_id": user_id,
                "metrics": None,
                "message": "No viewing history found"
            })
        
        candidates = []
        for item in history:
            candidates.append(DiversityCandidate(
                id=str(item.tmdb_id),
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                score=1.0,
                genres=[]
            ))
        
        prefs = UserPreferences.objects.filter(user=user).first()
        user_genre_preferences = prefs.preferred_genres if prefs else []
        
        metrics = diversity_engine.calculate_metrics(candidates, user_genre_preferences)
        
        return JsonResponse({
            "user_id": user_id,
            "metrics": {
                "intra_diversity": round(metrics.intra_diversity, 4),
                "genre_balance": round(metrics.genre_balance, 4),
                "serendipity_score": round(metrics.serendipity_score, 4),
                "exploration_rate": round(metrics.exploration_rate, 4),
                "coverage_score": round(metrics.coverage_score, 4)
            },
            "history_count": len(candidates)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_sentiment_analytics(request, tmdb_id):
    """Get sentiment analytics for a movie/TV show"""
    try:
        media_type = request.GET.get('media_type', 'movie')
        
        from .models import SentimentAnalytics
        
        analytics = SentimentAnalytics.objects.filter(
            tmdb_id=tmdb_id,
            media_type=media_type
        ).first()
        
        if not analytics:
            return JsonResponse({
                "tmdb_id": tmdb_id,
                "media_type": media_type,
                "analytics": None,
                "message": "No sentiment analytics found. Trigger an update first."
            })
        
        return JsonResponse({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "analytics": {
                "avg_sentiment_score": round(analytics.avg_sentiment_score, 4),
                "total_reviews": analytics.total_reviews,
                "positive_count": analytics.positive_count,
                "negative_count": analytics.negative_count,
                "neutral_count": analytics.neutral_count,
                "last_updated": analytics.last_updated.isoformat() if analytics.last_updated else None
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def analyze_text_sentiment(request):
    """Analyze sentiment of arbitrary text"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        text = body.get('text', '')
        
        if not text:
            return JsonResponse({"error": "text is required"}, status=400)
        
        from .ml.sentiment_analyzer import sentiment_analyzer
        
        result = sentiment_analyzer.analyze_text(text)
        
        return JsonResponse({
            "text": text[:200] + "..." if len(text) > 200 else text,
            "sentiment": {
                "score": round(result.score, 4),
                "classification": result.classification,
                "compound": round(result.compound, 4),
                "positive": round(result.positive, 4),
                "negative": round(result.negative, 4),
                "neutral": round(result.neutral, 4)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def update_sentiment_for_content(request, tmdb_id):
    """Trigger sentiment recalculation for a movie/TV show"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body) if request.body else {}
        media_type = body.get('media_type', 'movie')
        
        from .ml.sentiment_analyzer import sentiment_analyzer
        
        result = sentiment_analyzer.update_sentiment_analytics(tmdb_id, media_type)
        
        return JsonResponse({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "result": result
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_recommendation_history(request, user_id):
    """Get recommendation history for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        limit = min(int(request.GET.get('limit', 50)), 200)
        offset = int(request.GET.get('offset', 0))
        include_metrics = request.GET.get('include_metrics', 'true').lower() == 'true'
        
        recommendations = Recommendation.objects.filter(user=user).order_by('-created_at')[offset:offset+limit]
        
        history = []
        for rec in recommendations:
            rec_data = {
                'id': rec.id,
                'tmdb_id': rec.tmdb_id,
                'media_type': rec.media_type,
                'title': rec.title,
                'poster_path': rec.poster_path,
                'recommendation_type': rec.recommendation_type,
                'reason': rec.reason,
                'confidence': round(rec.confidence, 4) if rec.confidence else None,
                'relevance_score': round(rec.relevance_score, 4) if rec.relevance_score else None,
                'user_interacted': rec.user_interacted,
                'user_feedback': rec.user_feedback,
                'ai_explanation': rec.ai_explanation,
                'created_at': rec.created_at.isoformat() if rec.created_at else None,
                'updated_at': rec.updated_at.isoformat() if rec.updated_at else None,
            }
            
            if include_metrics:
                metrics = RecommendationMetrics.objects.filter(recommendation=rec).first()
                if metrics:
                    rec_data['metrics'] = {
                        'clicked_at': metrics.clicked_at.isoformat() if metrics.clicked_at else None,
                        'view_duration': metrics.view_duration,
                        'added_to_watchlist': metrics.added_to_watchlist,
                        'added_to_watchlist_at': metrics.added_to_watchlist_at.isoformat() if metrics.added_to_watchlist_at else None,
                        'actually_watched': metrics.actually_watched,
                        'watched_at': metrics.watched_at.isoformat() if metrics.watched_at else None,
                        'user_rating': metrics.user_rating,
                        'effectiveness_score': round(metrics.effectiveness_score, 4) if metrics.effectiveness_score else None,
                    }
                else:
                    rec_data['metrics'] = None
            
            history.append(rec_data)
        
        total_count = Recommendation.objects.filter(user=user).count()
        
        return JsonResponse({
            "user_id": user_id,
            "recommendations": history,
            "count": len(history),
            "total_count": total_count,
            "offset": offset,
            "limit": limit
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def log_recommendation_interaction(request):
    """Log recommendation interaction (clicked, watchlisted, rated_high, ignored, dismissed)"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        recommendation_id = body.get('recommendation_id')
        user_id = body.get('user_id')
        interaction_type = body.get('interaction_type')
        
        if not recommendation_id:
            return JsonResponse({"error": "recommendation_id is required"}, status=400)
        if not user_id:
            return JsonResponse({"error": "user_id is required"}, status=400)
        if not interaction_type:
            return JsonResponse({"error": "interaction_type is required"}, status=400)
        
        valid_interaction_types = ['clicked', 'watchlisted', 'rated_high', 'ignored', 'dismissed']
        if interaction_type not in valid_interaction_types:
            return JsonResponse({
                "error": f"Invalid interaction_type. Must be one of: {', '.join(valid_interaction_types)}"
            }, status=400)
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        recommendation = Recommendation.objects.filter(id=recommendation_id).first()
        if not recommendation:
            return JsonResponse({"error": "Recommendation not found"}, status=404)
        
        if recommendation.user_id != user.id:
            return JsonResponse({"error": "Recommendation does not belong to this user"}, status=403)
        
        recommendation.user_interacted = True
        
        feedback_mapping = {
            'clicked': None,
            'watchlisted': 'liked',
            'rated_high': 'liked',
            'ignored': 'not_interested',
            'dismissed': 'disliked'
        }
        if feedback_mapping.get(interaction_type):
            recommendation.user_feedback = feedback_mapping[interaction_type]
        
        recommendation.save()
        
        metrics, created = RecommendationMetrics.objects.get_or_create(
            recommendation=recommendation,
            user=user
        )
        
        now = timezone.now()
        
        if interaction_type == 'clicked':
            metrics.clicked_at = now
        elif interaction_type == 'watchlisted':
            metrics.added_to_watchlist = True
            metrics.added_to_watchlist_at = now
        elif interaction_type == 'rated_high':
            metrics.user_rating = body.get('rating', 8)
            metrics.actually_watched = True
            metrics.watched_at = now
        
        effectiveness_scores = {
            'clicked': 0.3,
            'watchlisted': 0.6,
            'rated_high': 1.0,
            'ignored': 0.1,
            'dismissed': 0.0
        }
        metrics.effectiveness_score = effectiveness_scores.get(interaction_type, 0.0)
        metrics.save()
        
        FeatureContribution.objects.update_or_create(
            recommendation=recommendation,
            user=user,
            feature_name='interaction_outcome',
            defaults={
                'contribution_score': metrics.effectiveness_score,
                'was_successful': interaction_type in ['watchlisted', 'rated_high'],
                'outcome_type': interaction_type
            }
        )
        
        bandit_result = None
        try:
            from .ml.contextual_bandits import contextual_bandit_engine, RewardFeedback
            
            reward = contextual_bandit_engine.calculate_reward(interaction_type)
            
            experiment_id = f"rec_{recommendation_id}_{user_id}"
            
            feedback = RewardFeedback(
                experiment_id=experiment_id,
                reward=reward,
                outcome_type=interaction_type
            )
            
            contextual_bandit_engine.update_reward(feedback)
            bandit_result = {
                "experiment_id": experiment_id,
                "reward": round(reward, 3),
                "status": "updated"
            }
        except Exception as e:
            bandit_result = {"error": str(e), "status": "skipped"}
        
        return JsonResponse({
            "recommendation_id": recommendation_id,
            "user_id": user_id,
            "interaction_type": interaction_type,
            "user_feedback": recommendation.user_feedback,
            "metrics_created": created,
            "effectiveness_score": metrics.effectiveness_score,
            "bandit_update": bandit_result,
            "status": "logged"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_global_feature_importance(request):
    """Get global feature importance scores across all recommendations"""
    try:
        user_id = request.GET.get('user_id')
        
        from .ml.explainability_engine import explainability_engine
        
        result = explainability_engine.get_feature_importance(user_id)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_counterfactual_explanation(request, user_id, tmdb_id):
    """Get counterfactual explanation for why an alternative was not recommended"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        alternative_tmdb_id = request.GET.get('alternative_tmdb_id')
        if not alternative_tmdb_id:
            return JsonResponse({"error": "alternative_tmdb_id query parameter is required"}, status=400)
        
        try:
            alternative_tmdb_id = int(alternative_tmdb_id)
        except ValueError:
            return JsonResponse({"error": "alternative_tmdb_id must be a valid integer"}, status=400)
        
        media_type = request.GET.get('media_type', 'movie')
        
        from .ml.explainability_engine import explainability_engine
        
        result = explainability_engine.get_counterfactual_explanation(
            user_id=str(user_id),
            current_tmdb_id=tmdb_id,
            alternative_tmdb_id=alternative_tmdb_id,
            media_type=media_type
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_local_explanation(request, user_id, tmdb_id):
    """Get local explanation using permutation importance for an individual recommendation"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        media_type = request.GET.get('media_type', 'movie')
        num_permutations = min(int(request.GET.get('num_permutations', 10)), 50)
        
        from .ml.explainability_engine import explainability_engine
        
        result = explainability_engine.get_local_explanation(
            user_id=str(user_id),
            tmdb_id=tmdb_id,
            media_type=media_type,
            num_permutations=num_permutations
        )
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def calibrate_confidence(request):
    """Calibrate confidence scores based on historical accuracy"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body) if request.body else {}
        user_id = body.get('user_id')
        min_samples = body.get('min_samples', 10)
        
        from .ml.explainability_engine import explainability_engine
        
        result = explainability_engine.calibrate_confidence(
            user_id=str(user_id) if user_id else None,
            min_samples=min_samples
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_viewing_patterns(request, user_id):
    """Get viewing pattern analysis for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        from .ml.pattern_recognition import viewing_pattern_analyzer
        
        pattern_summary = viewing_pattern_analyzer.get_pattern_summary(user_id)
        result = viewing_pattern_analyzer.to_dict(pattern_summary)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def get_similar_movies_semantic(request, tmdb_id):
    """Get semantically similar movies using vector search (Pinecone) with TMDB fallback."""
    try:
        limit = min(int(request.GET.get('limit', 10)), 50)
        media_type = request.GET.get('media_type', 'movie')

        import concurrent.futures
        from . import api as tmdb_api

        def enrich_and_filter(items):
            """Fetch full TMDB metadata for all items, then remove those without a poster."""
            def fetch_detail(idx):
                item = items[idx]
                try:
                    detail = tmdb_api.tmdb_request(f"/{media_type}/{item['tmdb_id']}")
                    return idx, detail
                except Exception:
                    return idx, {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                for idx, detail in executor.map(fetch_detail, range(len(items))):
                    if detail:
                        items[idx]['poster_path'] = detail.get('poster_path') or items[idx].get('poster_path', '')
                        items[idx]['overview'] = detail.get('overview') or ''
                        items[idx]['vote_average'] = detail.get('vote_average') or 0
                        items[idx]['release_date'] = detail.get('release_date') or detail.get('first_air_date') or ''
                        items[idx]['genres'] = [g['name'] for g in detail.get('genres', [])]

            return [item for item in items if item.get('poster_path')]

        similar_items = []
        SIMILARITY_THRESHOLD = 0.70  # min acceptable Pinecone quality

        # 1. Try Pinecone vector search — only use if top result quality is high enough
        try:
            from .ml.pinecone_service import pinecone_service
            results = pinecone_service.get_nearest_neighbors(int(tmdb_id), k=limit + 5)
            if results:
                top_score = results[0].get('similarity', 0.0) if results else 0.0
                if top_score >= SIMILARITY_THRESHOLD:
                    similar_items = [
                        {
                            'tmdb_id': r.get('id'),
                            'title': r.get('title', ''),
                            'poster_path': r.get('poster_path') or '',
                            'similarity_score': round(r.get('similarity', 0.0), 3),
                            'media_type': media_type,
                            'type': 'semantic_vector',
                            'explanation': r.get('explanation', ''),
                        }
                        for r in results if str(r.get('id')) != str(tmdb_id)
                    ][:limit]
                    similar_items = enrich_and_filter(similar_items)
                else:
                    print(f"Pinecone quality too low for {tmdb_id} (top={top_score:.2f}), using TMDB fallback")
        except Exception as e:
            print(f"Pinecone search error: {e}")

        # 2. Fallback: TMDB recommendations (better quality than /similar for popular films)
        if not similar_items:
            try:
                rec_result = tmdb_api.tmdb_request(f"/{media_type}/{tmdb_id}/recommendations")
                rec_items = rec_result.get('results', [])[:limit + 5]
                if rec_items:
                    similar_items = [
                        {
                            'tmdb_id': item['id'],
                            'title': item.get('title') or item.get('name', ''),
                            'poster_path': item.get('poster_path') or '',
                            'overview': item.get('overview') or '',
                            'vote_average': item.get('vote_average') or 0,
                            'release_date': item.get('release_date') or item.get('first_air_date') or '',
                            'genre_ids': item.get('genre_ids', []),
                            'genres': [],
                            'similarity_score': round(item.get('vote_average', 0) / 10, 3),
                            'media_type': media_type,
                            'type': 'tmdb_recommendations',
                            'explanation': 'Recommended by TMDB',
                        }
                        for item in rec_items
                        if item.get('poster_path')
                    ][:limit]
            except Exception as e:
                print(f"TMDB recommendations error: {e}")

        # 3. Last resort: TMDB /similar endpoint
        if not similar_items:
            try:
                sim_result = tmdb_api.tmdb_request(f"/{media_type}/{tmdb_id}/similar")
                sim_items = sim_result.get('results', [])[:limit + 5]
                similar_items = [
                    {
                        'tmdb_id': item['id'],
                        'title': item.get('title') or item.get('name', ''),
                        'poster_path': item.get('poster_path') or '',
                        'overview': item.get('overview') or '',
                        'vote_average': item.get('vote_average') or 0,
                        'release_date': item.get('release_date') or item.get('first_air_date') or '',
                        'genre_ids': item.get('genre_ids', []),
                        'genres': [],
                        'similarity_score': round(item.get('vote_average', 0) / 10, 3),
                        'media_type': media_type,
                        'type': 'tmdb_similar',
                        'explanation': 'Fans also watched',
                    }
                    for item in sim_items
                    if item.get('poster_path')
                ][:limit]
            except Exception as e:
                print(f"TMDB similar error: {e}")

        return JsonResponse({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "similar_items": similar_items,
            "count": len(similar_items),
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
