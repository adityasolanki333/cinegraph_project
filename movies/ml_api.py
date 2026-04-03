"""
ML Recommendation API endpoints
Provides Python-based ML recommendation services
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.models import User
from django.utils import timezone
from .validation import error_response
from .decorators import rate_limit
from .models import (
    UserReview, ViewingHistory, UserWatchlist, UserFavorites,
    Recommendation, RecommendationMetrics, FeatureContribution
)

logger = logging.getLogger(__name__)


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
            if not rec['poster_path']:
                continue  # Skip items with no poster
            vote_avg = round(meta.get('vote_average', 0), 1)
            vote_count = meta.get('vote_count', 0)
            if vote_avg < 5.5 and vote_count >= 20:
                continue  # Skip poorly rated movies with enough votes to be sure
            rec['backdrop_path'] = meta.get('backdrop_path')
            rec['overview'] = meta.get('overview', '')
            rec['vote_average'] = vote_avg
            rec['vote_count'] = vote_count
            rec['release_date'] = meta.get('release_date') or meta.get('first_air_date', '')
            rec['genre_ids'] = [g['id'] for g in meta.get('genres', [])] or meta.get('genre_ids', [])
            rec['popularity'] = meta.get('popularity', 0)
            rec['runtime'] = meta.get('runtime')
            rec['number_of_seasons'] = meta.get('number_of_seasons')
            enriched[tmdb_id] = rec

    # Preserve original ordering, skip items without metadata or poster
    return [enriched[r['tmdb_id']] for r in recommendations if r['tmdb_id'] in enriched]


@require_GET
def get_hybrid_recommendations(request, user_id):
    """
    Hybrid recommendations – bandit-driven tiered strategy:
      0. Cold-start path for new users (< 5 interactions)
      1. MovieLens item-item similarity seeded from unified signals
      2. TMDB Discover filtered by user's preferred genres (onboarding prefs)
      3. TMDB trending/popular as final fallback
    Post-processing: diversity engine (MMR + serendipity)
    """
    from datetime import datetime, date
    from . import api as tmdb_api
    from .models import UserPreferences, TmdbMovieCache

    from movies.ml.utils import GENRE_NAME_TO_ID, GENRE_MAP as GENRE_ID_TO_NAME

    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)

        limit = min(int(request.GET.get('limit', 20)), 100)
        current_year = datetime.now().year

        # ── Signal aggregator: unified implicit + explicit seeds ──────────
        from .ml.signal_aggregator import signal_aggregator
        seed_ids = signal_aggregator.get_seed_ids(user, min_score=0.2, limit=30)
        interaction_count = signal_aggregator.get_interaction_count(user)

        # ── Collect exclusion set ─────────────────────────────────────────
        reviewed_ids = set(UserReview.objects.filter(user=user).values_list('tmdb_id', flat=True))
        watchlist_ids = set(UserWatchlist.objects.filter(user=user).values_list('tmdb_id', flat=True))
        excluded_ids = reviewed_ids | watchlist_ids

        try:
            dismissed_ids = set(
                Recommendation.objects.filter(user=user, user_feedback='disliked')
                .values_list('tmdb_id', flat=True)
            )
            excluded_ids |= dismissed_ids
        except Exception:
            pass

        # User's preferred genres (set during onboarding)
        preferred_genre_ids = []
        preferred_genre_names = []
        try:
            prefs = UserPreferences.objects.get(user=user)
            preferred_genre_names = prefs.preferred_genres or []
            for gname in preferred_genre_names:
                gid = GENRE_NAME_TO_ID.get(gname)
                if gid:
                    preferred_genre_ids.append(gid)
        except UserPreferences.DoesNotExist:
            pass

        # ── Per-user learned weights from feedback loop ───────────────────
        user_weights = {}
        try:
            from .ml.feedback_service import feedback_service
            user_weights = feedback_service.get_user_weights(user)
        except Exception:
            pass

        collab_w = user_weights.get('collaborative', 0.6)
        content_w = user_weights.get('content', 0.4)
        popularity_w = user_weights.get('popularity', 0.2)
        recency_w = user_weights.get('recency', 0.15)

        def quality_score(item, movielens_sim=0.0):
            vote_avg = item.get('vote_average', 0)
            popularity = item.get('popularity', 0)
            raw_date = item.get('release_date') or item.get('first_air_date', '')
            try:
                year = int(raw_date[:4]) if raw_date else 2000
            except ValueError:
                year = 2000
            recency = max(0, 1 - (current_year - year) / 15)
            tmdb_score = (vote_avg / 10) * 0.35 + min(popularity / 300, 1) * popularity_w + recency * recency_w
            return movielens_sim * collab_w * 0.33 + tmdb_score

        # ── Bandit: select strategy ───────────────────────────────────────
        experiment_id = None
        arm_chosen = 'hybrid_ensemble'
        try:
            from .ml.contextual_bandits import contextual_bandit_engine
            ctx = contextual_bandit_engine.extract_context(
                str(user_id), session_duration=0
            )
            ctx.recent_interaction_count = interaction_count
            ctx.recent_genres = preferred_genre_names[:5]
            selection = contextual_bandit_engine.select_contextual_arm(ctx)
            arm_chosen = selection.arm_chosen
            experiment_id = contextual_bandit_engine.log_experiment(
                str(user_id), arm_chosen, ctx, selection.exploration_rate
            )
            logger.info('Bandit: selected arm "%s" for user %s', arm_chosen, user_id)
        except Exception as e:
            logger.warning('Bandit selection failed, defaulting to hybrid: %s', e)

        recommendations = []

        # ═══════════════════════════════════════════════════════════════════
        # COLD-START — users with fewer than 5 interactions
        # ═══════════════════════════════════════════════════════════════════
        if interaction_count < 5:
            logger.info('Cold-start path for user %s (%d interactions)', user_id, interaction_count)
            if preferred_genre_names:
                cached_movies = TmdbMovieCache.objects.filter(
                    vote_count__gte=50,
                    vote_average__gte=6.0,
                    poster_path__isnull=False,
                ).exclude(tmdb_id__in=excluded_ids).order_by('-popularity')[:200]

                scored = []
                for movie in cached_movies:
                    movie_genres = movie.genres or []
                    genre_names = []
                    for g in movie_genres:
                        if isinstance(g, dict):
                            genre_names.append(g.get('name', ''))
                        elif isinstance(g, str):
                            genre_names.append(g)

                    genre_overlap = len(set(genre_names) & set(preferred_genre_names))
                    if genre_overlap == 0:
                        continue

                    genre_score = genre_overlap / max(len(preferred_genre_names), 1)
                    pop_score = min(movie.popularity / 300, 1.0)
                    vote_score = movie.vote_average / 10.0
                    total = genre_score * 0.5 + vote_score * 0.3 + pop_score * 0.2

                    scored.append({
                        'tmdb_id': movie.tmdb_id,
                        'media_type': movie.media_type,
                        'title': movie.title,
                        'poster_path': movie.poster_path,
                        'backdrop_path': movie.backdrop_path,
                        'overview': movie.overview or '',
                        'vote_average': round(movie.vote_average, 1),
                        'vote_count': movie.vote_count,
                        'popularity': round(movie.popularity, 1),
                        'release_date': movie.release_date or '',
                        'genre_ids': [g.get('id') for g in movie_genres if isinstance(g, dict)] if movie_genres else [],
                        'score': round(total, 4),
                        'type': 'cold-start',
                        'reason': f'Matches your love for {", ".join(list(set(genre_names) & set(preferred_genre_names))[:2])}',
                    })

                scored.sort(key=lambda x: x['score'], reverse=True)
                recommendations = scored[:limit]
                logger.info('Cold-start: %d recs from cache for user %s', len(recommendations), user_id)

        # ═══════════════════════════════════════════════════════════════════
        # TIER 1 — MovieLens item-item similarity (if bandit picks collab/hybrid/ensemble)
        # ═══════════════════════════════════════════════════════════════════
        run_movielens = arm_chosen in ('collaborative', 'hybrid_ensemble', 'content_based')
        if seed_ids and run_movielens and len(recommendations) < limit:
            try:
                from .ml.movielens_engine import movielens_engine
                if movielens_engine.is_ready():
                    ml_pairs = movielens_engine.get_recommendations(
                        liked_tmdb_ids=seed_ids,
                        excluded_tmdb_ids=excluded_ids,
                        k=limit * 3,
                    )
                    if ml_pairs:
                        sim_map = {tmdb_id: sim for tmdb_id, sim in ml_pairs}
                        raw_recs = [
                            {'tmdb_id': tid, 'score': sim, 'type': 'movielens',
                             'reason': 'Based on movies you liked', 'media_type': 'movie'}
                            for tid, sim in ml_pairs[: limit * 3]
                        ]
                        enriched = enrich_recommendations_with_tmdb(raw_recs, max_workers=12)

                        filtered = []
                        for rec in enriched:
                            if (rec.get('poster_path')
                                    and rec.get('vote_average', 0) >= 5.5
                                    and rec.get('vote_count', 0) >= 20):
                                rec['score'] = quality_score(rec, sim_map.get(rec['tmdb_id'], 0))
                                filtered.append(rec)

                        filtered.sort(key=lambda x: x['score'], reverse=True)
                        existing_ids = {r['tmdb_id'] for r in recommendations}
                        for rec in filtered:
                            if rec['tmdb_id'] not in existing_ids and len(recommendations) < limit:
                                recommendations.append(rec)
                                existing_ids.add(rec['tmdb_id'])
                        logger.info('MovieLens: returned %d recs for user %s', len(recommendations), user_id)
            except Exception as e:
                logger.warning('MovieLens tier failed: %s', e)

        # ═══════════════════════════════════════════════════════════════════
        # TIER 2 — TMDB Discover filtered by preferred genres
        # ═══════════════════════════════════════════════════════════════════
        run_genre = arm_chosen in ('content_based', 'hybrid_ensemble', 'trending', 'exploration_random')
        if len(recommendations) < limit // 2 or (run_genre and len(recommendations) < limit):
            existing_ids = {r['tmdb_id'] for r in recommendations}
            genre_pool = {}

            genres_to_try = preferred_genre_ids[:3] if preferred_genre_ids else [28, 878, 18]
            three_years_ago = str(current_year - 3)

            discover_calls = []
            for gid in genres_to_try:
                discover_calls += [
                    ('/discover/movie', {
                        'with_genres': gid,
                        'sort_by': 'vote_average.desc',
                        'vote_count.gte': 200,
                        'primary_release_date.gte': f'{three_years_ago}-01-01',
                        'page': 1,
                    }, 'movie', f'Top-rated {GENRE_ID_TO_NAME.get(gid, "genre")} from the last 3 years'),
                    ('/discover/tv', {
                        'with_genres': gid,
                        'sort_by': 'vote_average.desc',
                        'vote_count.gte': 100,
                        'first_air_date.gte': f'{three_years_ago}-01-01',
                        'page': 1,
                    }, 'tv', f'Top-rated {GENRE_ID_TO_NAME.get(gid, "genre")} TV from the last 3 years'),
                ]
            for gid in genres_to_try[:2]:
                discover_calls.append(
                    ('/discover/movie', {
                        'with_genres': gid,
                        'sort_by': 'vote_average.desc',
                        'vote_count.gte': 1000,
                        'page': 1,
                    }, 'movie', 'Highly rated match for your taste')
                )

            for endpoint, params, mtype, reason in discover_calls:
                try:
                    data = tmdb_api.tmdb_request(endpoint, params)
                    for item in data.get('results', []):
                        tid = item['id']
                        if tid in excluded_ids or tid in existing_ids or tid in genre_pool:
                            continue
                        if not item.get('poster_path'):
                            continue
                        if item.get('vote_average', 0) < 6.0:
                            continue
                        genre_pool[tid] = (item, mtype, reason)
                except Exception:
                    pass

            genre_recs = []
            for tid, (item, mtype, reason) in genre_pool.items():
                score = quality_score(item)
                genre_recs.append({
                    'tmdb_id': tid,
                    'media_type': mtype,
                    'title': item.get('title') or item.get('name', ''),
                    'poster_path': item.get('poster_path'),
                    'backdrop_path': item.get('backdrop_path'),
                    'overview': item.get('overview', ''),
                    'vote_average': round(item.get('vote_average', 0), 1),
                    'vote_count': item.get('vote_count', 0),
                    'popularity': round(item.get('popularity', 0), 1),
                    'release_date': item.get('release_date') or item.get('first_air_date', ''),
                    'genre_ids': item.get('genre_ids', []),
                    'score': round(score, 4),
                    'type': 'genre-discover',
                    'reason': reason,
                })

            genre_recs.sort(key=lambda x: x['score'], reverse=True)
            needed = limit - len(recommendations)
            recommendations += genre_recs[:needed]
            logger.info('Genre-discover: added %d recs for user %s', min(len(genre_recs), needed), user_id)

        # ═══════════════════════════════════════════════════════════════════
        # TIER 3 — Trending / popular fallback
        # ═══════════════════════════════════════════════════════════════════
        if len(recommendations) < limit // 2:
            existing_ids = {r['tmdb_id'] for r in recommendations}
            fallback_pool = {}
            fallback_sources = [
                ('/trending/all/week', {}, 'Trending this week'),
                ('/movie/now_playing', {'page': 1}, 'In cinemas now'),
                ('/tv/popular', {'page': 1}, 'Popular on TV'),
            ]
            for endpoint, params, reason in fallback_sources:
                try:
                    data = tmdb_api.tmdb_request(endpoint, params)
                    for item in data.get('results', []):
                        tid = item['id']
                        mtype = item.get('media_type', 'movie' if '/movie' in endpoint else 'tv')
                        if tid not in excluded_ids and tid not in existing_ids and tid not in fallback_pool:
                            if item.get('poster_path') and item.get('vote_average', 0) >= 6.5:
                                fallback_pool[tid] = (item, mtype, reason)
                except Exception:
                    pass

            fallback_recs = []
            for tid, (item, mtype, reason) in fallback_pool.items():
                fallback_recs.append({
                    'tmdb_id': tid,
                    'media_type': mtype,
                    'title': item.get('title') or item.get('name', ''),
                    'poster_path': item.get('poster_path'),
                    'backdrop_path': item.get('backdrop_path'),
                    'overview': item.get('overview', ''),
                    'vote_average': round(item.get('vote_average', 0), 1),
                    'vote_count': item.get('vote_count', 0),
                    'popularity': round(item.get('popularity', 0), 1),
                    'release_date': item.get('release_date') or item.get('first_air_date', ''),
                    'genre_ids': item.get('genre_ids', []),
                    'score': round(quality_score(item), 4),
                    'type': 'trending',
                    'reason': reason,
                })

            fallback_recs.sort(key=lambda x: x['score'], reverse=True)
            needed = limit - len(recommendations)
            recommendations += fallback_recs[:needed]

        # ═══════════════════════════════════════════════════════════════════
        # POST-PROCESSING — Diversity engine (MMR + serendipity)
        # ═══════════════════════════════════════════════════════════════════
        if len(recommendations) > 3:
            try:
                from .ml.diversity_engine import (
                    diversity_engine, DiversityCandidate, DiversityConfig,
                )

                diversity_candidates = []
                for rec in recommendations:
                    genre_names_for_rec = [
                        GENRE_ID_TO_NAME.get(gid, '') for gid in rec.get('genre_ids', [])
                    ]
                    genre_names_for_rec = [g for g in genre_names_for_rec if g]
                    diversity_candidates.append(DiversityCandidate(
                        id=str(rec['tmdb_id']),
                        tmdb_id=rec['tmdb_id'],
                        media_type=rec.get('media_type', 'movie'),
                        score=rec.get('score', 0.5),
                        genres=genre_names_for_rec,
                    ))

                config = DiversityConfig(
                    lambda_param=0.7,
                    epsilon_exploration=0.1,
                    max_consecutive_same_genre=3,
                    serendipity_rate=0.12,
                    diversity_metric='mmr',
                )

                diversified = diversity_engine.apply_diversity(
                    diversity_candidates, config, preferred_genre_names
                )

                rec_lookup = {r['tmdb_id']: r for r in recommendations}
                reordered = []
                for dc in diversified:
                    if dc.tmdb_id in rec_lookup:
                        rec = rec_lookup[dc.tmdb_id]
                        rec['score'] = round(dc.score, 4)
                        reordered.append(rec)
                if reordered:
                    recommendations = reordered
                    logger.info('Diversity: reranked %d recs for user %s', len(recommendations), user_id)
            except Exception as e:
                logger.warning('Diversity engine failed (non-fatal): %s', e)

        return JsonResponse({
            "user_id": user_id,
            "recommendations": recommendations[:limit],
            "type": "hybrid",
            "count": len(recommendations[:limit]),
            "strategy": arm_chosen,
            "experiment_id": experiment_id,
        })

    except Exception as e:
        import traceback
        logger.error('get_hybrid_recommendations error: %s', traceback.format_exc())
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_collaborative_recommendations(request, user_id):
    """Get recommendations using collaborative filtering"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_user_similarity(request, user_id):
    """Find users with similar taste"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def semantic_search(request):
    """Semantic search for movies/TV shows with hybrid re-ranking"""
    if request.method not in ['POST', 'GET']:
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    import time
    start_time = time.time()
    
    try:
        if request.method == 'POST':
            body = json.loads(request.body)
            query = body.get('query', '')
            limit = min(body.get('limit', 20), 100)
            filters = body.get('filters', {})
            sort_by = body.get('sortBy', 'relevance')
        else:
            query = request.GET.get('query', '')
            try:
                limit = min(int(request.GET.get('limit', 20)), 100)
            except ValueError:
                limit = 20
            filters = {}
            sort_by = request.GET.get('sortBy', 'relevance')
        
        if not query:
            return error_response("query is required", "VALIDATION_ERROR", 400)
        from .ml.pinecone_service import pinecone_service
        search_method = "pinecone_semantic"

        if pinecone_service.is_initialized():
            pinecone_filters = None
            if filters:
                pinecone_filters = {}
                if filters.get('yearRange'):
                    yr = filters['yearRange']
                    if isinstance(yr, list) and len(yr) == 2:
                        pinecone_filters["release_year"] = {
                            "$gte": str(yr[0]),
                            "$lte": str(yr[1]),
                        }
                if filters.get('minRating') and filters['minRating'] > 0:
                    pinecone_filters["vote_average"] = {"$gte": float(filters['minRating'])}
                if filters.get('languages') and len(filters['languages']) > 0:
                    pinecone_filters["original_language"] = {"$in": filters['languages']}
                if not pinecone_filters:
                    pinecone_filters = None

            pinecone_results = pinecone_service.search(query, k=limit, filters=pinecone_filters)
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
                        'popularity': item.get('popularity', 0),
                        'genres': item.get('genres', '').split(', ') if item.get('genres') else [],
                        'mediaType': 'movie',
                        'similarity': item.get('composite_score', item.get('similarity', 0)),
                        'rawSimilarity': item.get('similarity', 0),
                        'explanation': item.get('explanation', ''),
                        'matchQuality': item.get('match_quality', ''),
                        'recencyBoost': item.get('recency_boost', 0),
                        'popularityBoost': item.get('popularity_boost', 0),
                    })

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
                            if not formatted_results[idx].get('genres') or formatted_results[idx]['genres'] == []:
                                formatted_results[idx]['genres'] = [g['name'] for g in detail.get('genres', [])]
                            formatted_results[idx]['popularity'] = detail.get('popularity') or formatted_results[idx].get('popularity', 0)

                formatted_results = [r for r in formatted_results if r.get('posterPath')]

                if sort_by == 'release_date':
                    formatted_results.sort(key=lambda x: x.get('releaseDate') or '', reverse=True)
                elif sort_by == 'rating':
                    formatted_results.sort(key=lambda x: x.get('voteAverage') or 0, reverse=True)

                search_time = time.time() - start_time

                return JsonResponse({
                    'results': formatted_results,
                    'query': query,
                    'count': len(formatted_results),
                    'totalMatches': len(formatted_results),
                    'searchTime': round(search_time, 3),
                    'searchMethod': search_method,
                })

        search_method = "tfidf_local"
        from . import api
        from .ml.embedding_service import semantic_embedding_service
        from .models import TmdbTrainingData

        local_items = []
        try:
            qs = TmdbTrainingData.objects.exclude(overview__isnull=True).exclude(overview='')
            year_range = filters.get('yearRange')
            min_rating = filters.get('minRating', 0)
            max_rating = filters.get('maxRating', 10)

            if year_range and isinstance(year_range, list) and len(year_range) == 2:
                qs = qs.filter(release_date__gte=str(year_range[0]), release_date__lte=str(year_range[1]) + '-12-31')
            if min_rating and min_rating > 0:
                qs = qs.filter(vote_average__gte=min_rating)
            if max_rating and max_rating < 10:
                qs = qs.filter(vote_average__lte=max_rating)

            qs = qs.order_by('-popularity')[:limit * 10]

            for row in qs:
                local_items.append({
                    'id': row.tmdb_id,
                    'title': row.title or '',
                    'overview': row.overview or '',
                    'vote_average': row.vote_average or 0,
                    'popularity': row.popularity or 0,
                    'release_date': row.release_date or '',
                    'poster_path': row.poster_path or '',
                    'genres': row.genres or '',
                    'media_type': 'movie',
                })
        except Exception:
            local_items = []

        if not local_items:
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
                for item in result['results'][:limit * 2]:
                    if item.get('media_type') == 'person':
                        continue
                    local_items.append(item)

        if local_items:
            ranked_results = semantic_embedding_service.search_with_similarity(
                query, local_items, top_k=limit, apply_reranking=True
            )

            formatted_results = []
            for item, similarity in ranked_results:
                title = item.get('title') or item.get('name', '')

                match_pct = int(similarity * 100)
                labels = []
                if similarity >= 0.7:
                    labels.append("Semantic match")
                vote_avg = item.get('vote_average', 0)
                if vote_avg and vote_avg >= 7.0:
                    labels.append("Popular")
                match_quality = ", ".join(labels) if labels else "Related"

                formatted_results.append({
                    'tmdbId': item.get('id'),
                    'title': title,
                    'overview': item.get('overview', ''),
                    'posterPath': item.get('poster_path'),
                    'releaseDate': item.get('release_date') or item.get('first_air_date'),
                    'voteAverage': vote_avg,
                    'popularity': item.get('popularity'),
                    'genres': item.get('genre_ids', item.get('genres', [])),
                    'mediaType': item.get('media_type', 'movie'),
                    'similarity': round(similarity, 3),
                    'explanation': f"{match_pct}% match — {match_quality}",
                    'matchQuality': match_quality,
                })

            if sort_by == 'release_date':
                formatted_results.sort(key=lambda x: x.get('releaseDate') or '', reverse=True)
            elif sort_by == 'rating':
                formatted_results.sort(key=lambda x: x.get('voteAverage') or 0, reverse=True)
            
            search_time = time.time() - start_time

            return JsonResponse({
                "query": query,
                "results": formatted_results,
                "totalMatches": len(formatted_results),
                "searchTime": round(search_time, 3),
                "searchMethod": search_method,
                "queryAnalysis": {
                    "originalQuery": query,
                    "filters": filters
                }
            })

        return JsonResponse({
            "query": query,
            "results": [],
            "totalMatches": 0,
            "searchTime": round(time.time() - start_time, 3),
            "searchMethod": search_method,
            "queryAnalysis": {"originalQuery": query, "filters": filters}
        })

    except json.JSONDecodeError:
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_recommendation_explanation(request, user_id, tmdb_id):
    """Explain why a recommendation was made for a user using the explainability engine"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_bandit_statistics(request, user_id):
    """Get contextual bandit statistics for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
        from .ml.contextual_bandits import contextual_bandit_engine
        
        stats = contextual_bandit_engine.get_statistics(str(user_id))
        
        return JsonResponse({
            "user_id": user_id,
            "bandit_statistics": stats
        })
        
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def select_recommendation_arm(request, user_id):
    """Select a recommendation strategy using contextual bandits"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def update_bandit_reward(request):
    """Update bandit experiment with user feedback reward"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    try:
        body = json.loads(request.body)
        experiment_id = body.get('experiment_id')
        outcome_type = body.get('outcome_type')
        
        if not experiment_id or not outcome_type:
            return error_response("experiment_id and outcome_type are required", "VALIDATION_ERROR", 400)
        
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def apply_diversity(request):
    """Apply diversity algorithms to a list of recommendations"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    try:
        body = json.loads(request.body)
        candidates = body.get('candidates', [])
        config = body.get('config', {})
        user_genre_preferences = body.get('user_genre_preferences', [])
        
        if not candidates:
            return error_response("candidates is required", "VALIDATION_ERROR", 400)
        
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_diversity_metrics(request, user_id):
    """Get diversity metrics for a user's recommendation history"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def analyze_text_sentiment(request):
    """Analyze sentiment of arbitrary text"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    try:
        body = json.loads(request.body)
        text = body.get('text', '')
        
        if not text:
            return error_response("text is required", "VALIDATION_ERROR", 400)
        
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def update_sentiment_for_content(request, tmdb_id):
    """Trigger sentiment recalculation for a movie/TV show"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_recommendation_history(request, user_id):
    """Get recommendation history for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def log_recommendation_interaction(request):
    """Log recommendation interaction (clicked, watchlisted, rated_high, ignored, dismissed)"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
    try:
        body = json.loads(request.body)
        recommendation_id = body.get('recommendation_id')
        user_id = body.get('user_id')
        interaction_type = body.get('interaction_type')
        
        if not recommendation_id:
            return error_response("recommendation_id is required", "VALIDATION_ERROR", 400)
        if not user_id:
            return error_response("user_id is required", "VALIDATION_ERROR", 400)
        if not interaction_type:
            return error_response("interaction_type is required", "VALIDATION_ERROR", 400)
        
        valid_interaction_types = ['clicked', 'watchlisted', 'rated_high', 'ignored', 'dismissed']
        if interaction_type not in valid_interaction_types:
            return JsonResponse({
                "error": f"Invalid interaction_type. Must be one of: {', '.join(valid_interaction_types)}"
            }, status=400)
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)

        # recommendation_id may be a DB integer ID or "tmdb_id-media_type" composite
        recommendation = None
        tmdb_id_from_rec = None
        media_type_from_rec = 'movie'

        if recommendation_id and '-' in str(recommendation_id):
            # Composite key format: "<tmdb_id>-<media_type>"
            parts = str(recommendation_id).rsplit('-', 1)
            try:
                tmdb_id_from_rec = int(parts[0])
                media_type_from_rec = parts[1] if len(parts) > 1 else 'movie'
            except (ValueError, IndexError):
                pass

        if tmdb_id_from_rec:
            # Find existing or create a lightweight Recommendation record
            recommendation = Recommendation.objects.filter(
                user=user, tmdb_id=tmdb_id_from_rec
            ).first()
            if not recommendation:
                recommendation = Recommendation.objects.create(
                    user=user,
                    tmdb_id=tmdb_id_from_rec,
                    media_type=media_type_from_rec,
                    recommendation_type='hybrid',
                    title='',
                    reason='User feedback',
                    confidence=0.5,
                    relevance_score=0.5,
                )
        else:
            # Fallback: treat as an integer DB primary key
            try:
                recommendation = Recommendation.objects.filter(id=int(recommendation_id), user=user).first()
            except (ValueError, TypeError):
                pass

        if not recommendation:
            return error_response("Recommendation not found", "NOT_FOUND", 404)
        
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
        
        try:
            from .ml.feedback_service import feedback_service
            scoring_factors = body.get('scoring_factors') or {}
            if not scoring_factors:
                rec_type = recommendation.recommendation_type or 'hybrid'
                scoring_factors = {
                    'collaborative': 0.6 if rec_type in ('collaborative', 'hybrid') else 0.2,
                    'content': 0.4 if rec_type in ('content', 'hybrid') else 0.2,
                    'popularity': 0.2,
                    'recency': 0.15,
                }
            feedback_service.record_outcome(
                user=user,
                recommendation=recommendation,
                interaction_type=interaction_type,
                scoring_factors=scoring_factors,
            )
        except Exception as e:
            logger.warning('Feedback service error (non-fatal): %s', e)
        
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_global_feature_importance(request):
    """Get global feature importance scores across all recommendations"""
    try:
        user_id = request.GET.get('user_id')
        
        from .ml.explainability_engine import explainability_engine
        
        result = explainability_engine.get_feature_importance(user_id)
        
        return JsonResponse(result)
        
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_counterfactual_explanation(request, user_id, tmdb_id):
    """Get counterfactual explanation for why an alternative was not recommended"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
        alternative_tmdb_id = request.GET.get('alternative_tmdb_id')
        if not alternative_tmdb_id:
            return error_response("alternative_tmdb_id query parameter is required", "VALIDATION_ERROR", 400)
        
        try:
            alternative_tmdb_id = int(alternative_tmdb_id)
        except ValueError:
            return error_response("alternative_tmdb_id must be a valid integer", "VALIDATION_ERROR", 400)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_local_explanation(request, user_id, tmdb_id):
    """Get local explanation using permutation importance for an individual recommendation"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
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
        return error_response(str(e), "INTERNAL_ERROR", 500)


@rate_limit()
def calibrate_confidence(request):
    """Calibrate confidence scores based on historical accuracy"""
    if request.method != 'POST':
        return error_response("Method not allowed", "METHOD_NOT_ALLOWED", 405)
    
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
        return error_response("Invalid JSON", "VALIDATION_ERROR", 400)
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


@require_GET
def get_viewing_patterns(request, user_id):
    """Get viewing pattern analysis for a user"""
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return error_response("User not found", "NOT_FOUND", 404)
        
        from .ml.pattern_recognition import viewing_pattern_analyzer
        
        pattern_summary = viewing_pattern_analyzer.get_pattern_summary(user_id)
        result = viewing_pattern_analyzer.to_dict(pattern_summary)
        
        return JsonResponse(result)
        
    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)


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
                    logger.info("Pinecone quality too low for %s (top=%.2f), using TMDB fallback", tmdb_id, top_score)
        except Exception as e:
            logger.warning("Pinecone search error: %s", e)

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
                logger.warning("TMDB recommendations error: %s", e)

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
                logger.warning("TMDB similar error: %s", e)

        # Filter out movies the logged-in user has dismissed
        if request.user.is_authenticated:
            try:
                from .models import Recommendation
                dismissed_ids = set(
                    Recommendation.objects.filter(
                        user=request.user, user_feedback='disliked'
                    ).values_list('tmdb_id', flat=True)
                )
                if dismissed_ids:
                    similar_items = [
                        item for item in similar_items
                        if item.get('tmdb_id') not in dismissed_ids
                    ]
            except Exception:
                pass

        return JsonResponse({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "similar_items": similar_items,
            "count": len(similar_items),
        })

    except Exception as e:
        return error_response(str(e), "INTERNAL_ERROR", 500)
