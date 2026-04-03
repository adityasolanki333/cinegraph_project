import { useQuery } from "@tanstack/react-query";
import { Sparkles, Zap, TrendingUp, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { MediaCard } from "@/components/media-card";
import MediaCardSkeleton from "@/components/media-card-skeleton";

interface TmdbDetailItem {
  id: number;
  title?: string;
  name?: string;
  vote_average: number;
  poster_path: string;
}

interface SimilarContentProps {
  title: string;
  overview: string;
  mediaType: 'movie' | 'tv';
  currentTmdbId: number;
}

interface SemanticSearchResult {
  tmdbId: number;
  title?: string;
  name?: string;
  similarity: number;
  overview: string;
  posterPath?: string;
  mediaType: 'movie' | 'tv';
  matchQuality?: string;
  explanation?: string;
}

interface SemanticSearchResponse {
  query: string;
  results: SemanticSearchResult[];
  count: number;
  duration: string;
  method: string;
  searchMethod?: string;
  searchTime?: number;
}

function MatchIndicator({ similarity, matchQuality }: { similarity: number; matchQuality?: string }) {
  const pct = Math.round(similarity * 100);

  const getColor = () => {
    if (pct >= 80) return 'text-emerald-600 dark:text-emerald-400';
    if (pct >= 60) return 'text-blue-600 dark:text-blue-400';
    if (pct >= 40) return 'text-amber-600 dark:text-amber-400';
    return 'text-gray-500';
  };

  const getProgressColor = () => {
    if (pct >= 80) return '[&>div]:bg-emerald-500';
    if (pct >= 60) return '[&>div]:bg-blue-500';
    if (pct >= 40) return '[&>div]:bg-amber-500';
    return '';
  };

  const getIcon = () => {
    if (!matchQuality) return null;
    if (matchQuality.includes('Semantic')) return <Zap className="h-3 w-3" />;
    if (matchQuality.includes('Popular')) return <TrendingUp className="h-3 w-3" />;
    if (matchQuality.includes('Recent')) return <Clock className="h-3 w-3" />;
    return null;
  };

  return (
    <div className="px-1 space-y-1" data-testid="match-indicator">
      <div className="flex items-center justify-between text-xs">
        <span className={`font-medium flex items-center gap-1 ${getColor()}`}>
          {getIcon()}
          {pct}% match
        </span>
        {matchQuality && matchQuality !== 'Related' && (
          <span className="text-[10px] text-muted-foreground truncate max-w-[80px]">{matchQuality}</span>
        )}
      </div>
      <Progress value={pct} className={`h-1.5 ${getProgressColor()}`} />
    </div>
  );
}

export function SimilarContent({ title, overview, mediaType, currentTmdbId }: SimilarContentProps) {
  const { data: semanticResults, isLoading: semanticLoading } = useQuery({
    queryKey: ['/api/recommendations/semantic-search', title, overview],
    queryFn: async () => {
      const query = `${title} ${overview}`;
      const response = await fetch(`/api/recommendations/semantic-search?query=${encodeURIComponent(query)}&limit=12`);
      if (!response.ok) throw new Error('Failed to fetch semantic similar content');
      return response.json() as Promise<SemanticSearchResponse>;
    },
    enabled: !!title,
  });

  const filteredResults = semanticResults?.results?.filter((r) => r.tmdbId !== currentTmdbId) || [];

  const similarItemIds = filteredResults.map((r) => r.tmdbId);

  const { data: itemDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['/api/tmdb/details', mediaType, similarItemIds],
    queryFn: async () => {
      const promises = similarItemIds.map(async (id: number) => {
        try {
          const response = await fetch(`/api/tmdb/${mediaType}/${id}`);
          if (!response.ok) return null;
          return response.json();
        } catch {
          return null;
        }
      });
      const results = await Promise.all(promises);
      return results.filter(Boolean);
    },
    enabled: similarItemIds.length > 0,
  });

  if (semanticLoading || detailsLoading) {
    return (
      <div className="space-y-4" data-testid="similar-content-section">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-accent" />
              AI-Recommended Similar {mediaType === 'movie' ? 'Movies' : 'Shows'}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Finding content with similar themes and storylines...
            </p>
          </div>
        </div>
        <ScrollArea className="w-full">
          <div className="flex gap-4 pb-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="w-[150px] sm:w-[180px] md:w-[200px] flex-shrink-0">
                <MediaCardSkeleton />
              </div>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      </div>
    );
  }

  if (!itemDetails || itemDetails.length === 0) {
    return (
      <div className="space-y-4" data-testid="similar-content-section">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-accent" />
              AI-Recommended Similar {mediaType === 'movie' ? 'Movies' : 'Shows'}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Content with similar themes and storylines
            </p>
          </div>
        </div>
        <div className="text-center py-12 bg-muted/30 rounded-lg" data-testid="empty-similar-content">
          <Sparkles className="h-16 w-16 text-muted-foreground mx-auto mb-4 opacity-50" />
          <h3 className="text-xl font-semibold mb-2">No Semantic Matches Found</h3>
          <p className="text-muted-foreground">
            Try browsing other {mediaType === 'movie' ? 'movies' : 'shows'} or check back later
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="similar-content-section">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            AI-Recommended Similar {mediaType === 'movie' ? 'Movies' : 'Shows'}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Content with similar themes and storylines
          </p>
        </div>
        <div className="flex items-center gap-2">
          {semanticResults?.searchTime && (
            <Badge variant="outline" className="text-xs" data-testid="badge-search-time">
              {semanticResults.searchTime}s
            </Badge>
          )}
          {semanticResults?.searchMethod && (
            <Badge variant="secondary" className="text-[10px]" data-testid="badge-search-method">
              {semanticResults.searchMethod === 'pinecone_semantic' ? 'Vector' : 'TF-IDF'}
            </Badge>
          )}
        </div>
      </div>

      <ScrollArea className="w-full">
        <div className="flex gap-4 pb-4">
          {itemDetails.map((item: TmdbDetailItem) => {
            const semanticResult = filteredResults.find((r) => r.tmdbId === item.id);
            const similarity = semanticResult?.similarity || 0;
            const matchQuality = semanticResult?.matchQuality;

            return (
              <div
                key={item.id}
                className="w-[150px] sm:w-[180px] md:w-[200px] flex-shrink-0 space-y-2"
                data-testid={`similar-content-item-${item.id}`}
              >
                <MediaCard
                  item={{
                    id: item.id,
                    title: item.title,
                    name: item.name,
                    vote_average: item.vote_average,
                    poster_path: item.poster_path,
                    type: mediaType
                  }}
                  mediaType={mediaType}
                />
                {semanticResult && (
                  <MatchIndicator similarity={similarity} matchQuality={matchQuality} />
                )}
              </div>
            );
          })}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      <div className="text-center text-sm text-muted-foreground" data-testid="text-similar-count">
        Showing {itemDetails.length} AI-recommended similar {mediaType === 'movie' ? 'movies' : 'shows'}
      </div>
    </div>
  );
}
