import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MediaCard } from "@/components/media-card";
import { Heart, Plus, Loader2, LogIn, CheckCircle, Eye, Bookmark, Film, Tv, BarChart2, Sparkles } from "lucide-react";
import { useLocation } from "wouter";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import { tmdbService } from "@/lib/tmdb";
import { useAuth } from "@/hooks/useAuth";
import { useWatchlist } from "@/hooks/useWatchlist";
import { apiRequest } from "@/lib/queryClient";
import type { Movie } from "@shared/schema";

function EnrichedMovieCard({ item, isOwnList, onRemove }: { item: any; isOwnList: boolean; onRemove: () => void }) {
  const mediaType = item.mediaType === 'tv' ? 'tv' : item.type === 'tv' ? 'tv' : 'movie';
  const tmdbId = item.tmdbId || item.id;

  const { data: tmdbData, isLoading } = useQuery({
    queryKey: [`/api/tmdb/${mediaType}/${tmdbId}`],
    enabled: !!tmdbId,
  });

  if (isLoading) {
    return (
      <Card>
        <div className="aspect-[2/3] bg-muted animate-pulse" />
        <CardContent className="p-3 sm:p-4">
          <Skeleton className="h-4 w-3/4 mb-2" />
          <Skeleton className="h-3 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (!tmdbData) {
    const fallbackMovie: Movie = {
      id: tmdbId.toString(),
      title: item.title || 'Unknown',
      year: 0,
      genre: '',
      rating: 0,
      synopsis: '',
      posterUrl: item.posterUrl || (item.posterPath ? `https://image.tmdb.org/t/p/w500${item.posterPath}` : undefined),
      director: '',
      cast: [],
      duration: 0,
      type: mediaType,
      seasons: undefined,
    };

    return (
      <MediaCard
        movie={fallbackMovie}
        isInWatchlist={true}
        showRemoveButton={true}
        onRemoveFromWatchlist={onRemove}
      />
    );
  }

  const movie = tmdbService.convertToMovie(tmdbData as any, mediaType);

  return (
    <MediaCard
      movie={movie}
      isInWatchlist={true}
      showRemoveButton={true}
      onRemoveFromWatchlist={onRemove}
    />
  );
}

const LIST_TABS = [
  { id: "watchlist", label: "Watchlist", icon: Bookmark },
  { id: "watched",   label: "Watched",   icon: CheckCircle },
  { id: "favorite",  label: "Favorites", icon: Heart },
] as const;

export default function MyList() {
  const [listType, setListType] = useState<"watchlist" | "watched" | "favorite">("watchlist");
  const [filterType, setFilterType] = useState("all");
  const [sortBy, setSortBy] = useState("dateAdded");
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const { user, isLoading: authLoading, isAuthenticated } = useAuth();
  const { watchlist, removeFromWatchlist } = useWatchlist();

  const { data: favoritesData = [], isLoading: favoritesLoading } = useQuery({
    queryKey: ['/api/users', user?.id, 'favorites'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/favorites`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.items || data || [];
    },
    enabled: !!user?.id && listType === "favorite",
  });

  const { data: watchedData = [], isLoading: watchedLoading } = useQuery({
    queryKey: ['/api/users', user?.id, 'watched'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/watched`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.items || data || [];
    },
    enabled: !!user?.id && listType === "watched",
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      setLocation("/login");
    }
  }, [authLoading, isAuthenticated, setLocation]);

  const removeFromWatchlistMutation = useMutation({
    mutationFn: async (movieId: string) => removeFromWatchlist(movieId),
  });

  const removeFromFavoritesMutation = useMutation({
    mutationFn: async (tmdbId: string) => {
      await apiRequest('DELETE', `/api/users/${user?.id}/favorites/${tmdbId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'favorites'] });
    },
  });

  const removeFromWatchedMutation = useMutation({
    mutationFn: async (tmdbId: string) => {
      await apiRequest('DELETE', `/api/users/${user?.id}/watched/${tmdbId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'watched'] });
    },
  });

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Checking authentication...</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <Card className="text-center py-12 w-full max-w-md">
          <CardContent className="pt-6">
            <LogIn className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Please Log In</h3>
            <p className="text-muted-foreground mb-6">
              You need to be logged in to view your list.
            </p>
            <Button onClick={() => setLocation("/login")}>
              <LogIn className="h-4 w-4 mr-2" />
              Sign In
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isLoading = favoritesLoading || watchedLoading;

  const getCurrentListItems = () => {
    if (listType === "favorite") {
      return (Array.isArray(favoritesData) ? favoritesData : []).map((fav: any, index: number) => ({
        tmdbId: fav.tmdbId,
        id: fav.tmdbId?.toString() || '',
        title: fav.title || 'Unknown',
        mediaType: fav.mediaType,
        type: fav.mediaType,
        posterPath: fav.posterPath,
        posterUrl: fav.posterPath ? `https://image.tmdb.org/t/p/w500${fav.posterPath}` : '',
        rating: fav.voteAverage || fav.rating || 0,
        year: fav.releaseDate ? new Date(fav.releaseDate).getFullYear() : (fav.year || 0),
        dateAdded: fav.createdAt || fav.addedAt || new Date(Date.now() - index * 1000).toISOString(),
      }));
    }
    if (listType === "watched") {
      return (Array.isArray(watchedData) ? watchedData : []).map((item: any, index: number) => ({
        tmdbId: item.tmdbId,
        id: item.tmdbId?.toString() || '',
        title: item.title || 'Unknown',
        mediaType: item.mediaType || 'movie',
        type: item.mediaType || 'movie',
        posterPath: item.posterPath,
        posterUrl: item.posterPath ? `https://image.tmdb.org/t/p/w500${item.posterPath}` : '',
        rating: item.voteAverage || item.rating || 0,
        year: item.releaseDate ? new Date(item.releaseDate).getFullYear() : (item.year || 0),
        dateAdded: item.watchedAt || item.createdAt || new Date(Date.now() - index * 1000).toISOString(),
      }));
    }
    return watchlist;
  };

  const allListItems = getCurrentListItems();

  const handleRemoveFromList = (movieId: string) => {
    if (listType === "favorite") removeFromFavoritesMutation.mutate(movieId);
    else if (listType === "watched") removeFromWatchedMutation.mutate(movieId);
    else removeFromWatchlistMutation.mutate(movieId);
  };

  const filteredList = allListItems.filter((item: any) => {
    if (filterType === "movies") return item.type === "movie";
    if (filterType === "tv") return item.type === "tv";
    return true;
  });

  const sortedList = [...filteredList].sort((a: any, b: any) => {
    switch (sortBy) {
      case "title":   return (a.title || '').localeCompare(b.title || '');
      case "rating":  return (b.rating || 0) - (a.rating || 0);
      case "year":    return (b.year || 0) - (a.year || 0);
      case "dateAdded":
        return new Date(b.dateAdded || 0).getTime() - new Date(a.dateAdded || 0).getTime();
      default: return 0;
    }
  });

  const movieCount = allListItems.filter((item: any) => item.type === "movie").length;
  const tvCount    = allListItems.filter((item: any) => item.type === "tv").length;

  const activeTab = LIST_TABS.find(t => t.id === listType)!;

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
        <div className="flex items-center gap-3">
          <activeTab.icon className="h-7 w-7 sm:h-8 sm:w-8 text-accent shrink-0" />
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">My List</h1>
        </div>

        {/* Filters — wrap on mobile */}
        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="flex-1 sm:flex-none sm:w-32 min-w-[110px]" data-testid="select-filter-type">
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Items</SelectItem>
              <SelectItem value="movies">Movies</SelectItem>
              <SelectItem value="tv">TV Shows</SelectItem>
            </SelectContent>
          </Select>

          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="flex-1 sm:flex-none sm:w-36 min-w-[120px]" data-testid="select-sort-by">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="dateAdded">Date Added</SelectItem>
              <SelectItem value="title">Title</SelectItem>
              <SelectItem value="rating">Rating</SelectItem>
              <SelectItem value="year">Year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* List-type tabs */}
      <div className="flex gap-2 mb-6 border-b border-border pb-4">
        {LIST_TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setListType(id)}
            data-testid={`button-${id}`}
            className={`flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap
              ${listType === id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Stats — wraps on mobile */}
      <div className="flex flex-wrap gap-x-5 gap-y-1.5 mb-6 text-sm text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <BarChart2 className="h-3.5 w-3.5" />
          {allListItems.length} total
        </span>
        <span className="flex items-center gap-1.5">
          <Film className="h-3.5 w-3.5" />
          {movieCount} movies
        </span>
        <span className="flex items-center gap-1.5">
          <Tv className="h-3.5 w-3.5" />
          {tvCount} TV shows
        </span>
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin" />
          <span className="ml-2">Loading your list…</span>
        </div>
      ) : sortedList.length > 0 ? (
        /* Grid — 2 columns on mobile, scales up */
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3 sm:gap-4 lg:gap-5 mb-8">
          {sortedList.map((item: any) => (
            <EnrichedMovieCard
              key={item.id}
              item={item}
              isOwnList={true}
              onRemove={() => handleRemoveFromList(item.id)}
            />
          ))}
        </div>
      ) : (
        /* Empty state */
        <Card className="text-center py-12">
          <CardContent className="pt-6">
            <activeTab.icon className="h-14 w-14 sm:h-16 sm:w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg sm:text-xl font-semibold mb-2">
              Your {activeTab.label.toLowerCase()} is empty
            </h3>
            <p className="text-muted-foreground mb-6 text-sm sm:text-base max-w-sm mx-auto">
              {filterType === "movies"
                ? "No movies here yet. Start adding some!"
                : filterType === "tv"
                  ? "No TV shows here yet. Start adding some!"
                  : "Nothing here yet. Browse movies and shows to get started!"}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={() => setLocation("/movies")} data-testid="button-browse-movies">
                <Plus className="h-4 w-4 mr-2" />
                Browse Movies
              </Button>
              <Button variant="outline" onClick={() => setLocation("/tv-shows")} data-testid="button-browse-tv">
                <Plus className="h-4 w-4 mr-2" />
                Browse TV Shows
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No filter results */}
      {allListItems.length > 0 && sortedList.length === 0 && (
        <Card className="text-center py-10">
          <CardContent className="pt-6">
            <h3 className="text-lg sm:text-xl font-semibold mb-2">No items match your filter</h3>
            <p className="text-muted-foreground mb-6 text-sm sm:text-base">
              Try changing the filter to see more items.
            </p>
            <Button onClick={() => setFilterType("all")} data-testid="button-show-all">
              Show All Items
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Quick action banner */}
      {allListItems.length > 0 && (
        <Card className="p-4 sm:p-6 mt-6 sm:mt-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold mb-1">Ready to discover more?</h3>
              <p className="text-sm text-muted-foreground">
                Get personalised recommendations based on your list.
              </p>
            </div>
            <Button
              onClick={() => setLocation("/recommendations")}
              className="w-full sm:w-auto shrink-0"
              data-testid="button-get-recommendations"
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Get AI Recommendations
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
