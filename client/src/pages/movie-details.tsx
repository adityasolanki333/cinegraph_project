import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { Star, Sparkles, ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { MediaCard } from "@/components/media-card";
import { WatchProviders } from "@/components/watch-providers";
import MovieDetailsSkeleton from "@/components/movie-details-skeleton";
import { MediaDetails, type MediaDetailsConfig } from "@/components/media-details";
import type { Movie } from "@shared/schema";

interface MovieDetailsData {
  id: number;
  title: string;
  overview: string;
  release_date: string;
  runtime?: number;
  vote_average: number;
  vote_count: number;
  popularity: number;
  poster_path?: string;
  backdrop_path?: string;
  original_language?: string;
  genres: Array<{ id: number; name: string }>;
  production_companies: Array<{ id: number; name: string }>;
  production_countries: Array<{ iso_3166_1: string; name: string }>;
  spoken_languages: Array<{ iso_639_1: string; name: string }>;
  status: string;
  tagline?: string;
  budget: number;
  revenue: number;
  belongs_to_collection?: {
    id: number;
    name: string;
    poster_path: string;
    backdrop_path: string;
  } | null;
  credits?: {
    cast: Array<{
      id: number;
      name: string;
      character: string;
      profile_path?: string;
    }>;
    crew: Array<{
      id: number;
      name: string;
      job: string;
      department: string;
    }>;
  };
  videos?: {
    results: Array<{
      id: string;
      key: string;
      name: string;
      site: string;
      type: string;
      iso_639_1?: string;
    }>;
  };
  similar?: {
    results: Array<{
      id: number;
      title: string;
      poster_path?: string;
      vote_average: number;
    }>;
  };
  external_ids?: {
    imdb_id?: string;
    facebook_id?: string;
    instagram_id?: string;
    twitter_id?: string;
  };
}

export default function MovieDetailsPage() {
  const params = useParams();
  const movieId = params.id;

  const { data: movie, isLoading, error } = useQuery({
    queryKey: ['/api/tmdb/movie', movieId],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/movie/${movieId}`);
      if (!response.ok) throw new Error('Failed to fetch movie details');
      return response.json();
    },
    enabled: !!movieId,
    select: (data: MovieDetailsData) => data
  });

  if (isLoading) {
    return <MovieDetailsSkeleton />;
  }

  if (error || !movie) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Movie Not Found</h1>
          <p className="text-muted-foreground mb-4">
            The movie you're looking for doesn't exist or couldn't be loaded.
          </p>
          <Button onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const mainCast = movie.credits?.cast?.slice(0, 6) || [];
  const trailers = movie.videos?.results?.filter(video =>
    video.type === 'Trailer' && video.site === 'YouTube'
  ) || [];

  const movieData: Movie = {
    id: movie.id.toString(),
    title: movie.title,
    year: new Date(movie.release_date).getFullYear(),
    genre: movie.genres[0]?.name || 'Drama',
    rating: movie.vote_average,
    synopsis: movie.overview,
    posterUrl: movie.poster_path ? `https://image.tmdb.org/t/p/w500${movie.poster_path}` : undefined,
    director: movie.credits?.crew?.find(member => member.job === 'Director')?.name || 'Unknown',
    cast: movie.credits?.cast?.slice(0, 5).map(actor => actor.name) || [],
    duration: movie.runtime || undefined,
    type: 'movie',
    seasons: undefined,
  };

  const config: MediaDetailsConfig = {
    mediaType: 'movie',
    id: movieId!,
    title: movie.title,
    date: movie.release_date,
    overview: movie.overview,
    durationLabel: movie.runtime ? `${movie.runtime} min` : '',
    voteAverage: movie.vote_average,
    voteCount: movie.vote_count,
    posterPath: movie.poster_path,
    backdropPath: movie.backdrop_path,
    originalLanguage: movie.original_language,
    genres: movie.genres,
    tmdbId: movie.id,
    cast: mainCast,
    trailers,
    similarItems: movie.similar?.results,
    movieData,
    tabCount: 5,
    detailsTab: <MovieDetailsTab movie={movie} movieId={movieId!} />,
    similarTab: (
      <SemanticSimilarMovies
        movieTitle={movie.title}
        movieOverview={movie.overview}
        currentMovieId={movie.id}
        genres={movie.genres}
        cast={movie.credits?.cast}
        tagline={movie.tagline}
        collection={movie.belongs_to_collection}
      />
    ),
  };

  return <MediaDetails config={config} />;
}

function MovieDetailsTab({ movie, movieId }: { movie: MovieDetailsData; movieId: string }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4 sm:space-y-6 md:space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('mediaDetails.movieInformation')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold">{t('mediaDetails.status')}</h4>
              <p className="text-muted-foreground">{movie.status}</p>
            </div>

            <div>
              <h4 className="font-semibold">{t('mediaDetails.releaseDate')}</h4>
              <p className="text-muted-foreground">{movie.release_date}</p>
            </div>

            {movie.runtime && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.runtimeLabel')}</h4>
                <p className="text-muted-foreground">{movie.runtime} {t('mediaDetails.minutes')}</p>
              </div>
            )}

            {movie.budget > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.budget')}</h4>
                <p className="text-muted-foreground">${movie.budget.toLocaleString()}</p>
              </div>
            )}

            {movie.revenue > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.revenue')}</h4>
                <p className="text-muted-foreground">${movie.revenue.toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('mediaDetails.production')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {movie.production_companies.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.productionCompanies')}</h4>
                <p className="text-muted-foreground">
                  {movie.production_companies.map(company => company.name).join(', ')}
                </p>
              </div>
            )}

            {movie.production_countries.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.countries')}</h4>
                <p className="text-muted-foreground">
                  {movie.production_countries.map(country => country.name).join(', ')}
                </p>
              </div>
            )}

            {movie.spoken_languages.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.languages')}</h4>
                <p className="text-muted-foreground">
                  {movie.spoken_languages.map(lang => lang.name).join(', ')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <WatchProviders tmdbId={parseInt(movieId || '0')} mediaType="movie" />
    </div>
  );
}

function SemanticSimilarMovies({
  movieTitle,
  movieOverview,
  currentMovieId,
  genres,
  cast,
  tagline,
  collection
}: {
  movieTitle: string;
  movieOverview: string;
  currentMovieId: number;
  genres?: Array<{ id: number; name: string }>;
  cast?: Array<{ id: number; name: string; character: string }>;
  tagline?: string;
  collection?: { id: number; name: string; poster_path: string; backdrop_path: string } | null;
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const moviesPerPage = 12;

  const { data: semanticResults, isLoading: semanticLoading } = useQuery({
    queryKey: ['/api/ml/similar/semantic', currentMovieId],
    queryFn: async () => {
      const response = await fetch(`/api/ml/similar/semantic/${currentMovieId}`);
      if (!response.ok) return { results: [] };
      const data = await response.json();
      const items = data.similar_items || data.results || [];
      return {
        results: items.map((item: any) => ({
          id: item.tmdb_id ?? item.id,
          title: item.title || '',
          poster_path: item.poster_path || null,
          vote_average: item.vote_average ?? (item.similarity_score ? item.similarity_score * 10 : 0),
          release_date: item.release_date || '',
          overview: item.overview || '',
          genre: Array.isArray(item.genres) && item.genres.length > 0 ? item.genres[0] : '',
          genre_ids: Array.isArray(item.genre_ids) ? item.genre_ids : [],
          similarity: item.similarity_score ?? item.similarity ?? null,
          explanation: item.explanation || null,
        })),
      };
    },
    enabled: !!currentMovieId
  });

  const allMovies = semanticResults?.results || [];
  const indexOfLastMovie = currentPage * moviesPerPage;
  const indexOfFirstMovie = indexOfLastMovie - moviesPerPage;
  const currentMovies = allMovies.slice(indexOfFirstMovie, indexOfLastMovie);
  const totalPages = Math.ceil(allMovies.length / moviesPerPage);
  const paginate = (pageNumber: number) => setCurrentPage(pageNumber);

  if (semanticLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <Skeleton key={i} className="h-[400px] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (allMovies.length === 0) {
    return (
      <div className="text-center py-12">
        <Sparkles className="h-12 w-12 text-primary mx-auto mb-4 opacity-50" />
        <h3 className="text-xl font-medium mb-2">No AI Matches Found</h3>
        <p className="text-muted-foreground mb-6">
          Our AI couldn't find semantically similar movies in the vector database yet.
          Ensure the database is ingested.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-primary border-primary/30">
            <Sparkles className="w-3 h-3 mr-1" />
            Vector Embeddings
          </Badge>
          <span className="text-sm text-muted-foreground">
            Based on visual and thematic analysis
          </span>
        </div>
        <span className="text-xs text-muted-foreground">
          {allMovies.length} matches found
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        {currentMovies.map((movie: any) => (
          <div key={movie.id} className="group relative">
            <MediaCard
              item={{
                id: movie.id,
                title: movie.title,
                vote_average: movie.vote_average,
                poster_path: movie.poster_path,
                type: 'movie',
                release_date: movie.release_date,
                synopsis: movie.overview,
                genre: movie.genre,
                genre_ids: movie.genre_ids,
              }}
              mediaType="movie"
            />
            {movie.similarity && (
              <div className="absolute top-2 right-2 z-10">
                <Badge className="bg-primary/90 hover:bg-primary text-primary-foreground shadow-sm backdrop-blur-sm">
                  {Math.round(movie.similarity * 100)}% Match
                </Badge>
              </div>
            )}
            {movie.explanation && (
              <div className="mt-2 text-xs text-muted-foreground line-clamp-2 italic px-1">
                "{movie.explanation}"
              </div>
            )}
          </div>
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex justify-center mt-8 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => paginate(currentPage - 1)}
            disabled={currentPage === 1}
          >
            Previous
          </Button>
          <div className="flex items-center gap-1 mx-2">
            <span className="text-sm text-muted-foreground">
              Page {currentPage} of {totalPages}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => paginate(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
