import { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BarChart3, Users, Clock, Film, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";

interface WatchlistItem {
  id?: number;
  movieId?: number;
  title?: string;
  genre?: string;
  genres?: Array<{ id: number; name: string }>;
  addedAt?: string;
  watchedAt?: string;
  createdAt?: string;
}

interface RatingItem {
  id?: number;
  movieId?: number;
  rating: number;
  review?: string;
  createdAt?: string;
}

interface LeaderboardUser {
  userId?: number;
  username?: string;
  firstName?: string;
  reviewCount?: number;
  averageRating?: number;
}

interface CommunityLeaderboardData {
  topReviewers?: LeaderboardUser[];
}

type ApiListResponse<T> = T[] | { items: T[] } | { results: T[] } | { ratings: T[] } | { reviews: T[] };

const GENRE_COLORS: Record<string, string> = {
  Action: "#e11d48",
  Drama: "#7c3aed",
  Comedy: "#0891b2",
  Thriller: "#d97706",
  "Sci-Fi": "#059669",
  Horror: "#dc2626",
  Romance: "#db2777",
  Animation: "#7c3aed",
  Adventure: "#2563eb",
  Crime: "#6b7280",
  Fantasy: "#8b5cf6",
  Mystery: "#a855f7",
  Family: "#f97316",
  Documentary: "#0d9488",
  Music: "#ec4899",
  War: "#78716c",
  Western: "#ca8a04",
  History: "#b45309",
};

interface GenreDataItem {
  name: string;
  value: number;
  color: string;
}

function GenreChart({ data }: { data: GenreDataItem[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = 300;
    canvas.height = 200;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 70;
    const innerRadius = 40;
    const total = data.reduce((sum, g) => sum + g.value, 0);

    let currentAngle = -Math.PI / 2;

    data.forEach((genre) => {
      const sliceAngle = (genre.value / total) * 2 * Math.PI;

      ctx.beginPath();
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true);
      ctx.closePath();
      ctx.fillStyle = genre.color;
      ctx.fill();

      currentAngle += sliceAngle;
    });
  }, [data]);

  return <canvas ref={canvasRef} className="w-full h-full" aria-label="Genre distribution chart" role="img" />;
}

interface TimelineDataItem {
  month: string;
  count: number;
}

function TimelineChart({ data }: { data: TimelineDataItem[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = 400;
    canvas.height = 150;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const padding = 40;
    const chartWidth = canvas.width - 2 * padding;
    const chartHeight = canvas.height - 2 * padding;
    const maxValue = Math.max(...data.map(d => d.count), 1);

    ctx.strokeStyle = "#374151";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    ctx.strokeStyle = "#8B5CF6";
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((point, index) => {
      const x = padding + (index / Math.max(data.length - 1, 1)) * chartWidth;
      const y = canvas.height - padding - (point.count / maxValue) * chartHeight;

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    ctx.fillStyle = "#8B5CF6";
    data.forEach((point, index) => {
      const x = padding + (index / Math.max(data.length - 1, 1)) * chartWidth;
      const y = canvas.height - padding - (point.count / maxValue) * chartHeight;

      ctx.beginPath();
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });
  }, [data]);

  return <canvas ref={canvasRef} className="w-full h-full" aria-label="Viewing timeline chart" role="img" />;
}

function NetworkGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = 400;
    canvas.height = 300;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    const connections = [
      { from: [centerX, centerY], to: [centerX - 80, centerY - 60] },
      { from: [centerX, centerY], to: [centerX + 80, centerY - 60] },
      { from: [centerX, centerY], to: [centerX + 80, centerY + 60] },
      { from: [centerX, centerY], to: [centerX - 80, centerY + 60] },
    ];

    ctx.strokeStyle = "#8B5CF6";
    ctx.lineWidth = 2;
    ctx.globalAlpha = 0.6;

    connections.forEach(conn => {
      ctx.beginPath();
      ctx.moveTo(conn.from[0], conn.from[1]);
      ctx.lineTo(conn.to[0], conn.to[1]);
      ctx.stroke();
    });

    ctx.globalAlpha = 1;

    const nodes = [
      { x: centerX, y: centerY, color: "#1E40AF", size: 20 },
      { x: centerX - 80, y: centerY - 60, color: "#8B5CF6", size: 12 },
      { x: centerX + 80, y: centerY - 60, color: "#F59E0B", size: 12 },
      { x: centerX + 80, y: centerY + 60, color: "#10B981", size: 12 },
      { x: centerX - 80, y: centerY + 60, color: "#EC4899", size: 12 },
    ];

    nodes.forEach(node => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.size, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();
    });
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full" aria-label="Recommendation connection graph" role="img" />;
}

function ErrorRetry({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="py-8 flex flex-col items-center justify-center text-center">
      <AlertCircle className="h-10 w-10 text-destructive mb-3" aria-hidden="true" />
      <p className="text-sm text-muted-foreground mb-3">{message}</p>
      <Button variant="outline" size="sm" onClick={onRetry} data-testid="button-retry">
        <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
        Try Again
      </Button>
    </div>
  );
}

