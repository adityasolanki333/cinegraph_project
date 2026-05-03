import React, { useState } from 'react';
import { getAuthHeaders } from '@/lib/queryClient';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sparkles, Search, Brain, ChevronDown, ChevronUp, ArrowUpDown, Clock, Star, TrendingUp, Zap, SearchX } from 'lucide-react';
import { PreferenceWizard } from './preference-wizard';
import { useQuery } from '@tanstack/react-query';
import { MediaCard } from '@/components/media-card';
import MediaCardSkeleton from '@/components/media-card-skeleton';
import { ExplanationVisualizer, ExplanationData } from './explanation-visualizer';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from 'react-i18next';

const genreNameToKey: Record<string, string> = {
  "Action": "action", "Adventure": "adventure", "Animation": "animation",
  "Comedy": "comedy", "Crime": "crime", "Documentary": "documentary",
  "Drama": "drama", "Family": "family", "Fantasy": "fantasy",
  "History": "history", "Horror": "horror", "Music": "music",
  "Mystery": "mystery", "Romance": "romance", "Science Fiction": "scienceFiction",
  "TV Movie": "tvMovie", "Thriller": "thriller", "War": "war",
  "Western": "western", "Action & Adventure": "actionAndAdventure",
  "Sci-Fi & Fantasy": "sciFiAndFantasy", "Kids": "kids", "News": "news",
  "Reality": "reality", "Soap": "soap", "Talk": "talk",
  "War & Politics": "warAndPolitics", "Sci-Fi": "sciFi"
};

function ExplanationLoader({ movieId, mediaType, initialReason }: { movieId: number, mediaType: string, initialReason: string }) {
  const { user } = useAuth();
  const { t } = useTranslation();
  const userId = user?.id || 'demo_user';

  const { data: explanation, isLoading } = useQuery({
    queryKey: ['explanation', userId, movieId],
    queryFn: async () => {
      const res = await fetch(`/api/recommendations/explain/${userId}/${movieId}?media_type=${mediaType}`, {
        headers: { ...getAuthHeaders() },
      });
      if (!res.ok) throw new Error('Failed to load explanation');
      return await res.json();
    }
  });

  if (isLoading) return <div className="text-xs text-muted-foreground animate-pulse">{t('advancedFinder.analyzingInsights')}</div>;

  if (!explanation) return <div className="text-xs text-muted-foreground">{initialReason}</div>;

  return <ExplanationVisualizer explanation={explanation} className="text-xs" />;
}

