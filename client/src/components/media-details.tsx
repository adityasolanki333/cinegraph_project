import { useState, type ReactNode } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Star, Calendar, Clock, Users, ArrowLeft,
  Play, Heart, Bookmark, MessageSquare, TrendingUp, CheckCircle, Sparkles,
  Layers
} from "lucide-react";
import { usePageMeta } from "@/hooks/usePageMeta";
import { ReviewForm } from "@/components/review-form";
import { ReviewList } from "@/components/review-list";
import { VideoReviews } from "@/components/video-reviews";
import { Progress } from "@/components/ui/progress";
import { Link } from "wouter";
import { useAuth } from "@/hooks/useAuth";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useToast } from "@/hooks/use-toast";
import type { Movie } from "@shared/schema";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MediaCard } from "@/components/media-card";
import { ExpandableText } from "@/components/expandable-text";
import { apiRequest, queryClient, getAuthHeaders } from "@/lib/queryClient";
import { TrailerDialog } from "@/components/trailer-dialog";
import { AddToListButton } from "@/components/add-to-list-button";
import { ListCard } from "@/components/list-card";
import { Skeleton } from "@/components/ui/skeleton";
import { ToastAction } from "@/components/ui/toast";
import { UserRecommendationsSection } from "@/components/user-recommendations-section";

export interface MediaDetailsConfig {
  mediaType: 'movie' | 'tv';
  id: string;
  title: string;
  date: string;
  overview: string;
  durationLabel: string;
  voteAverage: number;
  voteCount: number;
  posterPath?: string;
  backdropPath?: string;
  originalLanguage?: string;
  genres: Array<{ id: number; name: string }>;
  tmdbId: number;
  cast: Array<{
    id: number;
    name: string;
    character: string;
    profile_path?: string;
  }>;
  trailers: Array<{
    id: string;
    key: string;
    name: string;
    site: string;
    type: string;
    iso_639_1?: string;
  }>;
  similarItems?: Array<{
    id: number;
    title?: string;
    name?: string;
    poster_path?: string;
    vote_average: number;
  }>;
  movieData: Movie;
  detailsTab: ReactNode;
  episodesTab?: ReactNode;
  similarTab: ReactNode;
  tabCount: number;
}

