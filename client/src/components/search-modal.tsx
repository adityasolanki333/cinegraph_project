import { useState, useEffect, useMemo } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { tmdbService } from "@/lib/tmdb";
import { Search, X, Film, Tv, User, Building, Sparkles, Loader2, Star } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { logSearchInteraction } from "@/lib/feedback";
import { useTranslation } from "react-i18next";
import { getAuthHeaders } from "@/lib/queryClient";

interface SearchModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Detect if a query is descriptive/semantic rather than a keyword title lookup */
function detectSemanticQuery(q: string): boolean {
  const trimmed = q.trim();
  if (trimmed.length < 4) return false;
  const words = trimmed.split(/\s+/);
  if (words.length >= 4) return true;
  return [
    /\babout\b/i, /\bwith\b/i, /\bwhere\b/i, /\bfeel(s|ing)?\b/i,
    /\blike\b/i, /\bplot\b/i, /\bstory\b/i, /\btheme\b/i,
    /^(a|the)\s+(movie|film|show|series|doc)/i,
    /\b(scary|funny|sad|dark|uplifting|romantic|intense|suspenseful|heartwarming)\b/i,
    /\b(redemption|friendship|survival|betrayal|revenge|journey|quest)\b/i,
    /\b(psychological|existential|philosophical|dystopian|futuristic)\b/i,
    /\b(based on|set in|inspired by|similar to|reminds me)\b/i,
  ].some(p => p.test(trimmed));
}

