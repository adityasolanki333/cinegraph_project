import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Star, Plus, Check, Heart, Play, LogIn, ThumbsUp, ThumbsDown, Trash2, Info } from "lucide-react";
import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useToast } from "@/hooks/use-toast";
import { TrailerDialog } from "@/components/trailer-dialog";
import { ExplanationDialog } from "@/components/explanation-dialog";
import { apiRequest } from "@/lib/queryClient";
import type { Movie } from "@shared/schema";
import { ChevronUp, Brain } from "lucide-react";

const TMDB_GENRE_MAP: Record<number, string> = {
  28: 'Action', 12: 'Adventure', 16: 'Animation', 35: 'Comedy', 80: 'Crime',
  99: 'Documentary', 18: 'Drama', 10751: 'Family', 14: 'Fantasy', 36: 'History',
  27: 'Horror', 10402: 'Music', 9648: 'Mystery', 10749: 'Romance',
  878: 'Sci-Fi', 10770: 'TV Movie', 53: 'Thriller', 10752: 'War', 37: 'Western',
  10759: 'Action & Adventure', 10762: 'Kids', 10763: 'News', 10764: 'Reality',
  10765: 'Sci-Fi & Fantasy', 10766: 'Soap', 10767: 'Talk', 10768: 'War & Politics',
};

export interface MediaItem {
  id: number | string;
  title?: string;
  name?: string;
  rating?: number;
  vote_average?: number;
  year?: string | number;
  first_air_date?: string;
  last_air_date?: string;
  release_date?: string;
  genre?: string;
  genres?: Array<{ id: number; name: string }>;
  genre_ids?: number[];
  duration?: number;
  number_of_seasons?: number;
  synopsis?: string;
  overview?: string;
  poster_path?: string;
  posterUrl?: string;
  type?: 'movie' | 'tv';
  media_type?: 'movie' | 'tv';
  seasons?: number;
}

export interface MediaCardProps {
  item?: MediaItem;
  movie?: any;
  mediaType?: 'movie' | 'tv';
  isInWatchlist?: boolean;
  onAddToWatchlist?: (itemId: string) => void;
  onRemoveFromWatchlist?: (itemId: string) => void;
  onRate?: (itemId: string, rating: number) => void;
  userRating?: number;
  showRemoveButton?: boolean;
  showFeedback?: boolean;
  recommendationStrategy?: string;
  recommendationScore?: number;
  recommendationReason?: string;
  experimentId?: string;
  showExplanation?: boolean;
  priority?: boolean;
  children?: React.ReactNode;
}