export function MediaDetails({ config }: { config: MediaDetailsConfig }) {
  const {
    mediaType, id, title, date, overview, durationLabel,
    voteAverage, voteCount, posterPath, backdropPath, originalLanguage,
    genres, tmdbId, cast, trailers, similarItems,
    movieData, detailsTab, episodesTab, similarTab, tabCount
  } = config;

  const [activeTab, setActiveTab] = useState("details");
  const { isAuthenticated, user } = useAuth();
  const { addToWatchlist, removeFromWatchlist, isInWatchlist } = useWatchlist();
  const { toast } = useToast();
  const [isTrailerOpen, setIsTrailerOpen] = useState(false);
  const [posterError, setPosterError] = useState(false);

  const { data: userReviews, refetch: refetchReviews } = useQuery({
    queryKey: ['/api/ratings', id, mediaType],
    queryFn: async () => {
      const response = await fetch(`/api/ratings?tmdbId=${id}&mediaType=${mediaType}`);
      if (!response.ok) throw new Error('Failed to fetch reviews');
      return response.json();
    },
    enabled: !!id
  });

  const userExistingRating = userReviews?.find((review: any) => String(review.userId) === String(user?.id));

  const { data: sentimentData } = useQuery({
    queryKey: ['/api/sentiment', id, mediaType],
    queryFn: async () => {
      const response = await fetch(`/api/sentiment/${id}/${mediaType}`);
      if (!response.ok) throw new Error('Failed to fetch sentiment');
      return response.json();
    },
    enabled: !!id
  });

  const { data: userFavorites } = useQuery({
    queryKey: ['/api/users', user?.id, 'favorites'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/favorites`, {
        headers: { ...getAuthHeaders() },
      });
      if (!response.ok) return [];
      const data = await response.json();
      return Array.isArray(data) ? data : (data.items || data.favorites || []);
    },
    enabled: !!user?.id
  });

  const { data: userWatched } = useQuery({
    queryKey: ['/api/users', user?.id, 'watched'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/watched`, {
        headers: { ...getAuthHeaders() },
      });
      if (!response.ok) return [];
      const data = await response.json();
      return Array.isArray(data) ? data : (data.items || data.watched || []);
    },
    enabled: !!user?.id
  });

  const { data: containingLists, isLoading: isLoadingLists } = useQuery({
    queryKey: ['/api/community/lists/containing', id, mediaType],
    queryFn: async () => {
      const response = await fetch(`/api/community/lists/containing/${id}/${mediaType}`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.lists || [];
    },
    enabled: !!id
  });

  const isInFavorites = Array.isArray(userFavorites) && userFavorites.some((fav: any) => fav.tmdbId === parseInt(id || '0'));
  const isWatched = Array.isArray(userWatched) && userWatched.some((item: any) => item.tmdbId === parseInt(id || '0'));
  const isInUserWatchlist = isInWatchlist(movieData.id);

  const favoritesMutation = useMutation({
    mutationFn: async ({ action }: { action: 'add' | 'remove' }) => {
      if (action === 'add') {
        return apiRequest('POST', `/api/users/${user?.id}/favorites/add`, {
          tmdbId: parseInt(id || '0'),
          mediaType,
          title,
          posterPath: posterPath || null
        });
      } else {
        return apiRequest('DELETE', `/api/users/${user?.id}/favorites/${id}`);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'favorites'] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [`/api/community/user-impact/${user.id}`] });
      }
    }
  });

  const watchedMutation = useMutation({
    mutationFn: async ({ action }: { action: 'add' | 'remove' }) => {
      if (action === 'add') {
        return apiRequest('POST', `/api/users/${user?.id}/watched/add`, {
          tmdbId: parseInt(id || '0'),
          mediaType,
          title,
          posterPath: posterPath || null
        });
      } else {
        return apiRequest('DELETE', `/api/users/${user?.id}/watched/${id}`);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'watched'] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [`/api/community/user-impact/${user.id}`] });
      }
    }
  });

  usePageMeta({
    title: title || (mediaType === 'movie' ? "Movie Details" : "TV Show Details"),
    description: overview?.slice(0, 160) || `View ${mediaType === 'movie' ? 'movie' : 'TV show'} details, reviews, and recommendations on CineGraph.`,
    ogImage: posterPath ? `https://image.tmdb.org/t/p/w500${posterPath}` : undefined,
    ogType: mediaType === 'movie' ? "video.movie" : "video.tv_show",
  });

  const mediaLabel = mediaType === 'movie' ? 'movie' : 'TV show';

  const handleWatchlistToggle = async () => {
    if (!isAuthenticated) {
      toast({
        title: "Please log in",
        description: "You need to be logged in to add items to your watchlist.",
        variant: "destructive",
      });
      return;
    }

    if (isInUserWatchlist) {
      const success = await removeFromWatchlist(movieData.id);
      if (success) {
        toast({
          title: "Removed from watchlist",
          description: `${title} has been removed from your watchlist.`,
        });
      }
    } else {
      const success = await addToWatchlist(movieData);
      if (success) {
        toast({
          title: "Added to watchlist",
          description: `${title} has been added to your watchlist.`,
        });
      }
    }
  };

  const handleFavoritesToggle = () => {
    if (isInFavorites) {
      favoritesMutation.mutate({ action: 'remove' }, {
        onSuccess: () => {
          toast({
            title: "Removed from favorites",
            description: `${title} has been removed from your favorites.`,
          });
        }
      });
    } else {
      favoritesMutation.mutate({ action: 'add' }, {
        onSuccess: () => {
          toast({
            title: "Added to favorites",
            description: `${title} has been added to your favorites.`,
          });
        }
      });
    }
  };

  const handleWatchedToggle = () => {
    if (isWatched) {
      watchedMutation.mutate({ action: 'remove' }, {
        onSuccess: () => {
          toast({
            title: "Removed from watched",
            description: `${title} has been removed from your watched list.`,
          });
        }
      });
    } else {
      watchedMutation.mutate({ action: 'add' }, {
        onSuccess: () => {
          toast({
            title: "Marked as watched",
            description: `${title} has been marked as watched.`,
            action: (
              <ToastAction altText="Write a review" onClick={() => {
                setActiveTab("reviews");
                window.scrollTo({ top: 500, behavior: "smooth" });
              }}>
                Write Review
              </ToastAction>
            ),
          });
        }
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className={`relative ${mediaType === 'movie' ? 'min-h-[400px] sm:min-h-[500px] md:h-96' : 'pb-4 sm:pb-6 md:pb-8'} bg-gradient-to-r from-black/70 to-black/30`}>
        {backdropPath && (
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{
              backgroundImage: `url(https://image.tmdb.org/t/p/w1280${backdropPath})`,
            }}
          />
        )}
        <div className="absolute inset-0 bg-black/60" />
        <div className={`relative ${mediaType === 'movie' ? 'z-10' : ''} container mx-auto px-3 sm:px-4 ${mediaType === 'movie' ? 'h-full flex items-center py-4 sm:py-6 md:py-0' : 'py-4 sm:py-6 md:py-8 flex items-center min-h-[400px] sm:min-h-[500px] md:min-h-96'}`}>
          <div className="flex flex-col md:flex-row gap-4 md:gap-6 items-start w-full">
            <div className="flex-shrink-0">
              <div className="w-24 h-36 sm:w-40 sm:h-60 md:w-48 md:h-72 bg-muted rounded-lg overflow-hidden">
                {posterPath && !posterError ? (
                  <img
                    src={`https://image.tmdb.org/t/p/w500${posterPath}`}
                    alt={title}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={() => setPosterError(true)}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-sm text-center p-4">{title}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex-1 text-white w-full md:w-auto">
              <Button
                variant="ghost"
                size="sm"
                className="mb-2 md:mb-4 text-white hover:text-white hover:bg-white/20"
                onClick={() => window.history.back()}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>

              <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-2">{title}</h1>

              <div className="flex flex-wrap items-center gap-2 md:gap-4 mb-3 md:mb-4">
                <div className="flex items-center gap-2">
                  <Star className="h-4 w-4 md:h-5 md:w-5 fill-yellow-400 text-yellow-400" />
                  <span className="text-base md:text-lg font-semibold">
                    {voteAverage.toFixed(1)}
                  </span>
                  <span className="text-xs md:text-sm opacity-80">
                    ({voteCount.toLocaleString()} votes)
                  </span>
                </div>

                <Separator orientation="vertical" className="h-4 md:h-6 hidden sm:block" />

                <div className="flex items-center gap-2">
                  <Calendar className="h-3 w-3 md:h-4 md:w-4" />
                  <span className="text-sm md:text-base">{date}</span>
                </div>

                <Separator orientation="vertical" className="h-4 md:h-6 hidden sm:block" />

                <div className="flex items-center gap-2">
                  <Clock className="h-3 w-3 md:h-4 md:w-4" />
                  <span className="text-sm md:text-base">{durationLabel}</span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-3 md:mb-4">
                {genres.map((genre) => (
                  <Badge key={genre.id} variant="secondary" className="text-xs">
                    {genre.name}
                  </Badge>
                ))}
              </div>

              <div className="mb-3 md:mb-6 max-w-2xl">
                <ExpandableText
                  text={overview}
                  className="text-sm md:text-lg opacity-90"
                  maxLines={2}
                />
              </div>

              <div className="space-y-2 sm:space-y-0 sm:flex sm:flex-wrap sm:gap-2 md:gap-3">
                <Button
                  size="sm"
                  className="bg-red-600 hover:bg-red-700 w-full sm:w-auto"
                  onClick={() => {
                    if (trailers.length > 0) {
                      setIsTrailerOpen(true);
                    } else {
                      toast({
                        title: "No trailer available",
                        description: `Sorry, no trailer is available for this ${mediaLabel}.`,
                        variant: "default",
                      });
                    }
                  }}
                  data-testid="button-watch-trailer"
                >
                  <Play className="h-4 w-4 md:h-5 md:w-5 mr-2" />
                  <span className="hidden sm:inline">Watch Trailer</span>
                  <span className="sm:hidden">Trailer</span>
                </Button>

                <div className="grid grid-cols-2 gap-2 sm:contents">
                  <Button
                    variant={isInFavorites ? "default" : "outline"}
                    size="sm"
                    onClick={handleFavoritesToggle}
                    disabled={favoritesMutation.isPending}
                    data-testid="button-favorites"
                    className={`w-full sm:w-auto ${isInFavorites ? 'bg-red-500 hover:bg-red-600 text-white border-red-500' : ''}`}
                  >
                    <Heart className={`h-4 w-4 md:h-5 md:w-5 mr-2 ${isInFavorites ? 'fill-current' : ''}`} />
                    <span className="hidden md:inline">{isInFavorites ? 'Favorited' : 'Add to Favorites'}</span>
                    <span className="md:hidden">{isInFavorites ? 'Favorited' : 'Favorite'}</span>
                  </Button>

                  <Button
                    variant={isInUserWatchlist ? "default" : "outline"}
                    size="sm"
                    onClick={handleWatchlistToggle}
                    data-testid="button-watchlist"
                    className={`w-full sm:w-auto ${isInUserWatchlist ? 'bg-blue-500 hover:bg-blue-600 text-white border-blue-500' : ''}`}
                  >
                    <Bookmark className={`h-4 w-4 md:h-5 md:w-5 mr-2 ${isInUserWatchlist ? 'fill-current' : ''}`} />
                    <span className="hidden md:inline">{isInUserWatchlist ? 'In Watchlist' : 'Add to Watchlist'}</span>
                    <span className="md:hidden">{isInUserWatchlist ? 'Listed' : 'Watchlist'}</span>
                  </Button>

                  <Button
                    variant={isWatched ? "default" : "outline"}
                    size="sm"
                    onClick={handleWatchedToggle}
                    disabled={watchedMutation.isPending}
                    data-testid="button-watched"
                    className={`w-full sm:w-auto ${isWatched ? 'bg-green-500 hover:bg-green-600 text-white border-green-500' : ''}`}
                  >
                    <CheckCircle className={`h-4 w-4 md:h-5 md:w-5 mr-2 ${isWatched ? 'fill-current' : ''}`} />
                    <span className="hidden md:inline">{isWatched ? 'Watched' : 'Mark as Watched'}</span>
                    <span className="md:hidden">{isWatched ? 'Watched' : 'Watch'}</span>
                  </Button>

                  <AddToListButton
                    tmdbId={tmdbId}
                    mediaType={mediaType}
                    title={title}
                    posterPath={posterPath}
                    variant="outline"
                    size="sm"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-3 sm:px-4 py-4 sm:py-6 md:py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="overflow-x-auto scrollbar-none -mx-3 px-3 sm:mx-0 sm:px-0 mb-4 sm:mb-6">
            <TabsList className={`inline-flex w-max sm:grid ${tabCount === 6 ? 'sm:grid-cols-6' : 'sm:grid-cols-5'} sm:w-full gap-1 h-auto`} data-testid="tabs-navigation">
              <TabsTrigger value="details" data-testid="tab-details" className="text-xs sm:text-sm px-3 py-2">Details</TabsTrigger>
              <TabsTrigger value="cast" data-testid="tab-cast" className="text-xs sm:text-sm px-3 py-2">Cast</TabsTrigger>
              {episodesTab && (
                <TabsTrigger value="episodes" data-testid="tab-episodes" className="text-xs sm:text-sm px-3 py-2">Episodes</TabsTrigger>
              )}
              <TabsTrigger value="reviews" data-testid="tab-reviews" className="text-xs sm:text-sm px-3 py-2">Reviews</TabsTrigger>
              <TabsTrigger value="recommendations" data-testid="tab-recommendations" className="text-xs sm:text-sm px-3 py-2">For You</TabsTrigger>
              <TabsTrigger value="similar" data-testid="tab-similar" className="text-xs sm:text-sm px-3 py-2">Similar</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="details" className="mt-4 sm:mt-6">
            {detailsTab}
          </TabsContent>

          <TabsContent value="cast" className="mt-4 sm:mt-6">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4">
              {cast.map((actor) => (
                <Card key={actor.id} className="text-center hover:shadow-lg transition-all duration-300">
                  <div className="aspect-[3/4] bg-muted m-4 rounded flex items-center justify-center">
                    {actor.profile_path ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w500${actor.profile_path}`}
                        alt={actor.name}
                        className="w-full h-full object-cover rounded"
                        loading="lazy"
                      />
                    ) : (
                      <Users className="h-8 w-8 text-muted-foreground" />
                    )}
                  </div>
                  <CardContent className="p-4">
                    <h4 className="font-semibold text-sm truncate">{actor.name}</h4>
                    <p className="text-xs text-muted-foreground truncate">
                      {actor.character}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {episodesTab && (
            <TabsContent value="episodes" className="mt-6">
              {episodesTab}
            </TabsContent>
          )}

          <TabsContent value="reviews" className="mt-6">
            <Tabs defaultValue="user-reviews" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="user-reviews" data-testid="tab-user-reviews">
                  <MessageSquare className="h-4 w-4 mr-2" />
                  User Reviews
                </TabsTrigger>
                <TabsTrigger value="video-reviews" data-testid="tab-video-reviews">
                  <Play className="h-4 w-4 mr-2" />
                  Video Reviews
                </TabsTrigger>
              </TabsList>

              <TabsContent value="user-reviews" className="mt-6">
                <div className="space-y-8">
                  {(sentimentData as any)?.aiSummary && (
                    <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <Sparkles className="h-5 w-5 text-primary" />
                          AI Review Summary
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-sm leading-relaxed">{(sentimentData as any).aiSummary}</p>
                      </CardContent>
                    </Card>
                  )}

                  {sentimentData?.summary && (sentimentData.summary.totalReviews > 0 || (sentimentData as any).sources?.tmdb > 0) && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <TrendingUp className="h-5 w-5" />
                          Audience Sentiment
                          {(sentimentData as any).sources?.tmdb > 0 && (
                            <Badge variant="secondary" className="ml-auto text-xs">
                              {(sentimentData as any).sources.tmdb} TMDB reviews
                            </Badge>
                          )}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Overall Sentiment</span>
                          <span className="text-sm">{sentimentData.summary.avgScore.toFixed(2)}</span>
                        </div>
                        <Progress
                          value={(sentimentData.summary.avgScore + 1) * 50}
                          className="w-full"
                        />

                        <div className="grid grid-cols-3 gap-4 text-center">
                          <div className="space-y-1">
                            <div className="text-green-600 font-medium text-2xl">
                              😊 {sentimentData.summary.distribution.positive}
                            </div>
                            <div className="text-xs text-muted-foreground">Positive</div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-gray-600 font-medium text-2xl">
                              😐 {sentimentData.summary.distribution.neutral}
                            </div>
                            <div className="text-xs text-muted-foreground">Neutral</div>
                          </div>
                          <div className="space-y-1">
                            <div className="text-red-600 font-medium text-2xl">
                              😞 {sentimentData.summary.distribution.negative}
                            </div>
                            <div className="text-xs text-muted-foreground">Negative</div>
                          </div>
                        </div>

                        {sentimentData.insights && Array.isArray(sentimentData.insights) && sentimentData.insights.length > 0 && (
                          <div className="p-4 bg-muted rounded-lg">
                            <div className="space-y-2">
                              {sentimentData.insights.map((insight: string, index: number) => (
                                <p key={index} className="text-sm text-muted-foreground flex items-start gap-2">
                                  <span className="text-accent mt-0.5">•</span>
                                  <span>{insight}</span>
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5" />
                        User Reviews
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {isAuthenticated ? (
                        <ReviewForm
                          tmdbId={parseInt(id || '0')}
                          mediaType={mediaType}
                          title={title}
                          posterPath={posterPath ? `https://image.tmdb.org/t/p/w500${posterPath}` : null}
                          existingRating={userExistingRating ? {
                            id: userExistingRating.id,
                            rating: userExistingRating.rating,
                            review: userExistingRating.review
                          } : undefined}
                          onSuccess={() => {
                            refetchReviews();
                            toast({ title: "Review submitted!", description: "Thank you for your feedback." });
                          }}
                        />
                      ) : !isAuthenticated ? (
                        <div className="py-4 text-center space-y-3">
                          <MessageSquare className="h-10 w-10 mx-auto text-muted-foreground" />
                          <p className="text-muted-foreground">Sign in to rate and review this {mediaLabel}</p>
                          <Link href="/login">
                            <Button size="sm">Sign In</Button>
                          </Link>
                        </div>
                      ) : null}
                      <Separator />
                      <ReviewList
                        tmdbId={parseInt(id || '0')}
                        mediaType={mediaType}
                        currentUserId={user?.id}
                        sentimentMap={Object.fromEntries(
                          ((sentimentData as any)?.reviews || []).map((r: any) => [
                            r.id,
                            { sentiment: r.sentiment, sentimentScore: r.sentimentScore }
                          ])
                        )}
                      />
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>

              <TabsContent value="video-reviews" className="mt-6">
                <div className="space-y-6">
                  <VideoReviews
                    title={title}
                    mediaType={mediaType}
                  />
                </div>
              </TabsContent>
            </Tabs>
          </TabsContent>

          <TabsContent value="recommendations" className="mt-6">
            <UserRecommendationsSection
              forTmdbId={parseInt(id || '0')}
              forMediaType={mediaType}
              currentUserId={user?.id}
              isAuthenticated={isAuthenticated}
            />
          </TabsContent>

          <TabsContent value="similar" className="mt-6">
            <Tabs defaultValue={mediaType === 'movie' ? 'tmdb' : 'shows'} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value={mediaType === 'movie' ? 'tmdb' : 'shows'} data-testid={mediaType === 'movie' ? 'tab-tmdb-similar' : 'tab-similar-shows'}>
                  {mediaType === 'movie' ? 'Similar Movies' : 'Similar Shows'}
                </TabsTrigger>
                <TabsTrigger value="lists" data-testid="tab-similar-lists">Lists</TabsTrigger>
                <TabsTrigger value="ai-similar" data-testid="tab-ai-similar"><Sparkles className="h-4 w-4 mr-1 inline" />AI Similar</TabsTrigger>
              </TabsList>

              <TabsContent value={mediaType === 'movie' ? 'tmdb' : 'shows'} className="mt-6">
                {similarItems && similarItems.length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6" data-testid={mediaType === 'movie' ? 'grid-tmdb-similar' : 'grid-similar-shows'}>
                    {similarItems.slice(0, 8).map((item) => (
                      <MediaCard
                        key={item.id}
                        item={{
                          id: item.id,
                          ...(mediaType === 'movie' ? { title: item.title } : { name: item.name }),
                          vote_average: item.vote_average,
                          poster_path: item.poster_path,
                          type: mediaType
                        }}
                        mediaType={mediaType}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12" data-testid={mediaType === 'movie' ? 'empty-tmdb-similar' : 'empty-similar-shows'}>
                    <div className="text-muted-foreground mb-4">No similar {mediaType === 'movie' ? 'movies' : 'shows'} found.</div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="lists" className="mt-6">
                <div className="flex items-center gap-2 mb-6">
                  <Layers className="h-5 w-5 text-primary" />
                  <h2 className="text-2xl font-bold" data-testid="heading-similar-lists">
                    Lists Featuring This {mediaType === 'movie' ? 'Movie' : 'Show'}
                  </h2>
                </div>
                {isLoadingLists ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="loading-similar-lists">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-80" data-testid={`skeleton-list-${i}`} />
                    ))}
                  </div>
                ) : containingLists && containingLists.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="grid-similar-lists">
                    {containingLists.map((list: any) => (
                      <ListCard key={list.id} list={list} />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12" data-testid="empty-similar-lists">
                    <div className="text-muted-foreground mb-4">
                      This {mediaLabel} hasn't been added to any public lists yet.
                    </div>
                  </div>
                )}
              </TabsContent>

              <TabsContent value="ai-similar" className="mt-6">
                {similarTab}
              </TabsContent>
            </Tabs>
          </TabsContent>
        </Tabs>
      </div>

      <TrailerDialog
        isOpen={isTrailerOpen}
        onClose={() => setIsTrailerOpen(false)}
        trailers={trailers}
        title={title}
        originalLanguage={originalLanguage}
      />
    </div>
  );
}