export default function SearchModal({ open, onOpenChange }: SearchModalProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [activeTab, setActiveTab] = useState<'all' | 'movies' | 'tv' | 'people' | 'companies' | 'collections'>('all');
  const [semanticDebounced, setSemanticDebounced] = useState("");
  const [, setLocation] = useLocation();

  const isSemantic = useMemo(() => detectSemanticQuery(query), [query]);

  // Debounce semantic query (900 ms — AI needs a moment)
  useEffect(() => {
    if (!isSemantic || query.trim().length < 4) {
      setSemanticDebounced("");
      return;
    }
    const id = setTimeout(() => setSemanticDebounced(query.trim()), 900);
    return () => clearTimeout(id);
  }, [query, isSemantic]);

  // ── Regular TMDB keyword searches ──────────────────────────────────────────
  const { data: searchResults, isLoading } = useQuery({
    queryKey: ['/api/tmdb/search/multi', query],
    queryFn: async () => {
      if (!query.trim()) return { results: [] };
      return tmdbService.searchMulti(query);
    },
    enabled: query.length >= 2,
  });

  const { data: movieResults } = useQuery({
    queryKey: ['/api/tmdb/search/movies', query],
    queryFn: () => tmdbService.searchMovies(query),
    enabled: query.length >= 2 && activeTab === 'movies',
  });

  const { data: tvResults } = useQuery({
    queryKey: ['/api/tmdb/search/tv', query],
    queryFn: () => tmdbService.searchTVShows(query),
    enabled: query.length >= 2 && activeTab === 'tv',
  });

  const { data: personResults } = useQuery({
    queryKey: ['/api/tmdb/search/people', query],
    queryFn: () => tmdbService.searchPeople(query),
    enabled: query.length >= 2 && activeTab === 'people',
  });

  const { data: companyResults } = useQuery({
    queryKey: ['/api/tmdb/search/companies', query],
    queryFn: () => tmdbService.searchCompanies(query),
    enabled: query.length >= 2 && activeTab === 'companies',
  });

  const { data: collectionResults } = useQuery({
    queryKey: ['/api/tmdb/search/collections', query],
    queryFn: () => tmdbService.searchCollections(query),
    enabled: query.length >= 2 && activeTab === 'collections',
  });

  // ── Semantic AI search ─────────────────────────────────────────────────────
  const { data: semanticData, isFetching: semanticLoading } = useQuery({
    queryKey: ['/api/recommendations/semantic-search-modal', semanticDebounced],
    queryFn: async () => {
      if (!semanticDebounced) return null;
      const res = await fetch('/api/recommendations/semantic-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ query: semanticDebounced, limit: 8, filters: {} }),
      });
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!semanticDebounced,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  // ── Helpers ────────────────────────────────────────────────────────────────
  const sortByRelevance = (results: any[], searchQuery: string) => {
    if (!results || results.length === 0) return [];
    const q = searchQuery.toLowerCase().trim();
    return [...results].sort((a, b) => {
      const tA = (a.title || a.name || '').toLowerCase();
      const tB = (b.title || b.name || '').toLowerCase();
      if (tA === q && tB !== q) return -1;
      if (tB === q && tA !== q) return 1;
      if (tA.startsWith(q) && !tB.startsWith(q)) return -1;
      if (tB.startsWith(q) && !tA.startsWith(q)) return 1;
      return (b.popularity || 0) - (a.popularity || 0);
    });
  };

  const getResults = () => {
    if (query.length < 2) return [];
    let results: any[] = [];
    switch (activeTab) {
      case 'movies': results = movieResults?.results || []; break;
      case 'tv': results = tvResults?.results || []; break;
      case 'people': results = personResults?.results || []; break;
      case 'companies': results = companyResults?.results || []; break;
      case 'collections': results = collectionResults?.results || []; break;
      default: results = searchResults?.results || [];
    }
    return sortByRelevance(results, query);
  };

  const handleResultClick = (result: any) => {
    onOpenChange(false);
    if (query.length >= 2) logSearchInteraction(query, result.id, result.media_type || 'movie');
    setQuery("");
    if (result.media_type === 'movie' || result.title) {
      setLocation(`/movie/${result.id}`);
    } else if (result.media_type === 'tv' || result.name) {
      setLocation(`/tv/${result.id}`);
    } else if (result.media_type === 'person' || result.known_for_department) {
      setLocation(`/person/${result.id}`);
    } else if (result.backdrop_path !== undefined || activeTab === 'collections') {
      setLocation(`/collection/${result.id}`);
    }
  };

  const handleSemanticClick = (result: any) => {
    onOpenChange(false);
    setQuery("");
    const id = result.tmdbId;
    const type = result.mediaType === 'tv' ? 'tv' : 'movie';
    setLocation(`/${type}/${id}`);
  };

  const getResultIcon = (result: any) => {
    if (result.media_type === 'movie' || result.title) return Film;
    if (result.media_type === 'tv' || result.first_air_date) return Tv;
    if (result.media_type === 'person' || result.known_for_department) return User;
    if (result.logo_path) return Building;
    return Film;
  };

  const getImageUrl = (result: any) => {
    if (result.poster_path) return tmdbService.getImageUrl(result.poster_path, 'poster');
    if (result.profile_path) return tmdbService.getImageUrl(result.profile_path, 'poster');
    if (result.logo_path) return tmdbService.getImageUrl(result.logo_path, 'poster');
    return null;
  };

  const tabs = [
    { id: 'all', label: t('search.tabAll'), count: searchResults?.results?.length || 0 },
    { id: 'movies', label: t('search.tabMovies'), count: movieResults?.results?.length || 0 },
    { id: 'tv', label: t('search.tabTV'), count: tvResults?.results?.length || 0 },
    { id: 'collections', label: t('search.tabFranchises'), count: collectionResults?.results?.length || 0 },
    { id: 'people', label: t('search.tabPeople'), count: personResults?.results?.length || 0 },
    { id: 'companies', label: t('search.tabCompanies'), count: companyResults?.results?.length || 0 },
  ];

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActiveTab('all');
      setSemanticDebounced("");
    }
  }, [open]);

  const semanticResults = semanticData?.results || [];
  const searchIntent = semanticData?.searchIntent || "";
  const isSemanticPending = isSemantic && query.trim().length >= 4 && (semanticDebounced !== query.trim() || semanticLoading);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] p-0 flex flex-col">
        <DialogHeader className="p-6 pb-4 shrink-0">
          <DialogTitle className="flex items-center space-x-2">
            <Search className="h-5 w-5" />
            <span>{t('search.title')}</span>
          </DialogTitle>
        </DialogHeader>

        {/* Search input */}
        <div className="px-6 shrink-0">
          <div className="relative">
            {isSemantic ? (
              <Sparkles className="absolute left-3 top-3 h-4 w-4 text-violet-400" />
            ) : (
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            )}
            <Input
              id="search-modal-input"
              name="search"
              placeholder={t('search.placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className={`pl-10 pr-10 transition-colors ${isSemantic ? 'border-violet-500/50 focus-visible:ring-violet-500/30' : ''}`}
              autoComplete="off"
              autoFocus
            />
            {query && (
              <Button variant="ghost" size="sm" className="absolute right-2 top-2 h-6 w-6 p-0" onClick={() => setQuery("")}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* AI mode indicator */}
          {isSemantic && query.trim().length >= 4 && (
            <div className="flex items-center gap-2 mt-2 px-1">
              <div className="flex items-center gap-1.5">
                {isSemanticPending ? (
                  <Loader2 className="h-3 w-3 animate-spin text-violet-400" />
                ) : (
                  <Sparkles className="h-3 w-3 text-violet-400" />
                )}
                <span className="text-xs text-violet-400 font-medium">
                  {isSemanticPending
                    ? "AI is analyzing your description…"
                    : searchIntent
                      ? `AI understood: "${searchIntent}"`
                      : "Smart search active"}
                </span>
              </div>
            </div>
          )}
        </div>

        {query.length >= 2 && (
          <>
            {/* Tabs */}
            <div className="flex space-x-1 px-6 pt-3 border-b shrink-0">
              {tabs.map((tab) => (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? "default" : "ghost"}
                  size="sm"
                  className="rounded-b-none"
                  onClick={() => setActiveTab(tab.id as any)}
                  disabled={tab.count === 0 && query.length >= 2}
                >
                  {tab.label}
                  {tab.count > 0 && (
                    <Badge variant="secondary" className="ml-2">{tab.count}</Badge>
                  )}
                </Button>
              ))}
            </div>

            {/* Results */}
            <ScrollArea className="flex-1 px-6 pb-6 min-h-0">
              <div className="space-y-1 pt-2">

                {/* ── AI Semantic Results ────────────────────────────────── */}
                {isSemantic && activeTab === 'all' && (
                  <div className="mb-4">
                    <div className="flex items-center gap-2 py-2">
                      <Sparkles className="h-3.5 w-3.5 text-violet-400 shrink-0" />
                      <span className="text-xs font-semibold text-violet-400 uppercase tracking-wide">
                        AI Smart Matches
                      </span>
                      {isSemanticPending && (
                        <Loader2 className="h-3 w-3 animate-spin text-violet-400 ml-auto" />
                      )}
                    </div>

                    {/* Skeletons while waiting */}
                    {isSemanticPending && semanticResults.length === 0 && (
                      <div className="space-y-2">
                        {[1, 2, 3].map(i => (
                          <div key={i} className="flex items-center gap-3 p-3 rounded-lg border border-violet-500/10 bg-violet-500/5">
                            <Skeleton className="w-12 h-16 rounded shrink-0" />
                            <div className="flex-1 space-y-2">
                              <Skeleton className="h-4 w-1/2" />
                              <Skeleton className="h-3 w-full" />
                              <Skeleton className="h-3 w-3/4" />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Semantic results */}
                    {semanticResults.length > 0 && (
                      <div className="space-y-1.5">
                        {semanticResults.map((result: any, idx: number) => {
                          const posterUrl = result.posterPath
                            ? `https://image.tmdb.org/t/p/w92${result.posterPath}`
                            : null;
                          const year = result.releaseDate
                            ? new Date(result.releaseDate).getFullYear()
                            : null;
                          const matchPct = Math.round((result.similarity || 0) * 100);
                          const matchColor =
                            matchPct >= 80 ? "text-green-400" :
                            matchPct >= 60 ? "text-yellow-400" :
                            "text-muted-foreground";

                          return (
                            <div
                              key={`sem-${result.tmdbId}-${idx}`}
                              className="flex items-start gap-3 p-3 rounded-lg border border-violet-500/20 bg-violet-500/5 hover:bg-violet-500/10 cursor-pointer transition-colors group"
                              onClick={() => handleSemanticClick(result)}
                            >
                              {posterUrl ? (
                                <img
                                  src={posterUrl}
                                  alt={result.title}
                                  className="w-10 h-14 object-cover rounded shrink-0"
                                  onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                />
                              ) : (
                                <div className="w-10 h-14 bg-muted rounded flex items-center justify-center shrink-0">
                                  <Film className="h-4 w-4 text-muted-foreground" />
                                </div>
                              )}

                              <div className="flex-1 min-w-0">
                                <div className="flex items-start justify-between gap-2">
                                  <div className="min-w-0">
                                    <span className="font-medium text-sm group-hover:text-violet-300 transition-colors truncate block">
                                      {result.title}
                                    </span>
                                    {year && (
                                      <span className="text-xs text-muted-foreground">{year}</span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-1.5 shrink-0">
                                    {matchPct > 0 && (
                                      <span className={`text-xs font-semibold tabular-nums ${matchColor}`}>
                                        {matchPct}%
                                      </span>
                                    )}
                                    {result.voteAverage > 0 && (
                                      <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
                                        <Star className="h-2.5 w-2.5 fill-yellow-400 text-yellow-400" />
                                        {result.voteAverage.toFixed(1)}
                                      </span>
                                    )}
                                  </div>
                                </div>

                                {result.overview && (
                                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1 leading-relaxed">
                                    {result.overview}
                                  </p>
                                )}

                                <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                                  <Badge
                                    variant="outline"
                                    className="text-[10px] h-4 px-1.5 border-violet-500/40 text-violet-400 bg-transparent"
                                  >
                                    <Sparkles className="h-2 w-2 mr-0.5" />
                                    AI Match
                                  </Badge>
                                  {result.mediaType === 'tv' && (
                                    <Badge variant="outline" className="text-[10px] h-4 px-1.5">TV</Badge>
                                  )}
                                  {Array.isArray(result.genres) && result.genres[0] && (
                                    <span className="text-[10px] text-muted-foreground">{result.genres[0]}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Divider before regular results */}
                    {(semanticResults.length > 0 || isSemanticPending) && (
                      <div className="flex items-center gap-2 mt-4 mb-2">
                        <div className="h-px flex-1 bg-border" />
                        <span className="text-[11px] text-muted-foreground whitespace-nowrap">Also in database</span>
                        <div className="h-px flex-1 bg-border" />
                      </div>
                    )}
                  </div>
                )}

                {/* ── Regular TMDB Results ──────────────────────────────── */}
                {isLoading ? (
                  <div className="flex items-center justify-center py-8 text-muted-foreground">
                    <div className="flex items-center space-x-2">
                      <Search className="h-4 w-4 animate-pulse" />
                      <span>{t('search.searching')}</span>
                    </div>
                  </div>
                ) : getResults().length > 0 ? (
                  getResults().map((result: any, index: number) => {
                    const Icon = getResultIcon(result);
                    const imageUrl = getImageUrl(result);
                    const title = result.title || result.name;
                    const year = result.release_date
                      ? new Date(result.release_date).getFullYear()
                      : result.first_air_date
                        ? new Date(result.first_air_date).getFullYear()
                        : null;

                    return (
                      <div
                        key={`${result.id}-${index}`}
                        className="flex items-center space-x-3 p-3 rounded-lg hover:bg-muted/50 cursor-pointer transition-colors"
                        onClick={() => handleResultClick(result)}
                      >
                        {imageUrl ? (
                          <img
                            src={imageUrl}
                            alt={title}
                            loading="lazy"
                            className="w-12 h-12 object-cover rounded"
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        ) : (
                          <div className="w-12 h-12 bg-muted rounded flex items-center justify-center shrink-0">
                            <Icon className="h-6 w-6 text-muted-foreground" />
                          </div>
                        )}

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2">
                            <h4 className="font-medium truncate">{title}</h4>
                            {year && (
                              <span className="text-sm text-muted-foreground shrink-0">({year})</span>
                            )}
                          </div>

                          {result.overview && (
                            <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                              {result.overview}
                            </p>
                          )}

                          {result.known_for_department && (
                            <p className="text-sm text-muted-foreground mt-1">
                              {result.known_for_department}
                            </p>
                          )}

                          <div className="flex items-center space-x-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {result.media_type === 'movie' || result.title ? t('search.typeMovie') :
                                result.media_type === 'tv' || result.first_air_date ? t('search.typeTV') :
                                  result.media_type === 'person' || result.known_for_department ? t('search.typePerson') :
                                    activeTab === 'collections' || (result.backdrop_path !== undefined && !result.overview) ? t('search.typeCollection') :
                                      t('search.typeCompany')}
                            </Badge>
                            {result.vote_average && result.vote_average > 0 && (
                              <Badge variant="secondary" className="text-xs">
                                ⭐ {result.vote_average.toFixed(1)}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  !isSemantic && (
                    <div className="text-center py-8 text-muted-foreground">
                      <div className="flex flex-col items-center space-y-2">
                        <Search className="h-8 w-8" />
                        <p>{t('search.noResults', { query })}</p>
                        <p className="text-sm">{t('search.noResultsHint')}</p>
                      </div>
                    </div>
                  )
                )}
              </div>
            </ScrollArea>
          </>
        )}

        {query.length < 2 && (
          <div className="px-6 pb-6">
            <div className="text-center py-8 text-muted-foreground">
              <Search className="h-8 w-8 mx-auto mb-4" />
              <p>{t('search.startTyping')}</p>
              <p className="text-sm mt-2">{t('search.startTypingHint')}</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {[
                  "a movie about redemption",
                  "feel-good comedy set in Paris",
                  "psychological thriller with twist",
                  "sci-fi about artificial intelligence",
                ].map(hint => (
                  <button
                    key={hint}
                    className="text-xs px-3 py-1.5 rounded-full border border-violet-500/30 text-violet-400 hover:bg-violet-500/10 transition-colors flex items-center gap-1"
                    onClick={() => setQuery(hint)}
                  >
                    <Sparkles className="h-2.5 w-2.5" />
                    {hint}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
