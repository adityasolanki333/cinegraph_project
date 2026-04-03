import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "./useAuth";
import type { Movie } from "@shared/schema";
import { normalizeToMovie } from "@shared/schema";
import { queryClient, apiRequest, getAuthHeaders } from "@/lib/queryClient";

export function useWatchlist() {
  const { user } = useAuth();

  const { data: watchlist = [], isError: watchlistError, error: watchlistErrorDetails } = useQuery({
    queryKey: ['/api/users', user?.id, 'watchlist'],
    queryFn: async () => {
      if (!user?.id) return [];

      const response = await fetch(`/api/users/${user.id}/watchlist`, {
        headers: { ...getAuthHeaders() },
      });
      if (!response.ok) {
        throw new Error(`Failed to load watchlist: ${response.status}`);
      }

      const data = await response.json();
      const serverWatchlist = data.items || data || [];
      return Array.isArray(serverWatchlist) ? serverWatchlist.map((item: any) => normalizeToMovie(item)) : [];
    },
    enabled: !!user?.id,
    staleTime: 5 * 60 * 1000,
  });

  // Add to watchlist mutation
  const addMutation = useMutation({
    mutationFn: async (movie: Movie) => {
      if (!user) throw new Error("User not authenticated");

      return apiRequest('POST', `/api/users/${user.id}/watchlist/add`, {
        tmdbId: parseInt(movie.id),
        mediaType: movie.type || 'movie',
        title: movie.title,
        posterPath: movie.posterUrl || null
      });
    },
    onMutate: async (newMovie) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['/api/users', user?.id, 'watchlist'] });

      // Snapshot the previous value
      const previousWatchlist = queryClient.getQueryData(['/api/users', user?.id, 'watchlist']);

      // Optimistically update to the new value
      queryClient.setQueryData(['/api/users', user?.id, 'watchlist'], (old: Movie[] = []) => {
        const exists = old.some((item: Movie) => item.id === newMovie.id);
        return exists ? old : [...old, newMovie];
      });

      return { previousWatchlist };
    },
    onError: (_err, _newMovie, context) => {
      // Rollback on error
      if (context?.previousWatchlist) {
        queryClient.setQueryData(['/api/users', user?.id, 'watchlist'], context.previousWatchlist);
      }
    },
    onSettled: () => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'watchlist'] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [`/api/community/user-impact/${user.id}`] });
      }
    },
  });

  // Remove from watchlist mutation
  const removeMutation = useMutation({
    mutationFn: async (movieId: string) => {
      if (!user) throw new Error("User not authenticated");

      return apiRequest('DELETE', `/api/users/${user.id}/watchlist/${movieId}`);
    },
    onMutate: async (movieId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['/api/users', user?.id, 'watchlist'] });

      // Snapshot the previous value
      const previousWatchlist = queryClient.getQueryData(['/api/users', user?.id, 'watchlist']);

      // Optimistically update
      queryClient.setQueryData(['/api/users', user?.id, 'watchlist'], (old: Movie[] = []) => {
        return old.filter(item => item.id !== movieId);
      });

      return { previousWatchlist };
    },
    onError: (_err, _movieId, context) => {
      // Rollback on error
      if (context?.previousWatchlist) {
        queryClient.setQueryData(['/api/users', user?.id, 'watchlist'], context.previousWatchlist);
      }
    },
    onSettled: () => {
      // Refetch after mutation
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'watchlist'] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [`/api/community/user-impact/${user.id}`] });
      }
    },
  });

  const addToWatchlist = async (movie: Movie) => {
    if (!user) {
      console.warn("User not authenticated - cannot add to watchlist");
      return false;
    }

    const isAlreadyInList = watchlist.some((item: Movie) => item.id === movie.id);
    if (isAlreadyInList) {
      return false;
    }

    try {
      await addMutation.mutateAsync(movie);
      return true;
    } catch (error) {
      console.error("Error adding to watchlist:", error);
      return false;
    }
  };

  const removeFromWatchlist = async (movieId: string) => {
    if (!user) {
      console.warn("User not authenticated - cannot remove from watchlist");
      return false;
    }

    try {
      await removeMutation.mutateAsync(movieId);
      return true;
    } catch (error) {
      console.error("Error removing from watchlist:", error);
      return false;
    }
  };

  const isInWatchlist = (movieId: string) => {
    return watchlist.some((item: Movie) => item.id === movieId);
  };

  return {
    watchlist,
    addToWatchlist,
    removeFromWatchlist,
    isInWatchlist,
    watchlistError,
    watchlistErrorDetails,
  };
}
