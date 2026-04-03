import { useState, useEffect, useMemo } from "react";
import { getCsrfToken } from "@/lib/queryClient";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import AIChat from "@/components/ai-chat";
import { AdvancedRecommendations } from "@/components/advanced-recommendations";

import { MediaCard } from "@/components/media-card";
import MediaCardSkeleton from "@/components/media-card-skeleton";
import { tmdbService } from "@/lib/tmdb";
import { Sparkles, Heart, Brain, Zap, Smile, Loader2, Search, Settings, RefreshCw, Film, Tv, Target, ThumbsUp, X } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { useWatchlist } from "@/hooks/useWatchlist";
import { Link } from "wouter";
import type { Movie } from "@shared/schema";
import { useAuth } from "@/hooks/useAuth";
import { usePageMeta } from "@/hooks/usePageMeta";
import { useTranslation } from "react-i18next";

const moodOptionsDef = [
  { id: "happy", labelKey: "moods.happy", descKey: "moods.happyDesc", icon: Smile, color: "text-yellow-500" },
  { id: "romantic", labelKey: "moods.romantic", descKey: "moods.romanticDesc", icon: Heart, color: "text-pink-500" },
  { id: "energetic", labelKey: "moods.energetic", descKey: "moods.energeticDesc", icon: Zap, color: "text-red-500" },
  { id: "thoughtful", labelKey: "moods.thoughtful", descKey: "moods.thoughtfulDesc", icon: Brain, color: "text-blue-500" },
  { id: "scary", labelKey: "moods.scary", descKey: "moods.scaryDesc", icon: Brain, color: "text-purple-500" },
  { id: "nostalgic", labelKey: "moods.classic", descKey: "moods.classicDesc", icon: Sparkles, color: "text-amber-500" },
  { id: "animated", labelKey: "moods.animated", descKey: "moods.animatedDesc", icon: Heart, color: "text-green-500" },
  { id: "indie", labelKey: "moods.indie", descKey: "moods.indieDesc", icon: Sparkles, color: "text-indigo-500" },
];