export function MediaCard({
  item: propItem,
  movie: propMovie,
  mediaType,
  isInWatchlist: propIsInWatchlist,
  onAddToWatchlist,
  onRemoveFromWatchlist,
  onRate,
  userRating,
  showRemoveButton = false,
  showFeedback = false,
  recommendationStrategy,
  recommendationScore,
  recommendationReason,
  experimentId,
  priority = false,
  showExplanation = false,
  children,
}: MediaCardProps) {
  const item = propItem || propMovie;
  if (!item) return null;

  const type = mediaType || item.type || item.media_type || (item.name ? 'tv' : 'movie');
  const title = item.title || item.name || 'Untitled';
  const rating = item.rating || item.vote_average || 0;

  let yearStr = item.year || '';
  if (!yearStr) {
    if (type === 'tv') {
      if (item.last_air_date) {
        yearStr = new Date(item.last_air_date).getFullYear().toString();
      } else if (item.first_air_date) {
        yearStr = new Date(item.first_air_date).getFullYear().toString();
      }
    } else if (item.release_date) {
      yearStr = new Date(item.release_date).getFullYear().toString();
    }
  }

  const synopsis = item.synopsis || item.overview || '';
  const posterUrl = item.posterUrl || (item.poster_path ? `https://image.tmdb.org/t/p/w342${item.poster_path}` : undefined);
  const genreDisplay = item.genre
    || (item.genres && item.genres.length > 0 ? item.genres[0].name : '')
    || (item.genre_ids && item.genre_ids.length > 0 ? TMDB_GENRE_MAP[item.genre_ids[0]] || '' : '');

  const movie = {
    id: item.id.toString(),
    title: title,
    year: parseInt(yearStr) || new Date().getFullYear(),
    genre: genreDisplay || 'Unknown',
    rating: rating,
    synopsis: synopsis,
    posterUrl: posterUrl,
    type: type,
    seasons: item.number_of_seasons || item.seasons || undefined,
    duration: item.duration || undefined,
  };
  const [hoveredRating, setHoveredRating] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isTrailerOpen, setIsTrailerOpen] = useState(false);
  const [shouldFetchTrailer, setShouldFetchTrailer] = useState(false);
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<'positive' | 'negative' | null>(null);
  const [, setLocation] = useLocation();
  const { isAuthenticated, user } = useAuth();
  const { addToWatchlist, removeFromWatchlist, isInWatchlist: hookIsInWatchlist } = useWatchlist();
  const { toast } = useToast();

  // Use the hook's watchlist state if no prop is provided
  const isInWatchlist = propIsInWatchlist ?? hookIsInWatchlist(movie.id);

  // Fetch trailer data when needed
  const { data: trailerData, isLoading: trailerLoading } = useQuery({
    queryKey: ['/api/tmdb', movie.type, movie.id],
    enabled: shouldFetchTrailer && !!movie.id,
  });

  // Extract trailers from the API response
  const trailers = (trailerData as any)?.videos?.results?.filter((video: any) =>
    video.type === 'Trailer' && video.site === 'YouTube'
  ) || [];

  const handleWatchlistToggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast({
        title: "Please log in",
        description: "You need to be logged in to add items to your watchlist.",
        variant: "destructive",
      });
      setTimeout(() => setLocation('/login'), 500);
      return;
    }

    if (isInWatchlist) {
      // Remove from watchlist
      if (onRemoveFromWatchlist) {
        onRemoveFromWatchlist(movie.id);
      } else {
        const success = await removeFromWatchlist(movie.id);
        if (success) {
          toast({
            title: "Removed from watchlist",
            description: `${movie.title} has been removed from your watchlist.`,
          });
        }
      }
    } else {
      // Add to watchlist
      if (onAddToWatchlist) {
        onAddToWatchlist(movie.id);
      } else {
        const success = await addToWatchlist(movie);
        if (success) {
          toast({
            title: "Added to watchlist",
            description: `${movie.title} has been added to your watchlist.`,
          });
        }
      }
    }
  };

  const handleRating = (rating: number) => {
    if (onRate) {
      onRate(movie.id, rating);
    }
  };

  // Feedback mutation for like/dislike
  const feedbackMutation = useMutation({
    mutationFn: async (outcomeType: "preference_positive" | "preference_negative") => {
      if (experimentId) {
        return apiRequest("POST", `/api/ml/bandit/reward`, {
          experiment_id: experimentId,
          outcome_type: outcomeType
        });
      }

      return apiRequest("POST", `/api/ml/recommendations/interaction`, {
        recommendation_id: `${movie.id}-${movie.type}`,
        user_id: user?.id,
        interaction_type: outcomeType === "preference_positive" ? "rated_high" : "dismissed"
      });
    },
    onSuccess: (_, outcomeType) => {
      setFeedbackGiven(outcomeType === "preference_positive" ? 'positive' : 'negative');
      toast({
        title: "Feedback received!",
        description: outcomeType === "preference_positive"
          ? "Thanks! We'll recommend more like this."
          : "Thanks! We'll adjust future recommendations.",
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to submit feedback. Please try again.",
        variant: "destructive",
      });
    }
  });

  const [isVisible, setIsVisible] = useState(true);

  const handleFeedback = (positive: boolean) => {
    const outcomeType = positive ? "preference_positive" : "preference_negative";
    feedbackMutation.mutate(outcomeType);

    // Optimistically hide the card if user dislikes the recommendation
    if (!positive) {
      // Small delay to let the user see the click animation
      setTimeout(() => setIsVisible(false), 300);

      toast({
        title: "Recommendation Removed",
        description: "We won't show this to you again.",
      });
    }
  };

  const handlePlayTrailer = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Trigger trailer data fetch
    setShouldFetchTrailer(true);
  };

  // Open trailer dialog when data is loaded
  useEffect(() => {
    if (shouldFetchTrailer && !trailerLoading && trailerData) {
      if (trailers.length > 0) {
        setIsTrailerOpen(true);
        setShouldFetchTrailer(false);
      } else {
        toast({
          title: "No trailer available",
          description: `Sorry, no trailer is available for ${movie.title}.`,
          variant: "destructive",
        });
        setShouldFetchTrailer(false);
      }
    }
  }, [shouldFetchTrailer, trailerLoading, trailerData, trailers.length, toast, movie.title]);

  const renderStars = (rating: number, interactive = false) => {
    return Array.from({ length: 5 }, (_, i) => {
      const starValue = i + 1;
      const isFilled = starValue <= rating;

      return (
        <Star
          key={i}
          className={cn(
            "h-3 w-3 sm:h-4 sm:w-4 transition-colors",
            isFilled ? "fill-rating text-rating" : "text-muted-foreground",
            interactive && "cursor-pointer hover:text-rating"
          )}
          onMouseEnter={() => interactive && setHoveredRating(starValue)}
          onMouseLeave={() => interactive && setHoveredRating(0)}
          onClick={() => interactive && handleRating(starValue)}
        />
      );
    });
  };

  if (!isVisible) return null;

  return (
    <>
      <Link href={`${movie.type === 'tv' ? '/tv' : '/movie'}/${movie.id}`}>
        <Card
          className="movie-card group overflow-hidden border-border bg-card cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-300 ease-out"
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <div className="relative aspect-[2/3] overflow-hidden">
            <img
              src={movie.posterUrl || `https://images.unsplash.com/photo-1489599558473-7636b88d6e6a?ixlib=rb-4.0.3&w=400&h=600&fit=crop`}
              alt={movie.title}
              loading={priority ? "eager" : "lazy"}
              fetchpriority={priority ? "high" : "auto"}
              className="w-full h-full object-cover transition-all duration-500 ease-out group-hover:scale-110 group-hover:brightness-75"
            />

            {/* Overlay with actions */}
            {isHovered && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <div className="flex space-x-1 sm:space-x-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    className="bg-white/20 hover:bg-white/30 text-xs sm:text-sm px-2 sm:px-3 h-7 sm:h-9"
                    onClick={handlePlayTrailer}
                    data-testid="button-play-trailer"
                  >
                    <Play className="h-3 w-3 sm:h-4 sm:w-4 sm:mr-1" />
                    <span className="hidden sm:inline">Play</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleWatchlistToggle}
                    className="bg-white/20 hover:bg-white/30 px-2 sm:px-3 h-7 sm:h-9"
                  >
                    {isInWatchlist ? (
                      <Check className="h-3 w-3 sm:h-4 sm:w-4" />
                    ) : (
                      <Plus className="h-3 w-3 sm:h-4 sm:w-4" />
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Type badge */}
            <Badge variant="secondary" className="absolute top-1 left-1 sm:top-2 sm:left-2 text-[10px] sm:text-xs px-1.5 sm:px-2.5 py-0.5">
              {movie.type === "tv" ? (movie.seasons ? `${movie.seasons} Season${movie.seasons !== 1 ? 's' : ''}` : "TV Series") : "Movie"}
            </Badge>

            {/* Recommendation Strategy Badge */}
            {recommendationStrategy && (
              <Badge
                variant="outline"
                className="absolute top-1 right-1 sm:top-2 sm:right-2 text-[10px] sm:text-xs px-1.5 sm:px-2.5 py-0.5 bg-primary/90 text-primary-foreground border-primary"
                data-testid="badge-strategy"
              >

                <div className="truncate max-w-[80px] sm:max-w-[100px]">
                  {recommendationStrategy}
                </div>
              </Badge>
            )}

            {/* Remove button for watchlist */}
            {showRemoveButton && (
              <Button
                size="sm"
                variant="destructive"
                className="absolute top-2 right-2 h-8 w-8 p-0"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onRemoveFromWatchlist?.(movie.id);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>

          <CardContent className="p-2 sm:p-3 md:p-4 whitespace-normal">
            <h3 className="font-semibold text-xs sm:text-sm text-foreground group-hover:text-primary transition-colors line-clamp-2 min-h-[2.8rem] sm:min-h-[2.5rem] break-words">
              {movie.title}
            </h3>

            {/* Match Score (for recommendations) */}
            {recommendationScore !== undefined && (
              <div className="flex items-center gap-1 mt-1 sm:mt-2">
                <span className="text-[10px] sm:text-xs font-medium text-primary flex-shrink-0">🎯 Match:</span>

                {recommendationReason ? (
                  <TooltipProvider>
                    <Tooltip delayDuration={0}>
                      <TooltipTrigger asChild>
                        <Badge variant="secondary" className="text-[10px] sm:text-xs font-semibold cursor-help hover:bg-primary/20 transition-colors">
                          {(Math.min(recommendationScore, 1) * 100).toFixed(0)}%
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent side="right" className="max-w-[200px] text-xs">
                        <p className="font-semibold mb-1">Why Recommended?</p>
                        <p>{recommendationReason}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ) : (
                  <Badge variant="secondary" className="text-[10px] sm:text-xs font-semibold">
                    {(Math.min(recommendationScore, 1) * 100).toFixed(0)}%
                  </Badge>
                )}
              </div>
            )}



            {/* TMDB Rating */}
            <div className="flex items-center justify-between mt-1 sm:mt-2">
              <div className="flex items-center space-x-0.5 sm:space-x-1">
                {renderStars(Math.round((movie.rating || 7.0) / 2))}
                <span className="text-[10px] sm:text-sm text-muted-foreground ml-0.5 sm:ml-1">
                  {(movie.rating || 7.0).toFixed(1)}
                </span>
                {recommendationScore !== undefined && (
                  <span className="text-[9px] sm:text-xs text-muted-foreground/60 ml-0.5">TMDB</span>
                )}
              </div>
            </div>

            {/* User rating */}
            {onRate && (
              <div className="flex items-center space-x-1 mt-1 sm:mt-2">
                <span className="text-[10px] sm:text-xs text-muted-foreground">Your rating:</span>
                <div className="flex items-center space-x-0.5 sm:space-x-1">
                  {renderStars(hoveredRating || userRating || 0, true)}
                </div>
              </div>
            )}

            {/* Movie info */}
            <div className="flex items-center gap-1 mt-1 sm:mt-2 text-[10px] sm:text-xs text-muted-foreground">
              <span className="flex-1 min-w-0 truncate">
                {movie.year}{movie.genre ? ` • ${movie.genre}` : ''}
              </span>
              {movie.duration && (
                <span className="flex-shrink-0">{movie.duration}min</span>
              )}
            </div>

            {/* Synopsis */}
            {movie.synopsis && (
              <p className="text-[10px] sm:text-xs text-muted-foreground mt-1 sm:mt-2 line-clamp-2 break-words">
                {movie.synopsis}
              </p>
            )}

            {/* AI Explanation Toggle (Opens Dialog) - Only for recommendations with reason */}
            {showExplanation && (recommendationReason || recommendationScore !== undefined) && (
              <div className="mt-2" onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs h-7 gap-1.5 px-2 bg-primary/10 hover:bg-primary/20 text-primary border-primary/20 justify-start font-medium transition-all duration-300 overflow-hidden"
                  onClick={() => setIsExplanationOpen(true)}
                >
                  <Brain className="h-3.5 w-3.5 flex-shrink-0" />
                  <span className="truncate">AI Analysis</span>
                  <ChevronUp className="h-3.5 w-3.5 ml-auto flex-shrink-0 opacity-50 rotate-90" />
                </Button>
              </div>
            )}

            {/* Like/Dislike Feedback */}
            {showFeedback && isAuthenticated && (
              <div className="mt-2">
                {feedbackGiven ? (
                  <p className="text-[10px] sm:text-xs text-green-600 dark:text-green-400 text-center py-1" data-testid="text-feedback-thanks">
                    ✓ Thanks for your feedback!
                  </p>
                ) : (
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleFeedback(true);
                      }}
                      disabled={feedbackMutation.isPending}
                      className="flex-1 text-xs h-7"
                      data-testid="button-feedback-like"
                    >
                      <ThumbsUp className="h-3 w-3 mr-1" />
                      Like
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleFeedback(false);
                      }}
                      disabled={feedbackMutation.isPending}
                      className="flex-1 text-xs h-7"
                      data-testid="button-feedback-dislike"
                    >
                      <ThumbsDown className="h-3 w-3 mr-1" />
                      Dislike
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </Link>
      {children && (
        <div className="mt-2" onClick={(e) => e.preventDefault()}>
          {children}
        </div>
      )}

      {/* Trailer Dialog */}
      <TrailerDialog
        isOpen={isTrailerOpen}
        onClose={() => setIsTrailerOpen(false)}
        trailers={trailers}
        title={movie.title}
        originalLanguage={(trailerData as any)?.original_language}
      />

      {/* Explanation Dialog */}
      <ExplanationDialog
        isOpen={isExplanationOpen}
        onClose={() => setIsExplanationOpen(false)}
        movie={movie}
        initialReason={recommendationReason}
      />

    </>
  );
}