function MatchQualityBadge({ matchQuality, similarity }: { matchQuality: string; similarity: number }) {
  const pct = Math.round(similarity * 100);

  const getColor = () => {
    if (pct >= 80) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800';
    if (pct >= 60) return 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800';
    if (pct >= 40) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800';
    return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700';
  };

  const getIcon = () => {
    if (matchQuality.includes('Semantic match')) return <Zap className="h-3 w-3" />;
    if (matchQuality.includes('Popular')) return <TrendingUp className="h-3 w-3" />;
    if (matchQuality.includes('Recent')) return <Clock className="h-3 w-3" />;
    if (matchQuality.includes('Title match')) return <Search className="h-3 w-3" />;
    return <Sparkles className="h-3 w-3" />;
  };

  return (
    <div className="flex items-center gap-1.5 flex-wrap" data-testid="match-quality-badges">
      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 gap-1 font-semibold border ${getColor()}`} data-testid="badge-match-score">
        {getIcon()}
        {pct}% match
      </Badge>
      {matchQuality && matchQuality !== 'Related' && (
        <span className="text-[10px] text-muted-foreground">{matchQuality}</span>
      )}
    </div>
  );
}

interface UserPreferences {
  mediaType: string[];
  releaseYearRange: [number, number];
  ratingRange: [number, number];
  genres: string[];
  moods: string[];
  languages: string[];
  runtime: string;
}

interface RecommendedMovie {
  id: number;
  title: string;
  name?: string;
  overview: string;
  poster_path: string;
  release_date: string;
  first_air_date?: string;
  vote_average: number;
  popularity: number;
  genre: string;
  media_type: string;
  number_of_seasons?: number;
}

interface AdvancedRecommendation {
  movie: RecommendedMovie;
  matchScore: number;
  reasons: string[];
  searchContext: string[];
  relatedMovies: string[];
  matchQuality?: string;
  similarity?: number;
}

interface SemanticSearchApiResult {
  tmdbId: number;
  title: string;
  overview: string;
  posterPath: string;
  releaseDate: string;
  voteAverage: number;
  popularity: number;
  genres: string[];
  mediaType: string;
  similarity: number;
  explanation: string;
  matchQuality: string;
}

interface SearchResponse {
  recommendations: AdvancedRecommendation[];
  totalMatches: number;
  searchTime: number;
  searchMethod: string;
  queryAnalysis?: Record<string, unknown>;
}

export function AdvancedRecommendations() {
  const { t } = useTranslation();
  const [showWizard, setShowWizard] = useState(false);

  const [preferences, setPreferences] = useState<UserPreferences | null>(() => {
    const saved = sessionStorage.getItem('advancedRecommendations_preferences');
    return saved ? JSON.parse(saved) : null;
  });

  const [searchQuery, setSearchQuery] = useState(() => {
    return sessionStorage.getItem('advancedRecommendations_query') || '';
  });

  const [searchTrigger, setSearchTrigger] = useState(0);
  const [lastSearchedQuery, setLastSearchedQuery] = useState('');
  const [sortBy, setSortBy] = useState('relevance');
  const [expandedRecommendations, setExpandedRecommendations] = useState<Set<number>>(new Set());

  React.useEffect(() => {
    if (preferences) {
      sessionStorage.setItem('advancedRecommendations_preferences', JSON.stringify(preferences));
    } else {
      sessionStorage.removeItem('advancedRecommendations_preferences');
    }
  }, [preferences]);

  React.useEffect(() => {
    sessionStorage.setItem('advancedRecommendations_query', searchQuery);
  }, [searchQuery]);

  const { data: recommendations, isLoading, error, isFetching } = useQuery({
    queryKey: ['/api/recommendations/semantic-search', lastSearchedQuery, preferences, searchTrigger, sortBy],
    enabled: searchTrigger > 0 && !!lastSearchedQuery,
    queryFn: async () => {
      const filters: Record<string, string[] | number[] | [number, number] | number | string> = {};

      if (preferences) {
        if (preferences.genres && preferences.genres.length > 0) {
          filters.genres = preferences.genres;
        }
        if (preferences.releaseYearRange) {
          filters.yearRange = preferences.releaseYearRange;
        }
        if (preferences.ratingRange) {
          filters.minRating = preferences.ratingRange[0];
          filters.maxRating = preferences.ratingRange[1];
        }
        if (preferences.languages && preferences.languages.length > 0) {
          filters.languages = preferences.languages;
        }
        if (preferences.mediaType && preferences.mediaType.length > 0) {
          filters.mediaType = preferences.mediaType;
        }
        if (preferences.moods && preferences.moods.length > 0) {
          filters.moods = preferences.moods;
        }
        if (preferences.runtime) {
          filters.runtime = preferences.runtime;
        }
      }

      const response = await fetch('/api/recommendations/semantic-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders(),
        },
        body: JSON.stringify({
          query: lastSearchedQuery,
          limit: 20,
          filters,
          sortBy,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 429) {
          throw new Error(errorData.message || 'Too many requests. Please wait a moment before trying again.');
        }
        throw new Error(errorData.message || 'Failed to perform semantic search');
      }

      const data = await response.json();

      return {
        recommendations: data.results.map((result: SemanticSearchApiResult) => ({
          movie: {
            id: result.tmdbId,
            title: result.title,
            overview: result.overview,
            poster_path: result.posterPath,
            release_date: result.releaseDate,
            vote_average: result.voteAverage,
            popularity: result.popularity,
            genre: Array.isArray(result.genres) && result.genres.length > 0 ? result.genres[0] : '',
            media_type: result.mediaType || 'movie'
          },
          matchScore: Math.round((result.similarity || 0) * 100),
          reasons: [result.explanation],
          searchContext: [`Similarity: ${((result.similarity || 0) * 100).toFixed(1)}%`],
          relatedMovies: [],
          matchQuality: result.matchQuality || '',
          similarity: result.similarity || 0,
        })),
        totalMatches: data.totalMatches,
        searchTime: data.searchTime,
        searchMethod: data.searchMethod,
        queryAnalysis: data.queryAnalysis,
      };
    },
  });

  const handlePreferencesComplete = (prefs: UserPreferences) => {
    setPreferences(prefs);
    setShowWizard(false);
  };

  const handleSearch = () => {
    if (searchQuery.trim() && !isLoading && !isFetching) {
      setLastSearchedQuery(searchQuery.trim());
      setSearchTrigger(prev => prev + 1);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const toggleRecommendationDetails = (movieId: number) => {
    setExpandedRecommendations(prev => {
      const newSet = new Set(prev);
      if (newSet.has(movieId)) {
        newSet.delete(movieId);
      } else {
        newSet.add(movieId);
      }
      return newSet;
    });
  };

  if (showWizard) {
    return (
      <div className="min-h-screen bg-background p-4 flex items-center justify-center">
        <PreferenceWizard
          onComplete={handlePreferencesComplete}
          onSkip={() => {
            setShowWizard(false);
          }}
          onReset={() => {
            setPreferences(null);
            sessionStorage.removeItem('userPreferences');
            setShowWizard(false);
          }}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-3 sm:px-6 lg:px-8 py-4 sm:py-8">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 sm:mb-8">
        <div className="flex items-center space-x-2 sm:space-x-3">
          <Brain className="h-6 w-6 sm:h-8 sm:w-8 text-primary" />
          <div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-foreground">{t('advancedFinder.title')}</h1>
          </div>
        </div>
        <Button
          onClick={() => setShowWizard(true)}
          variant="outline"
          className="gap-2 w-full sm:w-auto"
        >
          <Sparkles className="h-4 w-4" />
          <span className="hidden sm:inline">{preferences ? t('advancedFinder.updatePreferences') : t('advancedFinder.setPreferences')}</span>
          <span className="sm:hidden">{t('advancedFinder.preferences')}</span>
        </Button>
      </div>

      <Card className="mb-4 sm:mb-8">
        <CardHeader className="p-4 sm:p-6 pb-3">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Brain className="h-4 w-4 sm:h-5 sm:w-5" />
            <span className="hidden sm:inline">{t('advancedFinder.semanticSearch')}</span>
            <span className="sm:hidden">{t('advancedFinder.semanticSearchShort')}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4 p-4 sm:p-6 pt-0">
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={t('advancedFinder.searchPlaceholder')}
              className="flex-1 text-sm sm:text-base"
              data-testid="input-advanced-search"
            />
            <Button
              onClick={handleSearch}
              disabled={!searchQuery.trim() || isLoading || isFetching}
              className="gap-2 w-full sm:w-auto"
              data-testid="button-advanced-search"
            >
              <Search className="h-4 w-4" />
              <span className="hidden sm:inline">{t('advancedFinder.findMovies')}</span>
              <span className="sm:hidden">{t('advancedFinder.searchBtn')}</span>
            </Button>
          </div>

          {!preferences && (
            <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
              <p className="text-sm text-blue-700 dark:text-blue-300">
                {t('advancedFinder.optionalPreferences')}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {preferences && (
        <Card className="mb-4 sm:mb-8">
          <CardHeader className="p-4 sm:p-6">
            <CardTitle className="text-base sm:text-lg">{t('advancedFinder.yourPreferences')}</CardTitle>
          </CardHeader>
          <CardContent className="p-4 sm:p-6 pt-0">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 text-sm">
              <div>
                <span className="font-medium">{t('advancedFinder.mediaType')}:</span> {preferences.mediaType.join(', ')}
              </div>
              <div>
                <span className="font-medium">{t('advancedFinder.years')}:</span> {preferences.releaseYearRange[0]} - {preferences.releaseYearRange[1]}
              </div>
              <div>
                <span className="font-medium">{t('advancedFinder.ratingLabel')}:</span> {preferences.ratingRange[0]} - {preferences.ratingRange[1]}
              </div>
              <div>
                <span className="font-medium">{t('advancedFinder.runtime')}:</span> {preferences.runtime}
              </div>
              <div className="sm:col-span-2 md:col-span-2">
                <span className="font-medium">{t('advancedFinder.languages')}:</span> {preferences.languages.join(', ')}
              </div>
              {preferences.genres.length > 0 && (
                <div className="sm:col-span-2 md:col-span-3">
                  <span className="font-medium">{t('advancedFinder.genres')}:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {preferences.genres.map(genre => (
                      <Badge key={genre} variant="secondary" className="text-xs">
                        {genre}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {preferences.moods.length > 0 && (
                <div className="sm:col-span-2 md:col-span-3">
                  <span className="font-medium">{t('advancedFinder.moods')}:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {preferences.moods.map(mood => (
                      <Badge key={mood} variant="outline" className="text-xs">
                        {mood}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {(isLoading || isFetching) && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <div className="h-4 w-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">{t('advancedFinder.searchingAI')}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-6">
            {Array.from({ length: 10 }, (_, i) => (
              <MediaCardSkeleton key={i} />
            ))}
          </div>
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center">
            <div className="flex flex-col items-center gap-3">
              <div className="text-red-600 dark:text-red-400">
                <p className="font-semibold mb-2">
                  {error.message.includes('Too many requests') || error.message.includes('rate limit')
                    ? t('advancedFinder.rateLimitReached')
                    : t('advancedFinder.error')}
                </p>
                <p className="text-sm text-muted-foreground">
                  {error.message}
                </p>
              </div>
              {(error.message.includes('Too many requests') || error.message.includes('rate limit')) && (
                <p className="text-xs text-muted-foreground max-w-md">
                  {t('advancedFinder.rateLimitDesc')}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {recommendations && recommendations.recommendations && recommendations.recommendations.length > 0 && !isLoading && !isFetching && (
        <div className="space-y-6">
          <div className="space-y-3 sm:space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h2 className="text-lg sm:text-xl lg:text-2xl font-bold" data-testid="text-results-heading">
                  {preferences?.mediaType.includes('both') || (preferences?.mediaType.includes('movies') && preferences?.mediaType.includes('tv'))
                    ? t('advancedFinder.recommendedMoviesTV')
                    : preferences?.mediaType.includes('tv')
                      ? t('advancedFinder.recommendedTV')
                      : t('advancedFinder.recommendedMovies')}
                </h2>
                <Badge variant="secondary" className="text-xs sm:text-sm" data-testid="badge-result-count">
                  {recommendations.recommendations.length} {t('advancedFinder.results')}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                {recommendations.searchTime && (
                  <span className="text-xs text-muted-foreground" data-testid="text-search-time">
                    {recommendations.searchTime}s
                  </span>
                )}
                <Select value={sortBy} onValueChange={(val) => { setSortBy(val); if (searchTrigger > 0) setSearchTrigger(prev => prev + 1); }}>
                  <SelectTrigger className="w-[160px] h-8 text-xs" data-testid="select-sort-by">
                    <ArrowUpDown className="h-3 w-3 mr-1" />
                    <SelectValue placeholder={t('advancedFinder.sortBy')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relevance">{t('advancedFinder.relevance')}</SelectItem>
                    <SelectItem value="release_date">{t('advancedFinder.releaseDate')}</SelectItem>
                    <SelectItem value="rating">{t('advancedFinder.ratingSort')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>


            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-6">
              {recommendations.recommendations.map((rec: AdvancedRecommendation, index: number) => {
                const mediaType = rec.movie.media_type || (rec.movie.name ? 'tv' : 'movie');
                const title = rec.movie.title || rec.movie.name;
                const releaseDate = rec.movie.release_date || rec.movie.first_air_date;
                const year = releaseDate ? new Date(releaseDate).getFullYear().toString() : '';

                return (
                  <div key={`${rec.movie.id}-${index}`} className="relative" data-testid={`card-result-${rec.movie.id}`}>
                    <MediaCard
                      item={{
                        id: rec.movie.id,
                        title: title,
                        name: rec.movie.name,
                        rating: rec.movie.vote_average || 0,
                        year: year,
                        synopsis: rec.movie.overview,
                        poster_path: rec.movie.poster_path,
                        genre: rec.movie.genre,
                        type: mediaType,
                        media_type: mediaType,
                        first_air_date: rec.movie.first_air_date,
                        release_date: rec.movie.release_date,
                        number_of_seasons: rec.movie.number_of_seasons
                      }}
                      mediaType={mediaType}
                    >
                      <div className="pt-2 space-y-1.5">
                        <MatchQualityBadge
                          matchQuality={rec.matchQuality || ''}
                          similarity={rec.similarity || rec.matchScore / 100}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full text-xs h-6 gap-1"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            toggleRecommendationDetails(rec.movie.id);
                          }}
                          data-testid={`button-why-${rec.movie.id}`}
                        >
                          <Brain className="h-3 w-3" />
                          {expandedRecommendations.has(rec.movie.id) ? 'Hide Insights' : 'Why this?'}
                          {expandedRecommendations.has(rec.movie.id) ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        </Button>

                        {expandedRecommendations.has(rec.movie.id) && (
                          <div className="mt-2 animate-in fade-in zoom-in-95 duration-200">
                            <ExplanationLoader
                              movieId={rec.movie.id}
                              mediaType={mediaType}
                              initialReason={rec.reasons[0]}
                            />
                          </div>
                        )}
                      </div>
                    </MediaCard>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {searchTrigger > 0 && !isLoading && !isFetching && !error && (!recommendations || !recommendations.recommendations?.length) && (
        <Card data-testid="card-empty-state">
          <CardContent className="py-12 text-center">
            <SearchX className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No results found for "{lastSearchedQuery}"</h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Try describing what you're looking for differently, or use broader terms. You can also adjust your preferences to widen the search.
            </p>
            <div className="flex flex-col sm:flex-row gap-2 justify-center">
              <Button
                onClick={() => {
                  setSearchQuery('');
                  setLastSearchedQuery('');
                  setSearchTrigger(0);
                }}
                variant="outline"
                data-testid="button-clear-search"
              >
                Clear Search
              </Button>
              {preferences && (
                <Button onClick={() => setShowWizard(true)} variant="outline" data-testid="button-update-preferences">
                  Update Preferences
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