// Pipeline Recommendations Component with Pagination
function PipelineRecommendations({ loading, recommendations }: { loading: boolean; recommendations: any }) {
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 12;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-accent" data-testid="loader-pipeline-recommendations" />
        <span className="ml-2 text-muted-foreground">Processing multi-stage pipeline...</span>
      </div>
    );
  }

  if (!recommendations?.recommendations?.length) {
    return (
      <div className="py-12 text-center">
        <Settings className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">No Pipeline Recommendations</h3>
        <p className="text-muted-foreground mb-6">
          Rate some movies or add titles to your watchlist to get advanced pipeline recommendations
        </p>
        <div className="flex gap-3 justify-center">
          <Link href="/movies">
            <Button data-testid="button-browse-movies-pipeline">
              <Film className="h-4 w-4 mr-2" />
              Browse Movies
            </Button>
          </Link>
          <Link href="/tv-shows">
            <Button variant="outline" data-testid="button-browse-tv-pipeline">
              <Tv className="h-4 w-4 mr-2" />
              Browse TV Shows
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  // Pagination logic
  const totalItems = recommendations.recommendations.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentItems = recommendations.recommendations.slice(startIndex, endIndex);

  return (
    <div className="space-y-6">
      {/* Pipeline Stage Info */}
      {recommendations.pipeline && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="text-center">
            <div className="text-2xl font-bold text-accent">Stage 1</div>
            <div className="text-sm text-muted-foreground mt-1">Candidate Generation</div>
            <div className="text-xs text-muted-foreground">{recommendations.pipeline.stage1}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-accent">Stage 2</div>
            <div className="text-sm text-muted-foreground mt-1">Precision Ranking</div>
            <div className="text-xs text-muted-foreground">{recommendations.pipeline.stage2}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-accent">Stage 3</div>
            <div className="text-sm text-muted-foreground mt-1">Re-ranking & Diversity</div>
            <div className="text-xs text-muted-foreground">{recommendations.pipeline.stage3}</div>
          </div>
        </div>
      )}

      {/* Recommendations Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {currentItems.map((rec: any) => {
          const movie: Movie = {
            id: rec.tmdbId.toString(),
            type: rec.mediaType || 'movie',
            title: rec.title,
            posterUrl: rec.posterPath ? tmdbService.getImageUrl(rec.posterPath, 'poster') : undefined,
            rating: rec.metadata?.vote_average || 0,
            year: rec.metadata?.release_date ? new Date(rec.metadata.release_date).getFullYear() : 0,
            genre: rec.metadata?.genres?.[0]?.name || '',
            synopsis: rec.metadata?.overview || undefined,
            director: undefined,
            cast: undefined,
            duration: rec.metadata?.runtime || undefined,
            seasons: undefined,
          };

          return (
            <MediaCard
              key={rec.tmdbId}
              movie={movie}
              showFeedback={true}
              recommendationScore={rec.score}
              recommendationStrategy={rec.strategy}
              experimentId={rec.experimentId}
            />
          );
        })}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex flex-col items-center gap-4 mt-6">
          <div className="flex items-center justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              data-testid="button-prev-page-pipeline"
            >
              Previous
            </Button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                let pageNum;
                if (totalPages <= 5) {
                  pageNum = i + 1;
                } else if (currentPage <= 3) {
                  pageNum = i + 1;
                } else if (currentPage >= totalPages - 2) {
                  pageNum = totalPages - 4 + i;
                } else {
                  pageNum = currentPage - 2 + i;
                }

                return (
                  <Button
                    key={pageNum}
                    variant={currentPage === pageNum ? "default" : "outline"}
                    size="sm"
                    onClick={() => setCurrentPage(pageNum)}
                    className="min-w-[40px]"
                    data-testid={`button-page-${pageNum}-pipeline`}
                  >
                    {pageNum}
                  </Button>
                );
              })}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              data-testid="button-next-page-pipeline"
            >
              Next
            </Button>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            Showing {startIndex + 1}-{Math.min(endIndex, totalItems)} of {totalItems} recommendations
          </div>
        </div>
      )}
    </div>
  );
}

export default function Recommendations() {
  const { t } = useTranslation();

  const moodOptions = moodOptionsDef.map(m => ({
    ...m,
    label: t(m.labelKey),
    description: t(m.descKey),
  }));

  usePageMeta({
    title: t("recommendations.title"),
    description: "Get personalized movie and TV show recommendations powered by AI on CineGraph.",
  });

  const [activeTab, setActiveTab] = useState<string>(() => {
    return sessionStorage.getItem('recommendations_activeTab') || 'chat';
  });

  const [selectedMood, setSelectedMood] = useState<string | null>(() => {
    return sessionStorage.getItem('recommendations_selectedMood') || null;
  });
  const [mediaType, setMediaType] = useState<'movie' | 'tv'>(() => {
    const saved = sessionStorage.getItem('recommendations_mediaType');
    return (saved as 'movie' | 'tv') || 'movie';
  });
  const [refreshKey, setRefreshKey] = useState(0);
  const { isInWatchlist } = useWatchlist();
  const { user, isAuthenticated } = useAuth();

  // Feedback state: dismissed IDs (persisted) + "because you liked" boosts
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => {
    try {
      const saved = sessionStorage.getItem('cg_dismissed_recs');
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch { return new Set(); }
  });
  const [likedBoosts, setLikedBoosts] = useState<{ title: string; items: any[] }[]>([]);

  const handleDislike = (tmdbId: string | number) => {
    const id = String(tmdbId);
    setDismissedIds(prev => {
      const next = new Set(prev);
      next.add(id);
      try { sessionStorage.setItem('cg_dismissed_recs', JSON.stringify([...next])); } catch {}
      return next;
    });
  };

  const handleLike = async (tmdbId: string | number, mediaType: string, title: string) => {
    try {
      const resp = await fetch(`/api/ml/similar/semantic/${tmdbId}?media_type=${mediaType}&limit=8`);
      if (!resp.ok) return;
      const data = await resp.json();
      const items = (data.similar_items || []).filter((item: any) => item.poster_path);
      if (items.length > 0) {
        setLikedBoosts(prev => {
          if (prev.some(b => b.title === title)) return prev;
          return [{ title, items }, ...prev];
        });
      }
    } catch (e) {
      console.warn('Could not fetch similar items:', e);
    }
  };

  // Persist state to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('recommendations_activeTab', activeTab);
  }, [activeTab]);

  useEffect(() => {
    if (selectedMood) {
      sessionStorage.setItem('recommendations_selectedMood', selectedMood);
    } else {
      sessionStorage.removeItem('recommendations_selectedMood');
    }
  }, [selectedMood]);

  useEffect(() => {
    sessionStorage.setItem('recommendations_mediaType', mediaType);
  }, [mediaType]);


  // Get different categories of recommendations from TMDB
  const { data: trendingData, isLoading: trendingLoading } = useQuery({
    queryKey: ['/api/tmdb/trending'],
    select: (data: any) => {
      if (!data.results) return [];
      return data.results.slice(0, 6).map((item: any) =>
        tmdbService.convertToMovie(item, item.media_type || 'movie')
      );
    }
  });

  const { data: topRatedMovies, isLoading: topRatedLoading } = useQuery({
    queryKey: ['/api/tmdb/movies/top-rated'],
    select: (data: any) => {
      if (!data.results) return [];
      return data.results.slice(0, 4).map((item: any) =>
        tmdbService.convertToMovie(item, 'movie')
      );
    }
  });

  const { data: popularMovies, isLoading: popularLoading } = useQuery({
    queryKey: ['/api/tmdb/movies/popular'],
    select: (data: any) => {
      if (!data.results) return [];
      return data.results.slice(0, 12).map((item: any) =>
        tmdbService.convertToMovie(item, 'movie')
      );
    }
  });

  const { data: popularTVShows, isLoading: tvLoading } = useQuery({
    queryKey: ['/api/tmdb/tv/popular'],
    select: (data: any) => {
      if (!data.results) return [];
      return data.results.slice(0, 12).map((item: any) =>
        tmdbService.convertToMovie(item, 'tv')
      );
    }
  });

  const handleMoodSelect = (moodId: string) => {
    setSelectedMood(selectedMood === moodId ? null : moodId);
  };

  // Remove local handlers - MovieCard will handle watchlist internally

  // TMDB-based mood recommendations for latest movies/TV shows
  const { data: moodRecommendations, isLoading: moodLoading } = useQuery({
    queryKey: ['/api/recommendations/mood', selectedMood, mediaType, refreshKey],
    enabled: !!selectedMood,
    queryFn: async () => {
      const response = await fetch(`/api/recommendations/mood/${selectedMood}?type=${mediaType}&seed=${refreshKey}`);
      if (!response.ok) throw new Error('Failed to fetch mood recommendations');
      return response.json();
    },
    select: (data: any) => {
      if (!data.recommendations) return [];
      return data.recommendations.slice(0, 8).map((item: any) =>
        tmdbService.convertToMovie(item, mediaType)
      );
    }
  });

  // Hybrid recommendations from the ML engine
  const [pipelineRefreshKey, setPipelineRefreshKey] = useState(0);
  const [diversityLevel, setDiversityLevel] = useState(0.5); // 0 = focused, 0.5 = balanced, 1 = diverse
  const { data: pipelineRecommendations, isLoading: pipelineLoading } = useQuery({
    queryKey: ['/api/recommendations/pipeline', user?.id, pipelineRefreshKey, diversityLevel],
    enabled: !!user?.id,
    queryFn: async () => {
      // Step 1: Select recommendation strategy via Contextual Bandit
      let arm = 'hybrid';
      let experimentId = null;
      try {
        const banditResp = await fetch(`/api/ml/bandit/${user?.id}/select`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
          credentials: 'include',
          body: JSON.stringify({ mood: selectedMood })
        });
        if (banditResp.ok) {
          const selection = await banditResp.json();
          arm = selection.arm_chosen || 'hybrid';
          experimentId = selection.experiment_id;
        }
      } catch (e) {
        console.warn("Bandit selection failed, fallback to hybrid strategy");
      }

      // Step 2: Fetch Base Recommendations based on the chosen arm
      let recs: any[] = [];
      const fetchBaseUrl = arm === 'collaborative' ? `/api/recommendations/collaborative/${user?.id}` : `/api/recommendations/hybrid/${user?.id}`;
      
      const baseResp = await fetch(`${fetchBaseUrl}?limit=24`);
      if (baseResp.ok) {
        const data = await baseResp.json();
        recs = data.recommendations || [];
        
        // Map scores correctly if collaborative is chosen, as it uses 'predicted_rating' vs 'score'
        if (arm === 'collaborative') {
          recs = recs.map(r => ({
            ...r,
            score: r.predicted_rating ? r.predicted_rating / 5 : 0.8
          }));
        }
      } else {
        throw new Error('Failed to fetch pipeline recommendations');
      }

      // Step 3: Apply Diversity Engine based on the diversity slider level
      if (recs.length > 0) {
        try {
          const divResp = await fetch(`/api/ml/diversity/apply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            credentials: 'include',
            body: JSON.stringify({
              candidates: recs,
              config: {
                epsilon_exploration: diversityLevel * 0.3, // mapped to slider
                serendipity_rate: diversityLevel * 0.5,
                diversity_metric: diversityLevel > 0.5 ? 'distance' : 'mmr'
              }
            })
          });
          if (divResp.ok) {
            const divData = await divResp.json();
            const diversifiedOrder = divData.diversified_results || [];
            if (diversifiedOrder.length > 0) {
              // Re-merge original metadata by tmdb_id — diversity engine may strip poster/title fields
              const recsById = new Map(recs.map((r: any) => [String(r.tmdb_id || r.id), r]));
              recs = diversifiedOrder.map((d: any) => ({
                ...recsById.get(String(d.tmdb_id || d.id)) || {},
                ...d,
                score: d.score,
              }));
            }
          }
        } catch (e) {
          console.warn("Diversity engine failed, using base recommendations");
        }
      }

      // Attach context to all recommendations for the tracker in MediaCard
      return { 
        recommendations: recs.map((r: any) => ({
          ...r, 
          strategy: arm.charAt(0).toUpperCase() + arm.slice(1), 
          experimentId: experimentId 
        }))
      };
    },
    staleTime: 10 * 60 * 1000,
    gcTime: 15 * 60 * 1000,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const getMoodBasedRecommendations = () => {
    // If no mood selected, use trending as default
    if (!selectedMood) return trendingData?.slice(0, 8) || [];

    // Start with mood recommendations if available
    const moodItems = moodRecommendations || [];

    // If we have enough mood recommendations, return 8 of them
    if (moodItems.length >= 8) {
      return moodItems.slice(0, 8);
    }

    // Otherwise, fill in with popular content of the same media type
    const fallbackItems = mediaType === 'tv'
      ? (popularTVShows || [])
      : (popularMovies || []);

    // Combine mood recommendations with fallback, ensuring no duplicates
    const combined = [...moodItems];
    const usedIds = new Set(moodItems.map((item: any) => item.id));

    for (const item of fallbackItems) {
      if (combined.length >= 8) break;
      if (!usedIds.has(item.id)) {
        combined.push(item);
        usedIds.add(item.id);
      }
    }

    return combined.slice(0, 8);
  };

  // Process pipeline recommendations into unified format
  const unifiedRecommendations = useMemo(() => {
    const combined: any[] = [];
    const seenIds = new Set<number>();

    const normalizeScore = (score: number | undefined): number => {
      if (score === undefined || score === null) return 0;
      if (score >= 0 && score <= 1) return score;
      if (score > 1 && score <= 100) return score / 100;
      if (score > 100) return 1;
      return 0;
    };

    // Add personalized hybrid/collaborative recommendations (logged-in users)
    if (pipelineRecommendations?.recommendations?.length) {
      for (const rec of pipelineRecommendations.recommendations) {
        const tmdbId = rec.tmdb_id || rec.tmdbId;
        if (!tmdbId || seenIds.has(tmdbId)) continue;
        const posterUrl = rec.poster_path ? `https://image.tmdb.org/t/p/w500${rec.poster_path}` : (rec.posterUrl || undefined);
        if (!posterUrl) continue; // Skip items with no poster
        seenIds.add(tmdbId);

        combined.push({
          id: tmdbId.toString(),
          type: rec.media_type || rec.mediaType || 'movie',
          title: rec.title,
          posterUrl,
          rating: rec.vote_average || 0,
          year: rec.release_date ? new Date(rec.release_date).getFullYear() : (rec.year || 0),
          genre: '',
          genre_ids: rec.genre_ids || [],
          synopsis: rec.overview || undefined,
          director: undefined,
          cast: undefined,
          duration: rec.runtime || undefined,
          seasons: rec.number_of_seasons || undefined,
          score: normalizeScore(rec.score),
          strategy: rec.type || 'Hybrid',
          reason: rec.reason || 'Based on your viewing history',
          source: 'hybrid',
        });
      }
    } else if (trendingData?.length) {
      // Fallback: show trending for non-logged-in users
      for (const item of trendingData.slice(0, 24)) {
        const tmdbId = Number(item.id);
        if (!tmdbId || seenIds.has(tmdbId)) continue;
        const itemPoster = item.posterUrl || (item.poster_path ? `https://image.tmdb.org/t/p/w500${item.poster_path}` : undefined);
        if (!itemPoster) continue; // Skip items with no poster
        seenIds.add(tmdbId);
        combined.push({
          ...item,
          score: normalizeScore((item.rating || 0) / 10),
          strategy: 'Trending',
          reason: 'Trending globally this week',
          source: 'trending',
        });
      }
    }

    return combined;
  }, [pipelineRecommendations, trendingData]);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <div className="mx-auto max-w-7xl w-full px-3 sm:px-4 lg:px-8 py-2 sm:py-3">
        <div className="flex items-center space-x-2 md:space-x-3 mb-2 sm:mb-3">
          <Sparkles className="h-5 w-5 sm:h-6 sm:w-6 text-accent flex-shrink-0" />
          <div>
            <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-foreground">AI-Powered Recommendations</h1>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full flex flex-col flex-1">
          <TabsList className="grid w-full grid-cols-3 mb-2 sm:mb-3 gap-0.5 sm:gap-1">
            <TabsTrigger value="chat" className="flex items-center gap-1 md:gap-2 text-xs sm:text-sm px-2 sm:px-3" data-testid="tab-ai-chat">
              <Sparkles className="h-3 w-3 md:h-4 md:w-4" />
              <span className="hidden sm:inline">AI Chat</span>
              <span className="sm:hidden">Chat</span>
            </TabsTrigger>
            <TabsTrigger value="advanced" className="flex items-center gap-1 md:gap-2 text-xs sm:text-sm px-2 sm:px-3" data-testid="tab-advanced-finder">
              <Search className="h-3 w-3 md:h-4 md:w-4" />
              <span className="hidden sm:inline">Advanced Finder</span>
              <span className="sm:hidden">Finder</span>
            </TabsTrigger>
            <TabsTrigger value="why" className="flex items-center gap-1 md:gap-2 text-xs sm:text-sm px-2 sm:px-3" data-testid="tab-why-recommend">
              <Brain className="h-3 w-3 md:h-4 md:w-4" />
              <span className="hidden sm:inline">Why We Recommend</span>
              <span className="sm:hidden">Why</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="chat" className="flex-1 mt-0">
            {/* AI Chat Interface - Full screen */}
            <AIChat className="w-full h-[calc(100dvh-10rem)] sm:h-[calc(100dvh-13rem)]" />
          </TabsContent>

          <TabsContent value="advanced">
            <AdvancedRecommendations />
          </TabsContent>


          <TabsContent value="why" className="space-y-8">
            {/* Diversity Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Settings className="h-5 w-5 text-primary" />
                  Recommendation Style
                </CardTitle>
                <CardDescription>
                  Control how adventurous your recommendations are
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-4">
                  <Slider
                    value={[diversityLevel]}
                    onValueChange={([value]) => setDiversityLevel(value)}
                    min={0}
                    max={1}
                    step={0.1}
                    className="w-full"
                    data-testid="slider-diversity"
                  />
                  <div className="flex justify-between text-xs sm:text-sm text-muted-foreground">
                    <span className="text-left max-w-[30%]">More of what I love</span>
                    <span className="text-center">Balanced</span>
                    <span className="text-right max-w-[30%]">Surprise me!</span>
                  </div>
                </div>

                {/* Current diversity level indicator */}
                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Current Level:</span>
                    <Badge variant={
                      diversityLevel >= 0.7 ? "default" :
                        diversityLevel >= 0.3 ? "secondary" :
                          "outline"
                    } data-testid="badge-diversity-level">
                      {diversityLevel >= 0.7 ? "High Diversity" :
                        diversityLevel >= 0.3 ? "Balanced" :
                          "Focused"}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {diversityLevel >= 0.7 ?
                      "High variety across genres and themes. Great for discovering new content outside your usual preferences." :
                      diversityLevel >= 0.3 ?
                        "Mix of familiar favorites and new discoveries. Balanced approach to keep things interesting." :
                        "Recommendations closely match your proven tastes. Deep dive into what you already love."}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Unified AI Recommendations */}
            <Card>
              <CardHeader>
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
                  <div className="flex-1">
                    <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
                      <Brain className="h-5 w-5 text-accent" />
                      <span>AI-Powered Recommendations</span>
                    </CardTitle>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setPipelineRefreshKey(prev => prev + 1);
                    }}
                    disabled={pipelineLoading}
                    className="w-full sm:w-auto"
                    data-testid="button-refresh-unified"
                  >
                    <RefreshCw className={cn("h-4 w-4", pipelineLoading && "animate-spin")} />
                    <span className="sm:hidden ml-2">Refresh</span>
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {pipelineLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-accent" data-testid="loader-unified-recommendations" />
                    <span className="ml-2 text-muted-foreground">Finding your perfect matches...</span>
                  </div>
                ) : unifiedRecommendations.length > 0 ? (
                  <div className="space-y-8">
                    {/* "Because you liked X" boost sections */}
                    {likedBoosts.map((boost, boostIdx) => {
                      const visibleItems = boost.items.filter(
                        (item: any) => !dismissedIds.has(String(item.tmdb_id ?? item.id))
                      );
                      if (visibleItems.length === 0) return null;
                      return (
                        <div key={boostIdx} className="space-y-3">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-sm font-semibold text-accent">
                              <ThumbsUp className="h-4 w-4" />
                              Because you liked &ldquo;{boost.title}&rdquo;
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                              onClick={() => setLikedBoosts(prev => prev.filter((_, i) => i !== boostIdx))}
                              data-testid={`button-dismiss-boost-${boostIdx}`}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                            {visibleItems.map((item: any, itemIdx: number) => {
                              const itemId = String(item.tmdb_id ?? item.id);
                              const boostMovie = {
                                id: itemId,
                                type: item.media_type || 'movie',
                                title: item.title,
                                posterUrl: item.poster_path
                                  ? `https://image.tmdb.org/t/p/w500${item.poster_path}`
                                  : undefined,
                                rating: item.vote_average || 0,
                                year: item.release_date ? new Date(item.release_date).getFullYear() : 0,
                                genre: (item.genres || [])[0] || '',
                                synopsis: item.overview || undefined,
                                score: item.similarity_score || 0,
                                strategy: 'Similar',
                                reason: item.explanation || `Similar to ${boost.title}`,
                              };
                              return (
                                <MediaCard
                                  key={`boost-${boostIdx}-${itemId}-${itemIdx}`}
                                  movie={boostMovie}
                                  showFeedback={true}
                                  recommendationScore={boostMovie.score}
                                  recommendationStrategy={boostMovie.strategy}
                                  recommendationReason={boostMovie.reason}
                                  onLike={handleLike}
                                  onDislike={handleDislike}
                                />
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}

                    {/* Main recommendation grid — filtered by dismissed IDs */}
                    {(() => {
                      const visibleRecs = unifiedRecommendations.filter(
                        (rec: any) => !dismissedIds.has(String(rec.id ?? rec.tmdbId ?? rec.movieId))
                      );
                      if (visibleRecs.length === 0) return null;
                      return (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                          {visibleRecs.map((rec: any, recIdx: number) => {
                            const rawId = rec.id ?? rec.tmdbId ?? rec.movieId;
                            if (!rawId) return null;
                            return (
                              <MediaCard
                                key={`rec-${rawId}-${recIdx}`}
                                movie={rec}
                                showFeedback={true}
                                recommendationScore={rec.score}
                                recommendationStrategy={rec.strategy}
                                recommendationReason={rec.reason}
                                experimentId={rec.experimentId}
                                showExplanation={true}
                                onLike={handleLike}
                                onDislike={handleDislike}
                              />
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="py-12 text-center">
                    <Brain className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-xl font-semibold mb-2">No Recommendations Yet</h3>
                    <p className="text-muted-foreground mb-6">
                      Rate some movies or add titles to your watchlist to get personalized AI-powered recommendations
                    </p>
                    <div className="flex gap-3 justify-center">
                      <Link href="/movies">
                        <Button data-testid="button-browse-movies">
                          <Film className="h-4 w-4 mr-2" />
                          Browse Movies
                        </Button>
                      </Link>
                      <Link href="/tv-shows">
                        <Button variant="outline" data-testid="button-browse-tv">
                          <Tv className="h-4 w-4 mr-2" />
                          Browse TV Shows
                        </Button>
                      </Link>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