function StatCardSkeleton() {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-12" />
          </div>
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </CardContent>
    </Card>
  );
}

interface GraphVisualizationsProps {
  className?: string;
}

export default function GraphVisualizations({ className }: GraphVisualizationsProps) {
  const { user } = useAuth();

  const { data: watchlistData, isError: watchlistError, refetch: refetchWatchlist } = useQuery<ApiListResponse<WatchlistItem>>({
    queryKey: ['/api/watchlist'],
    enabled: !!user,
  });

  const { data: favoritesData, isLoading: favoritesLoading, isError: favoritesError, refetch: refetchFavorites } = useQuery<WatchlistItem[]>({
    queryKey: ['/api/users', user?.id, 'favorites'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/favorites`);
      if (!response.ok) throw new Error('Failed to fetch favorites');
      const data: ApiListResponse<WatchlistItem> = await response.json();
      return normalizeArray<WatchlistItem>(data);
    },
    enabled: !!user?.id,
  });

  const { data: watchedData, isLoading: watchedLoading, isError: watchedError, refetch: refetchWatched } = useQuery<WatchlistItem[]>({
    queryKey: ['/api/users', user?.id, 'watched'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/watched`);
      if (!response.ok) throw new Error('Failed to fetch watched');
      const data: ApiListResponse<WatchlistItem> = await response.json();
      return normalizeArray<WatchlistItem>(data);
    },
    enabled: !!user?.id,
  });

  const { data: ratingsData, isLoading: ratingsLoading, isError: ratingsError, refetch: refetchRatings } = useQuery<RatingItem[]>({
    queryKey: ['/api/users', user?.id, 'reviews'],
    queryFn: async () => {
      const response = await fetch(`/api/users/${user?.id}/reviews`);
      if (!response.ok) throw new Error('Failed to fetch reviews');
      const data = await response.json();
      const parsed = data as Record<string, unknown>;
      if (Array.isArray(parsed.ratings)) return parsed.ratings as RatingItem[];
      if (Array.isArray(parsed.reviews)) return parsed.reviews as RatingItem[];
      if (Array.isArray(data)) return data as RatingItem[];
      return [];
    },
    enabled: !!user?.id,
  });

  const { data: communityData, isLoading: communityLoading, isError: communityError, refetch: refetchCommunity } = useQuery<CommunityLeaderboardData>({
    queryKey: ['/api/community/leaderboards'],
  });

  const isLoading = favoritesLoading || watchedLoading || ratingsLoading;
  const hasDataError = watchlistError || favoritesError || watchedError || ratingsError;

  function normalizeArray<T>(data: unknown): T[] {
    if (Array.isArray(data)) return data as T[];
    if (data && typeof data === 'object') {
      const obj = data as Record<string, unknown>;
      if (Array.isArray(obj.items)) return obj.items as T[];
      if (Array.isArray(obj.results)) return obj.results as T[];
    }
    return [];
  }

  const watchlist = normalizeArray<WatchlistItem>(watchlistData);
  const favorites = favoritesData ?? [];
  const watched = watchedData ?? [];
  const ratings = ratingsData ?? [];

  const moviesWatched = watched.length;
  const totalItems = watchlist.length + favorites.length + watched.length;

  const avgRating = ratings.length > 0
    ? (ratings.reduce((sum, r) => sum + (r.rating || 0), 0) / ratings.length).toFixed(1)
    : "0.0";

  const genreData: GenreDataItem[] = (() => {
    const genreCounts: Record<string, number> = {};
    const allItems: WatchlistItem[] = [...watchlist, ...favorites, ...watched];
    allItems.forEach((item) => {
      const genre = item.genre || item.genres?.[0]?.name;
      if (genre) {
        genreCounts[genre] = (genreCounts[genre] || 0) + 1;
      }
    });

    return Object.entries(genreCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([name, value]) => ({
        name,
        value,
        color: GENRE_COLORS[name] || "#6b7280",
      }));
  })();

  const totalGenreCount = genreData.reduce((sum, g) => sum + g.value, 0);

  const timelineData: TimelineDataItem[] = (() => {
    const monthCounts: Record<string, number> = {};
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

    const timelineItems: Array<WatchlistItem | RatingItem> = [...watched, ...ratings];
    timelineItems.forEach((item) => {
      const dateStr = ('watchedAt' in item ? item.watchedAt : undefined) ||
                      item.createdAt ||
                      ('addedAt' in item ? item.addedAt : undefined);
      if (dateStr) {
        const date = new Date(dateStr);
        const monthIdx = date.getMonth();
        const key = months[monthIdx];
        monthCounts[key] = (monthCounts[key] || 0) + 1;
      }
    });

    return months
      .filter(m => monthCounts[m])
      .map(month => ({ month, count: monthCounts[month] || 0 }));
  })();

  const leaderboardUsers: LeaderboardUser[] = communityData?.topReviewers?.slice(0, 3) ?? [];

  const retryAll = () => {
    refetchWatchlist();
    refetchFavorites();
    refetchWatched();
    refetchRatings();
  };

  return (
    <div className={className}>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        {hasDataError && !isLoading ? (
          <Card className="col-span-full" data-testid="card-stats-error">
            <CardContent className="pt-6">
              <ErrorRetry message="Failed to load your stats. Check your connection and try again." onRetry={retryAll} />
            </CardContent>
          </Card>
        ) : isLoading ? (
          Array.from({ length: 4 }, (_, i) => <StatCardSkeleton key={i} />)
        ) : (
          <>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Movies Watched</p>
                    <p className="text-2xl font-bold text-primary" data-testid="text-movies-watched">{moviesWatched}</p>
                  </div>
                  <Film className="h-8 w-8 text-primary" aria-hidden="true" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Items</p>
                    <p className="text-2xl font-bold text-accent" data-testid="text-total-items">{totalItems}</p>
                  </div>
                  <Clock className="h-8 w-8 text-accent" aria-hidden="true" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Avg Rating</p>
                    <p className="text-2xl font-bold text-rating" data-testid="text-avg-rating">{avgRating}</p>
                  </div>
                  <BarChart3 className="h-8 w-8 text-rating" aria-hidden="true" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Reviews</p>
                    <p className="text-2xl font-bold text-green-400" data-testid="text-reviews-count">{ratings.length}</p>
                  </div>
                  <Users className="h-8 w-8 text-green-400" aria-hidden="true" />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-accent" aria-hidden="true" />
            <span>Genre Preference Network</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="h-48 flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : genreData.length === 0 ? (
            <div className="h-48 flex flex-col items-center justify-center text-center">
              <BarChart3 className="h-10 w-10 text-muted-foreground mb-3" aria-hidden="true" />
              <p className="text-sm text-muted-foreground">No genre data yet</p>
              <p className="text-xs text-muted-foreground mt-1">Add movies to your watchlist or favorites to see your genre preferences</p>
            </div>
          ) : (
            <>
              <div className="h-48 bg-muted/30 rounded-lg flex items-center justify-center mb-4">
                <GenreChart data={genreData} />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                {genreData.map((genre) => (
                  <div key={genre.name} className="flex items-center space-x-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: genre.color }}
                      aria-hidden="true"
                    />
                    <span>{genre.name} ({totalGenreCount > 0 ? Math.round((genre.value / totalGenreCount) * 100) : 0}%)</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Users className="h-5 w-5 text-accent" aria-hidden="true" />
              <span>Top Community Reviewers</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {communityError ? (
              <div data-testid="card-community-error">
                <ErrorRetry message="Failed to load community data." onRetry={() => refetchCommunity()} />
              </div>
            ) : communityLoading ? (
              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <div key={i} className="bg-muted/30 rounded-lg p-4">
                    <Skeleton className="h-5 w-32 mb-2" />
                    <Skeleton className="h-4 w-24" />
                  </div>
                ))}
              </div>
            ) : leaderboardUsers.length === 0 ? (
              <div className="py-8 text-center">
                <Users className="h-10 w-10 text-muted-foreground mx-auto mb-3" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">No community data yet</p>
                <p className="text-xs text-muted-foreground mt-1">Write reviews and engage with others to see community stats</p>
              </div>
            ) : (
              <div className="space-y-4">
                {leaderboardUsers.map((member, index) => (
                  <div key={member.userId || index} className="bg-muted/30 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold">{member.firstName || member.username || `Reviewer #${index + 1}`}</h4>
                      <Badge variant="secondary" className="bg-primary/20 text-primary">
                        {member.reviewCount || 0} reviews
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Avg rating: {member.averageRating?.toFixed(1) || "N/A"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-5 w-5 text-accent" aria-hidden="true" />
              <span>Viewing Pattern Timeline</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-36 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : timelineData.length === 0 ? (
              <div className="h-36 flex flex-col items-center justify-center text-center">
                <Clock className="h-10 w-10 text-muted-foreground mb-3" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">No viewing history yet</p>
                <p className="text-xs text-muted-foreground mt-1">Mark movies as watched to see your viewing patterns over time</p>
              </div>
            ) : (
              <>
                <div className="h-36 bg-muted/30 rounded-lg flex items-center justify-center mb-4">
                  <TimelineChart data={timelineData} />
                </div>
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>Total tracked: {timelineData.reduce((s, d) => s + d.count, 0)} items</p>
                  <p>Most active: {timelineData.reduce((max, d) => d.count > max.count ? d : max, timelineData[0])?.month || "N/A"}</p>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <BarChart3 className="h-5 w-5 text-accent" aria-hidden="true" />
            <span>Recommendation Connection Graph</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-72 bg-muted/30 rounded-lg flex items-center justify-center mb-4">
            <NetworkGraph />
          </div>
          <p className="text-sm text-muted-foreground">
            Interactive graph showing how your preferences connect to movie recommendations through
            genre relationships and collaborative filtering algorithms.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
