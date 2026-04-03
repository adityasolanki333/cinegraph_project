import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AlertDialog,
  AlertDialogContent,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { Loader2, ThumbsUp, ThumbsDown, Sparkles, Star, ChevronRight } from "lucide-react";

const REQUIRED = 5;
type Decision = "liked" | "disliked";

export function OnboardingWizard() {
  const { user, isAuthenticated } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [isOpen, setIsOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [decisions, setDecisions] = useState<Array<{ movie: any; decision: Decision }>>([]);
  const [animating, setAnimating] = useState<"left" | "right" | null>(null);
  const [isPending, setIsPending] = useState(false);

  const decided = decisions.length;
  const isComplete = decided >= REQUIRED;

  // Check onboarding status
  const { data: userReviews, isLoading: loadingReviews } = useQuery({
    queryKey: ["/api/users", user?.id, "reviews-onboard"],
    queryFn: async () => {
      const res = await fetch(`/api/users/${user!.id}/reviews`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.reviews || (Array.isArray(data) ? data : []);
    },
    enabled: isAuthenticated && !!user?.id,
  });

  const { data: userFavorites, isLoading: loadingFavs } = useQuery({
    queryKey: ["/api/users", user?.id, "favorites-onboard"],
    queryFn: async () => {
      const res = await fetch(`/api/users/${user!.id}/favorites`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.favorites || (Array.isArray(data) ? data : []);
    },
    enabled: isAuthenticated && !!user?.id,
  });

  useEffect(() => {
    if (!isAuthenticated || !user?.id || loadingReviews || loadingFavs) return;
    if (localStorage.getItem(`onboarded_${user.id}`)) return;
    const existing = (userReviews?.length || 0) + (userFavorites?.length || 0);
    if (existing < REQUIRED) setIsOpen(true);
    else localStorage.setItem(`onboarded_${user.id}`, "true");
  }, [isAuthenticated, user?.id, userReviews, userFavorites, loadingReviews, loadingFavs]);

  // Fetch mix of popular + top-rated
  const { data: movies = [], isLoading: loadingMovies } = useQuery({
    queryKey: ["/api/tmdb/onboarding-pool"],
    queryFn: async () => {
      const [pop, top] = await Promise.all([
        fetch("/api/tmdb/movies/popular").then(r => r.json()),
        fetch("/api/tmdb/movies/top-rated").then(r => r.json()),
      ]);
      const all = [...(pop.results || []), ...(top.results || [])];
      const seen = new Set<number>();
      return all.filter(m => {
        if (seen.has(m.id) || !m.poster_path) return false;
        seen.add(m.id);
        return true;
      }).slice(0, 20);
    },
    enabled: isOpen,
    staleTime: Infinity,
  });

  const favMutation = useMutation({
    mutationFn: async (movie: any) => {
      const res = await fetch("/api/favorites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tmdbId: movie.id, mediaType: "movie", title: movie.title, posterPath: movie.poster_path }),
      });
      if (!res.ok) throw new Error();
    },
  });

  const reviewMutation = useMutation({
    mutationFn: async (movie: any) => {
      const res = await fetch("/api/ratings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tmdbId: movie.id, mediaType: "movie", title: movie.title, posterPath: movie.poster_path, rating: 2 }),
      });
      if (!res.ok) throw new Error();
    },
  });

  const handleDecision = async (decision: Decision) => {
    if (animating || isPending || currentIndex >= movies.length) return;
    const movie = movies[currentIndex];
    const dir = decision === "liked" ? "right" : "left";

    setAnimating(dir);
    setIsPending(true);

    // Fire-and-forget API call
    if (decision === "liked") favMutation.mutateAsync(movie).catch(() => {});
    else reviewMutation.mutateAsync(movie).catch(() => {});

    await new Promise(r => setTimeout(r, 350));
    setDecisions(prev => [...prev, { movie, decision }]);
    setCurrentIndex(i => i + 1);
    setAnimating(null);
    setIsPending(false);
  };

  const handleFinish = () => {
    localStorage.setItem(`onboarded_${user?.id}`, "true");
    setIsOpen(false);
    queryClient.invalidateQueries({ queryKey: ["/api/recommendations/hybrid"] });
    queryClient.invalidateQueries({ queryKey: ["/api/users", user?.id, "favorites"] });
    toast({ title: "Your feed is ready! 🎬", description: "Personalised recommendations are on their way." });
  };

  const handleSkip = () => {
    localStorage.setItem(`onboarded_${user?.id}`, "true");
    setIsOpen(false);
  };

  const currentMovie = movies[currentIndex];
  const nextMovie = movies[currentIndex + 1];

  const dotColors = Array.from({ length: REQUIRED }, (_, i) => {
    const d = decisions[i];
    if (!d) return "bg-muted";
    return d.decision === "liked" ? "bg-emerald-500" : "bg-red-400";
  });

  return (
    <AlertDialog open={isOpen}>
      <AlertDialogContent className="max-w-sm w-full p-0 overflow-hidden sm:rounded-2xl gap-0 border-0 shadow-2xl">

        {/* Header */}
        <div className="px-5 pt-5 pb-3 bg-gradient-to-b from-primary/10 to-background text-center">
          <div className="flex items-center justify-center gap-1.5 mb-0.5">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="font-bold text-base">Personalize your feed</span>
          </div>
          <p className="text-xs text-muted-foreground">
            {isComplete
              ? "Great taste! Your AI feed is ready 🎉"
              : `Rate ${REQUIRED} movies you know to get started`}
          </p>

          {/* Progress dots */}
          <div className="flex items-center justify-center gap-2 mt-3">
            {dotColors.map((color, i) => (
              <div
                key={i}
                className={`rounded-full transition-all duration-300 ${color} ${i === decided && !isComplete ? "w-4 h-3 ring-2 ring-primary/40" : "w-2.5 h-2.5"}`}
              />
            ))}
          </div>
        </div>

        {/* Card area */}
        <div className="relative bg-background px-5 pt-3 pb-4" style={{ minHeight: 420 }}>
          {loadingMovies ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading movies…</p>
            </div>
          ) : isComplete ? (
            /* Completion screen */
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-6 text-center">
              <div className="text-5xl">🎬</div>
              <div>
                <p className="font-bold text-lg mb-1">All set!</p>
                <p className="text-sm text-muted-foreground">
                  We've noted your picks. Your recommendations are being personalised right now.
                </p>
              </div>
              <div className="flex flex-wrap justify-center gap-2 mt-1">
                {decisions.map(({ movie, decision }) => (
                  <div key={movie.id} className="relative">
                    <img
                      src={`https://image.tmdb.org/t/p/w92${movie.poster_path}`}
                      alt={movie.title}
                      className="w-10 h-14 rounded object-cover"
                    />
                    <div className={`absolute -bottom-1 -right-1 text-[10px] rounded-full w-4 h-4 flex items-center justify-center ${decision === "liked" ? "bg-emerald-500" : "bg-red-400"}`}>
                      {decision === "liked" ? "👍" : "👎"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Card stack */
            <div className="relative flex flex-col items-center" style={{ height: 380 }}>

              {/* Background (next) card */}
              {nextMovie && (
                <div
                  className="absolute top-3 left-4 right-4 rounded-2xl overflow-hidden shadow-md"
                  style={{ height: 340, transform: "scale(0.93)", opacity: 0.5, zIndex: 0 }}
                >
                  <img
                    src={`https://image.tmdb.org/t/p/w500${nextMovie.poster_path}`}
                    alt={nextMovie.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              {/* Foreground (current) card */}
              {currentMovie && (
                <div
                  className="absolute top-0 left-0 right-0 rounded-2xl overflow-hidden shadow-xl"
                  style={{
                    height: 340,
                    zIndex: 1,
                    transition: animating ? "transform 0.35s ease, opacity 0.35s ease" : "none",
                    transform: animating === "right"
                      ? "translateX(120%) rotate(15deg)"
                      : animating === "left"
                        ? "translateX(-120%) rotate(-15deg)"
                        : "translateX(0) rotate(0deg)",
                    opacity: animating ? 0 : 1,
                  }}
                >
                  <img
                    src={`https://image.tmdb.org/t/p/w500${currentMovie.poster_path}`}
                    alt={currentMovie.title}
                    className="w-full h-full object-cover"
                  />
                  {/* Gradient + info overlay */}
                  <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent p-4">
                    <h3 className="text-white font-bold text-base leading-tight line-clamp-1">
                      {currentMovie.title}
                    </h3>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-white/70 text-xs">
                        {currentMovie.release_date?.slice(0, 4)}
                      </span>
                      {currentMovie.vote_average > 0 && (
                        <span className="flex items-center gap-0.5 text-yellow-400 text-xs font-medium">
                          <Star className="h-3 w-3 fill-current" />
                          {currentMovie.vote_average.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Like / Dislike hint labels that appear while deciding */}
              <div className="absolute top-0 left-0 right-0 flex justify-between pointer-events-none px-2 pt-2" style={{ zIndex: 2 }}>
                <div className="bg-red-500/90 text-white text-xs font-bold px-2 py-1 rounded-lg opacity-0">
                  NOPE 👎
                </div>
                <div className="bg-emerald-500/90 text-white text-xs font-bold px-2 py-1 rounded-lg opacity-0">
                  LIKE 👍
                </div>
              </div>

              {/* Action buttons */}
              <div className="absolute bottom-0 left-0 right-0 flex justify-center gap-6" style={{ zIndex: 2 }}>
                <button
                  onClick={() => handleDecision("disliked")}
                  disabled={isPending}
                  className="flex flex-col items-center gap-1 group"
                  data-testid="button-onboard-dislike"
                >
                  <div className="w-14 h-14 rounded-full bg-white dark:bg-card border-2 border-red-400 flex items-center justify-center shadow-lg transition-all duration-200 group-hover:scale-110 group-hover:bg-red-50 dark:group-hover:bg-red-950/40 group-active:scale-95 disabled:opacity-50">
                    <ThumbsDown className="h-6 w-6 text-red-400" />
                  </div>
                  <span className="text-[10px] font-medium text-muted-foreground">Nope</span>
                </button>

                <button
                  onClick={() => handleDecision("liked")}
                  disabled={isPending}
                  className="flex flex-col items-center gap-1 group"
                  data-testid="button-onboard-like"
                >
                  <div className="w-14 h-14 rounded-full bg-white dark:bg-card border-2 border-emerald-500 flex items-center justify-center shadow-lg transition-all duration-200 group-hover:scale-110 group-hover:bg-emerald-50 dark:group-hover:bg-emerald-950/40 group-active:scale-95 disabled:opacity-50">
                    <ThumbsUp className="h-6 w-6 text-emerald-500" />
                  </div>
                  <span className="text-[10px] font-medium text-muted-foreground">Love it</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 bg-card border-t flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground hover:text-foreground"
            onClick={handleSkip}
            data-testid="button-onboard-skip"
          >
            Skip
          </Button>

          {isComplete ? (
            <Button
              onClick={handleFinish}
              className="gap-1.5 bg-emerald-500 hover:bg-emerald-600 text-white"
              data-testid="button-onboard-finish"
            >
              <Sparkles className="h-4 w-4" />
              Build my feed!
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              {decided} / {REQUIRED} rated
              <ChevronRight className="h-3 w-3" />
            </span>
          )}
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
