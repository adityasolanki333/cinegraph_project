import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { RatingStars } from "./rating-stars";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";
import type { InsertRating } from "@shared/schema";

export function OnboardingWizard() {
  const { user, isAuthenticated } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [isOpen, setIsOpen] = useState(false);
  const [ratedMovies, setRatedMovies] = useState<Set<number>>(new Set());
  const REQUIRED_RATINGS = 5;

  // 1. Check local storage and user ratings backend
  const { data: userRatings, isLoading: isLoadingRatings } = useQuery({
    queryKey: ['/api/users', user?.id, 'ratings'],
    queryFn: async () => {
      if (!user?.id) return [];
      const res = await fetch(`/api/users/${user.id}/reviews`);
      if (!res.ok) throw new Error("Failed");
      const data = await res.json();
      return data.reviews || data.ratings || (Array.isArray(data) ? data : []);
    },
    enabled: isAuthenticated && !!user?.id,
  });

  useEffect(() => {
    if (!isAuthenticated || !user?.id || isLoadingRatings) return;
    
    // Check if dismissed
    const hasOnboarded = localStorage.getItem(`onboarded_${user.id}`);
    if (hasOnboarded) return;

    // Check if they need onboarding
    if (userRatings && userRatings.length < REQUIRED_RATINGS) {
      setIsOpen(true);
    } else if (userRatings && userRatings.length >= REQUIRED_RATINGS) {
      localStorage.setItem(`onboarded_${user.id}`, "true");
    }
  }, [isAuthenticated, user?.id, userRatings, isLoadingRatings]);

  // 2. Fetch popular movies for them to rate
  const { data: popularMoviesResponse, isLoading: isLoadingMovies } = useQuery({
    queryKey: ['/api/movies/popular', 1],
    queryFn: async () => {
      const res = await fetch(`/api/tmdb/movie/popular`);
      if (!res.ok) throw new Error("Failed");
      return await res.json();
    },
    enabled: isOpen,
  });
  
  const movies = popularMoviesResponse?.results || [];

  // 3. Handle rating a movie
  const rateMutation = useMutation({
    mutationFn: async (data: InsertRating) => {
      const response = await fetch("/api/ratings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      if (!response.ok) throw new Error("Failed");
      return response.json();
    },
    onSuccess: (_, variables) => {
      setRatedMovies(prev => new Set(prev).add(variables.tmdbId));
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'ratings'] });
    },
    onError: () => {
      toast({ title: "Failed to save rating", variant: "destructive" });
    }
  });

  const handleRate = (movie: any, score: number) => {
    // Only rate if we haven't already locally rated it to prevent double tapping
    if (ratedMovies.has(movie.id)) return;
    
    rateMutation.mutate({
      tmdbId: movie.id,
      mediaType: "movie",
      title: movie.title,
      posterPath: movie.poster_path,
      rating: score,
    });
  };

  const handleFinish = () => {
    localStorage.setItem(`onboarded_${user?.id}`, "true");
    setIsOpen(false);
    toast({
      title: "Welcome aboard!",
      description: "Your personalized recommendations are ready.",
    });
  };

  const handleSkip = () => {
    localStorage.setItem(`onboarded_${user?.id}`, "true");
    setIsOpen(false);
  };
  
  // Calculate progress
  // Safely fallback to 0 if loading, but baseRatings provides the existing baseline DB count
  const baseRatings = userRatings?.length || 0;
  const newRatings = ratedMovies.size;
  const currentTotal = baseRatings + newRatings;
  const progress = Math.min(100, Math.round((currentTotal / REQUIRED_RATINGS) * 100));
  const isComplete = currentTotal >= REQUIRED_RATINGS;

  return (
    <AlertDialog open={isOpen}>
      <AlertDialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-0 overflow-hidden sm:rounded-2xl">
        <div className="p-6 pb-2 shrink-0 border-b bg-card">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl sm:text-2xl">Personalize your feed ✨</AlertDialogTitle>
            <AlertDialogDescription className="text-sm sm:text-base">
              Rate {REQUIRED_RATINGS} movies you've seen to kickstart your personalized AI recommendations!
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          <div className="mt-4 mb-2 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-muted-foreground">Progress: {Math.min(currentTotal, REQUIRED_RATINGS)} / {REQUIRED_RATINGS}</span>
              <span className="font-medium text-emerald-500">{progress}%</span>
            </div>
            <Progress value={progress} className="h-2 w-full bg-muted" />
          </div>
        </div>

        <ScrollArea className="flex-1 p-4 sm:p-6 bg-muted/20">
          {isLoadingMovies ? (
            <div className="flex flex-col justify-center items-center py-20 gap-4">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-muted-foreground">Retrieving popular films...</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 min-[500px]:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
              {movies.map((movie: any) => {
                // Determine if already rated
                const dbRated = userRatings?.some((r: any) => r.tmdbId === movie.id);
                const justRated = ratedMovies.has(movie.id);
                const isRated = dbRated || justRated;

                return (
                  <div 
                    key={movie.id} 
                    className={`flex flex-col p-2 bg-card rounded-xl border transition-all duration-300 ${isRated ? 'opacity-60 scale-[0.98] bg-emerald-500/5 border-emerald-500/20' : 'hover:border-primary hover:shadow-md'}`}
                  >
                    <div className="relative aspect-[2/3] w-full rounded-md overflow-hidden bg-muted">
                      {movie.poster_path ? (
                        <img 
                          src={`https://image.tmdb.org/t/p/w300${movie.poster_path}`} 
                          alt={movie.title}
                          className="w-full h-full object-cover transition-transform hover:scale-105"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center p-2 text-center text-xs">
                          {movie.title}
                        </div>
                      )}
                      
                      {isRated && (
                        <div className="absolute inset-0 bg-black/40 flex items-center justify-center backdrop-blur-[1px]">
                          <div className="bg-emerald-500 text-white rounded-full p-2">
                            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 mt-2">
                      <h3 className="text-xs sm:text-sm font-semibold line-clamp-1" title={movie.title}>{movie.title}</h3>
                      <p className="text-[10px] text-muted-foreground">{movie.release_date?.substring(0, 4)}</p>
                    </div>
                    
                    <div className="mt-2 flex justify-center py-1">
                      {isRated ? (
                        <span className="text-xs font-medium text-emerald-500 flex items-center gap-1">
                          Rated
                        </span>
                      ) : (
                        <div className="scale-75 origin-left w-full hover:scale-100 transition-transform">
                          <RatingStars 
                            rating={0} 
                            size="sm"
                            showValue={false} 
                            onRatingChange={(score) => handleRate(movie, score)} 
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </ScrollArea>

        <div className="p-4 sm:p-6 shrink-0 bg-card border-t flex items-center justify-between shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.1)] z-10">
          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-foreground" onClick={handleSkip}>
            Skip for now
          </Button>
          <Button 
            onClick={handleFinish} 
            disabled={!isComplete}
            className={isComplete ? "bg-emerald-500 hover:bg-emerald-600 text-white animate-in zoom-in slide-in-from-bottom-[5px] duration-300" : "opacity-70"}
          >
            {isComplete ? "Take me to App" : `Rate ${Math.max(0, REQUIRED_RATINGS - currentTotal)} more`}
          </Button>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
