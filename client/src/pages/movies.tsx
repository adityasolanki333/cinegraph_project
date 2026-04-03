import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { MediaCard } from "@/components/media-card";
import MediaCardSkeleton from "@/components/media-card-skeleton";
import Pagination from "@/components/pagination";
import { tmdbService } from "@/lib/tmdb";
import { Search, Loader2, Filter, TrendingUp, Calendar, Star, Heart, Plus, Eye, Clock } from "lucide-react";
import { useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { useWatchlist } from "@/hooks/useWatchlist";
import type { Movie } from "@shared/schema";
import { usePageMeta } from "@/hooks/usePageMeta";
import { useTranslation } from "react-i18next";

export default function Movies() {
  const { t } = useTranslation();

  usePageMeta({
    title: t("nav.movies"),
    description: "Browse trending, top-rated, and upcoming movies. Discover your next favorite film on CineGraph.",
  });

  const [location] = useLocation();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedGenre, setSelectedGenre] = useState("all");
  const [selectedYear, setSelectedYear] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [activeTab, setActiveTab] = useState("discover");
  const { isInWatchlist } = useWatchlist();
  const [searchType, setSearchType] = useState("movies");

  const [trendingPage, setTrendingPage] = useState(1);
  const [nowPlayingPage, setNowPlayingPage] = useState(1);
  const [upcomingPage, setUpcomingPage] = useState(1);
  const [indianPage, setIndianPage] = useState(1);

  const [indianSearchQuery, setIndianSearchQuery] = useState("");
  const [indianRegion, setIndianRegion] = useState("all");
  const [indianGenre, setIndianGenre] = useState("all");
  const [indianYear, setIndianYear] = useState("all");
  const [indianSortBy, setIndianSortBy] = useState("popular");

  // Handle URL parameters for genre filtering
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const genreParam = urlParams.get('genre');
    if (genreParam) {
      setSelectedGenre(decodeURIComponent(genreParam));
    }
  }, [location]);

  // Scroll to top when pagination changes
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage, trendingPage, nowPlayingPage, upcomingPage, indianPage]);

  // Get genres from TMDB
  const { data: genresData } = useQuery({
    queryKey: ['/api/tmdb/genres/movies'],
    select: (data: any) => data.genres || []
  });

  // Get movie certifications
  const { data: certificationsData } = useQuery({
    queryKey: ['/api/tmdb/certification/movie/list'],
    select: (data: any) => data.certifications || {}
  });

  // Get recent movie changes
  const { data: changesData } = useQuery({
    queryKey: ['/api/tmdb/movie/changes'],
    select: (data: any) => data.results || []
  });

  // Get trending movies
  const { data: trendingData, isLoading: trendingLoading } = useQuery({
    queryKey: ['/api/tmdb/trending', trendingPage],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/trending?page=${trendingPage}`);
      if (!response.ok) throw new Error('Failed to fetch trending movies');
      return response.json();
    }
  });

  // Get now playing movies
  const { data: nowPlayingData, isLoading: nowPlayingLoading } = useQuery({
    queryKey: ['/api/tmdb/movies/now-playing', nowPlayingPage],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/movies/now-playing?page=${nowPlayingPage}`);
      if (!response.ok) throw new Error('Failed to fetch now playing movies');
      return response.json();
    }
  });

  // Get upcoming movies
  const { data: upcomingData, isLoading: upcomingLoading } = useQuery({
    queryKey: ['/api/tmdb/movies/upcoming', upcomingPage],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/movies/upcoming?page=${upcomingPage}`);
      if (!response.ok) throw new Error('Failed to fetch upcoming movies');
      return response.json();
    }
  });

  // Get Indian movies with search and region filter
  const { data: indianMoviesData, isLoading: indianMoviesLoading } = useQuery({
    queryKey: ['/api/tmdb/movies/indian', indianPage, indianSearchQuery, indianRegion, indianGenre, indianYear, indianSortBy],
    queryFn: async () => {
      // Determine languages based on region filter
      let allowedLanguages = ['hi', 'ta', 'te', 'ml', 'kn', 'bn']; // All Indian languages
      if (indianRegion === 'bollywood') {
        allowedLanguages = ['hi']; // Hindi (Bollywood)
      } else if (indianRegion === 'south') {
        allowedLanguages = ['ta', 'te', 'ml', 'kn']; // Tamil, Telugu, Malayalam, Kannada
      }

      // If there's a search query, use the search API and apply filters
      if (indianSearchQuery) {
        const response = await fetch(`/api/tmdb/search/movies?query=${encodeURIComponent(indianSearchQuery)}&page=${indianPage}`);
        if (!response.ok) throw new Error('Failed to search Indian movies');
        const data = await response.json();

        // Filter results by language (region), genre, and year
        const filteredResults = data.results.filter((movie: any) => {
          // Check language
          if (!movie.original_language || !allowedLanguages.includes(movie.original_language)) {
            return false;
          }

          // Check genre if selected
          if (indianGenre !== "all") {
            const genreId = genresData?.find((g: any) => g.name === indianGenre)?.id;
            if (genreId && (!movie.genre_ids || !movie.genre_ids.includes(genreId))) {
              return false;
            }
          }

          // Check year if selected
          if (indianYear !== "all") {
            const releaseYear = movie.release_date?.substring(0, 4);
            if (releaseYear !== indianYear) {
              return false;
            }
          }

          return true;
        });

        return { ...data, results: filteredResults };
      }

      // Build query params based on filters for discover API
      const languageParam = allowedLanguages.join('|');

      // Determine sort parameter
      let sortParam = 'popularity.desc';
      if (indianSortBy === 'top_rated') {
        sortParam = 'vote_average.desc';
      } else if (indianSortBy === 'now_playing') {
        sortParam = 'popularity.desc'; // For now playing, we'll use date filters
      }

      const params = new URLSearchParams({
        page: indianPage.toString(),
        region: 'IN',
        with_original_language: languageParam,
        sort_by: sortParam
      });

      // If sorting by trending, add recent date range for simulated trending
      if (indianSortBy === 'trending' && !indianSearchQuery) {
        // Get movies from the last 3 months sorted by popularity
        const threeMonthsAgo = new Date();
        threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
        const formattedDate = threeMonthsAgo.toISOString().split('T')[0];

        params.append('primary_release_date.gte', formattedDate);
        params.set('sort_by', 'popularity.desc');
        params.append('vote_count.gte', '10'); // Minimum votes to ensure quality
      }

      // Add vote count filter for top rated
      if (indianSortBy === 'top_rated') {
        params.append('vote_count.gte', '100');
      }

      // Add date filters for now playing
      if (indianSortBy === 'now_playing') {
        const today = new Date();
        const sixtyDaysAgo = new Date(today);
        sixtyDaysAgo.setDate(today.getDate() - 60);

        params.append('primary_release_date.gte', sixtyDaysAgo.toISOString().split('T')[0]);
        params.append('primary_release_date.lte', today.toISOString().split('T')[0]);
      }

      // Add genre filter if selected
      if (indianGenre !== "all") {
        const genreId = genresData?.find((g: any) => g.name === indianGenre)?.id;
        if (genreId) {
          params.append('with_genres', genreId.toString());
        }
      }

      // Add year filter if selected (override date filters for now playing if year is set)
      if (indianYear !== "all") {
        params.append('primary_release_year', indianYear);
      }

      const response = await fetch(`/api/tmdb/discover/movies?${params.toString()}`);
      if (!response.ok) throw new Error('Failed to fetch Indian movies');
      return response.json();
    }
  });

  // Reset Indian movies page when filters change
  useEffect(() => {
    setIndianPage(1);
  }, [indianSearchQuery, indianRegion, indianGenre, indianYear, indianSortBy]);

  // Multi-search functionality
  const { data: multiSearchData, isLoading: isMultiSearchLoading } = useQuery({
    queryKey: [`/api/tmdb/search/${searchType}`, searchQuery],
    enabled: !!searchQuery && activeTab === 'search',
    select: (data: any) => data.results || []
  });

  // Get movies from TMDB with filters
  const { data: moviesData, isLoading, error } = useQuery({
    queryKey: ['/api/tmdb/movies', searchQuery, selectedGenre, selectedYear, currentPage],
    queryFn: async () => {
      const params: any = { page: currentPage };

      if (searchQuery) {
        const searchResults = await tmdbService.searchMovies(searchQuery, currentPage);
        return {
          results: searchResults.results.map(item => tmdbService.convertToMovie(item, 'movie')),
          total_pages: searchResults.total_pages
        };
      }

      if (selectedGenre !== "all") {
        const genreId = genresData?.find((g: any) => g.name === selectedGenre)?.id;
        if (genreId !== undefined) {
          params.with_genres = genreId;
        }
      }
      if (selectedYear !== "all") {
        params.primary_release_year = selectedYear;
      }

      const discoverResults = await tmdbService.discoverMovies(params);
      return {
        results: discoverResults.results.map(item => tmdbService.convertToMovie(item, 'movie')),
        total_pages: discoverResults.total_pages
      };
    },
    enabled: selectedGenre === "all" || !!searchQuery || !!genresData
  });

  const movies = moviesData?.results || [];
  const totalPages = moviesData?.total_pages || 1;
  const genres = genresData || [];

  const trendingMovies = trendingData?.results?.filter((item: any) => item.media_type === 'movie') || [];
  const trendingTotalPages = trendingData?.total_pages || 1;
  const nowPlayingMovies = nowPlayingData?.results || [];
  const nowPlayingTotalPages = nowPlayingData?.total_pages || 1;
  const upcomingMovies = upcomingData?.results || [];
  const upcomingTotalPages = upcomingData?.total_pages || 1;
  const indianMovies = indianMoviesData?.results || [];
  const indianTotalPages = indianMoviesData?.total_pages || 1;

  // Generate years for filter (1990-2025 plus 2026 for upcoming)
  const years = Array.from({ length: 37 }, (_, i) => (2026 - i).toString()).sort((a, b) => parseInt(b) - parseInt(a));

  // Genre emoji mapping
  const genreEmojis: Record<string, string> = {
    "Action": "💥",
    "Adventure": "🗺️",
    "Animation": "🎨",
    "Comedy": "😂",
    "Crime": "🔫",
    "Documentary": "🎥",
    "Drama": "🎭",
    "Family": "👨‍👩‍👧‍👦",
    "Fantasy": "🧙",
    "History": "📜",
    "Horror": "👻",
    "Music": "🎵",
    "Mystery": "🔍",
    "Romance": "❤️",
    "Science Fiction": "🚀",
    "TV Movie": "📺",
    "Thriller": "😱",
    "War": "⚔️",
    "Western": "🤠"
  };

  return (
    <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold mb-4">{t("movies.title")}</h1>

        {/* Enhanced Tabs Interface */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="overflow-x-auto scrollbar-none -mx-4 px-4 sm:mx-0 sm:px-0 mb-1">
            <TabsList className="inline-flex w-max sm:grid sm:grid-cols-5 sm:w-full gap-0.5 sm:gap-1">
              <TabsTrigger value="discover" data-testid="tab-discover" className="text-xs sm:text-sm px-3 gap-1.5">
                <Filter className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                {t("movies.discover")}
              </TabsTrigger>
              <TabsTrigger value="trending" data-testid="tab-trending" className="text-xs sm:text-sm px-3 gap-1.5">
                <TrendingUp className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                {t("movies.trending")}
              </TabsTrigger>
              <TabsTrigger value="now-playing" data-testid="tab-now-playing" className="text-xs sm:text-sm px-3 gap-1.5">
                <Clock className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                {t("movies.nowPlaying")}
              </TabsTrigger>
              <TabsTrigger value="upcoming" data-testid="tab-upcoming" className="text-xs sm:text-sm px-3 gap-1.5">
                <Calendar className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                {t("movies.upcoming")}
              </TabsTrigger>
              <TabsTrigger value="indian" data-testid="tab-indian" className="text-xs sm:text-sm px-3 gap-1.5">
                <Star className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                {t("movies.indian")}
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Discover Tab */}
          <TabsContent value="discover" className="space-y-6">
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={t("movies.searchMovies")}
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => {
                    const query = e.target.value;
                    setSearchQuery(query);
                  }}
                  data-testid="input-discover-search"
                />
              </div>

              <div className="flex gap-3 sm:gap-4">
                <Select value={selectedGenre} onValueChange={setSelectedGenre}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="🎬 All Genres" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">🎬 All Genres</SelectItem>
                    {genres.map((genre: any) => (
                      <SelectItem key={genre.id} value={genre.name}>
                        {genreEmojis[genre.name] ? `${genreEmojis[genre.name]} ${genre.name}` : genre.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={selectedYear} onValueChange={setSelectedYear}>
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="📅 All Years" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">📅 All Years</SelectItem>
                    {years.map((year) => (
                      <SelectItem key={year} value={year}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {isLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                {Array.from({ length: 10 }, (_, i) => (
                  <MediaCardSkeleton key={i} />
                ))}
              </div>
            ) : error ? (
              <div className="text-center py-8 sm:py-12">
                <p className="text-sm sm:text-base text-muted-foreground">{t("movies.failedToLoad")}</p>
              </div>
            ) : movies.length === 0 ? (
              <div className="text-center py-8 sm:py-12">
                <p className="text-sm sm:text-base text-muted-foreground">
                  {searchQuery ? t("movies.noMoviesSearch", { query: searchQuery }) : t("movies.noMoviesFound")}
                </p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                  {movies.map((movie: Movie, index: number) => (
                    <MediaCard
                      key={movie.id}
                      movie={movie}
                      isInWatchlist={isInWatchlist(movie.id)}
                      priority={index < 4}
                    />
                  ))}
                </div>

                <Pagination
                  currentPage={currentPage}
                  totalPages={totalPages}
                  onPageChange={setCurrentPage}
                  testIdPrefix="discover"
                />
              </>
            )}
          </TabsContent>



          {/* Trending Tab */}
          <TabsContent value="trending" className="space-y-6">
            {trendingLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                {Array.from({ length: 20 }, (_, i) => (
                  <MediaCardSkeleton key={i} />
                ))}
              </div>
            ) : trendingMovies.length > 0 ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                  {trendingMovies.map((movie: any, index: number) => {
                    const convertedMovie = tmdbService.convertToMovie(movie, 'movie');
                    return (
                      <MediaCard
                        key={movie.id}
                        movie={convertedMovie}
                        isInWatchlist={isInWatchlist(convertedMovie.id)}
                        priority={index < 4}
                      />
                    );
                  })}
                </div>

                <Pagination
                  currentPage={trendingPage}
                  totalPages={trendingTotalPages}
                  onPageChange={setTrendingPage}
                  testIdPrefix="trending"
                />
              </>
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No trending movies available</p>
              </div>
            )}
          </TabsContent>

          {/* Now Playing Tab */}
          <TabsContent value="now-playing" className="space-y-6">
            {nowPlayingLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                {Array.from({ length: 20 }, (_, i) => (
                  <MediaCardSkeleton key={i} />
                ))}
              </div>
            ) : nowPlayingMovies.length > 0 ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                  {nowPlayingMovies.map((movie: any, index: number) => {
                    const convertedMovie = tmdbService.convertToMovie(movie, 'movie');
                    return (
                      <MediaCard
                        key={movie.id}
                        movie={convertedMovie}
                        isInWatchlist={isInWatchlist(convertedMovie.id)}
                        priority={index < 4}
                      />
                    );
                  })}
                </div>

                <Pagination
                  currentPage={nowPlayingPage}
                  totalPages={nowPlayingTotalPages}
                  onPageChange={setNowPlayingPage}
                  testIdPrefix="now-playing"
                />
              </>
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No current releases available</p>
              </div>
            )}
          </TabsContent>

          {/* Upcoming Tab */}
          <TabsContent value="upcoming" className="space-y-6">
            {upcomingLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                {Array.from({ length: 20 }, (_, i) => (
                  <MediaCardSkeleton key={i} />
                ))}
              </div>
            ) : upcomingMovies.length > 0 ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                  {upcomingMovies.map((movie: any, index: number) => {
                    const convertedMovie = tmdbService.convertToMovie(movie, 'movie');
                    return (
                      <MediaCard
                        key={movie.id}
                        movie={convertedMovie}
                        isInWatchlist={isInWatchlist(convertedMovie.id)}
                        priority={index < 4}
                      />
                    );
                  })}
                </div>

                <Pagination
                  currentPage={upcomingPage}
                  totalPages={upcomingTotalPages}
                  onPageChange={setUpcomingPage}
                  testIdPrefix="upcoming"
                />
              </>
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No upcoming releases available</p>
              </div>
            )}
          </TabsContent>

          {/* Indian Movies Tab */}
          <TabsContent value="indian" className="space-y-6">
            <div className="flex flex-col gap-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search Indian movies..."
                  className="pl-10"
                  value={indianSearchQuery}
                  onChange={(e) => setIndianSearchQuery(e.target.value)}
                  data-testid="input-indian-search"
                />
              </div>

              <div className="grid grid-cols-2 sm:flex gap-3 sm:gap-4">
                <Select value={indianRegion} onValueChange={setIndianRegion}>
                  <SelectTrigger className="w-full sm:w-[200px]" data-testid="select-indian-region">
                    <SelectValue placeholder="🌍 All Regions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">🌍 All Indian Movies</SelectItem>
                    <SelectItem value="bollywood">🎬 Bollywood (Hindi)</SelectItem>
                    <SelectItem value="south">🎭 South Indian</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={indianSortBy} onValueChange={setIndianSortBy}>
                  <SelectTrigger className="w-full sm:w-[200px]" data-testid="select-indian-sort">
                    <SelectValue placeholder="📊 Sort By" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="popular">🔥 Popular</SelectItem>
                    <SelectItem value="trending">📈 Trending</SelectItem>
                    <SelectItem value="top_rated">⭐ Top Rated</SelectItem>
                    <SelectItem value="now_playing">▶️ Now Playing</SelectItem>
                  </SelectContent>
                </Select>

                <Select value={indianGenre} onValueChange={setIndianGenre}>
                  <SelectTrigger className="w-full sm:w-[200px]" data-testid="select-indian-genre">
                    <SelectValue placeholder="🎬 All Genres" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">🎬 All Genres</SelectItem>
                    {genres.map((genre: any) => (
                      <SelectItem key={genre.id} value={genre.name}>
                        {genreEmojis[genre.name] ? `${genreEmojis[genre.name]} ${genre.name}` : genre.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                <Select value={indianYear} onValueChange={setIndianYear}>
                  <SelectTrigger className="w-full sm:w-[200px]" data-testid="select-indian-year">
                    <SelectValue placeholder="📅 All Years" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">📅 All Years</SelectItem>
                    {years.map((year) => (
                      <SelectItem key={year} value={year}>
                        {year}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {indianMoviesLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                {Array.from({ length: 20 }, (_, i) => (
                  <MediaCardSkeleton key={i} />
                ))}
              </div>
            ) : indianMovies.length > 0 ? (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 sm:gap-4 md:gap-6">
                  {indianMovies.map((movie: any, index: number) => {
                    const convertedMovie = tmdbService.convertToMovie(movie, 'movie');
                    return (
                      <MediaCard
                        key={movie.id}
                        movie={convertedMovie}
                        isInWatchlist={isInWatchlist(convertedMovie.id)}
                        priority={index < 4}
                      />
                    );
                  })}
                </div>

                <Pagination
                  currentPage={indianPage}
                  totalPages={indianTotalPages}
                  onPageChange={setIndianPage}
                  testIdPrefix="indian"
                />
              </>
            ) : (
              <div className="text-center py-12">
                <p className="text-muted-foreground">
                  {indianSearchQuery ? `No Indian movies found for "${indianSearchQuery}"` : "No Indian movies available"}
                </p>
              </div>
            )}
          </TabsContent>

        </Tabs>
      </div>
    </div>
  );
}
