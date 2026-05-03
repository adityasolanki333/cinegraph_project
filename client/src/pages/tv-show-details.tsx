import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "wouter";
import { Star, Play, ArrowLeft } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { WatchProviders } from "@/components/watch-providers";
import TVShowDetailsSkeleton from "@/components/tv-show-details-skeleton";
import { MediaDetails, type MediaDetailsConfig } from "@/components/media-details";
import { SimilarContent } from "@/components/similar-content";
import type { Movie } from "@shared/schema";

interface TVShowDetailsData {
  id: number;
  name: string;
  overview: string;
  first_air_date: string;
  last_air_date: string;
  number_of_seasons: number;
  number_of_episodes: number;
  vote_average: number;
  vote_count: number;
  popularity: number;
  poster_path?: string;
  backdrop_path?: string;
  original_language?: string;
  genres: Array<{ id: number; name: string }>;
  created_by: Array<{ id: number; name: string }>;
  networks: Array<{ id: number; name: string; logo_path?: string }>;
  production_companies: Array<{ id: number; name: string }>;
  status: string;
  type: string;
  episode_run_time: number[];
  in_production: boolean;
  seasons?: Array<{
    id: number;
    air_date: string;
    episode_count: number;
    name: string;
    overview: string;
    poster_path?: string;
    season_number: number;
    vote_average: number;
  }>;
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
    }>;
  };
  similar?: {
    results: Array<{
      id: number;
      name: string;
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

interface SeasonDetails {
  id: number;
  air_date: string;
  episodes: Array<{
    id: number;
    name: string;
    overview: string;
    air_date: string;
    episode_number: number;
    runtime?: number;
    season_number: number;
    still_path?: string;
    vote_average: number;
    vote_count: number;
  }>;
  name: string;
  overview: string;
  poster_path?: string;
  season_number: number;
}

export default function TVShowDetailsPage() {
  const params = useParams();
  const tvId = params.id;
  const [selectedSeason, setSelectedSeason] = useState<number>(1);

  const { data: tvShow, isLoading, error } = useQuery({
    queryKey: ['/api/tmdb/tv', tvId],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/tv/${tvId}`);
      if (!response.ok) throw new Error('Failed to fetch TV show details');
      return response.json();
    },
    enabled: !!tvId,
    select: (data: TVShowDetailsData) => data
  });

  const { data: seasonData, isLoading: isSeasonLoading } = useQuery({
    queryKey: ['/api/tmdb/tv', tvId, 'season', selectedSeason],
    queryFn: async () => {
      const response = await fetch(`/api/tmdb/tv/${tvId}/season/${selectedSeason}`);
      if (!response.ok) throw new Error('Failed to fetch season data');
      return response.json();
    },
    enabled: !!tvId && !!selectedSeason,
    select: (data: SeasonDetails) => data
  });

  if (isLoading) {
    return <TVShowDetailsSkeleton />;
  }

  if (error || !tvShow) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">TV Show Not Found</h1>
          <p className="text-muted-foreground mb-4">
            The TV show you're looking for doesn't exist or couldn't be loaded.
          </p>
          <Button onClick={() => window.history.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    );
  }

  const mainCast = tvShow.credits?.cast?.slice(0, 6) || [];
  const trailers = tvShow.videos?.results?.filter(video =>
    video.type === 'Trailer' && video.site === 'YouTube'
  ) || [];

  const movieData: Movie = {
    id: tvShow.id.toString(),
    title: tvShow.name,
    year: new Date(tvShow.first_air_date).getFullYear(),
    genre: tvShow.genres[0]?.name || 'Drama',
    rating: tvShow.vote_average,
    synopsis: tvShow.overview,
    posterUrl: tvShow.poster_path ? `https://image.tmdb.org/t/p/w500${tvShow.poster_path}` : undefined,
    director: tvShow.created_by[0]?.name || 'Unknown',
    cast: tvShow.credits?.cast?.slice(0, 5).map(actor => actor.name) || [],
    duration: tvShow.episode_run_time[0] || undefined,
    type: 'tv',
    seasons: tvShow.number_of_seasons,
  };

  const config: MediaDetailsConfig = {
    mediaType: 'tv',
    id: tvId!,
    title: tvShow.name,
    date: tvShow.first_air_date,
    overview: tvShow.overview,
    durationLabel: `${tvShow.number_of_seasons} seasons`,
    voteAverage: tvShow.vote_average,
    voteCount: tvShow.vote_count,
    posterPath: tvShow.poster_path,
    backdropPath: tvShow.backdrop_path,
    originalLanguage: tvShow.original_language,
    genres: tvShow.genres,
    tmdbId: tvShow.id,
    cast: mainCast,
    trailers,
    similarItems: tvShow.similar?.results?.map(s => ({ ...s, title: undefined, name: s.name })),
    movieData,
    tabCount: 6,
    detailsTab: <TVDetailsTab tvShow={tvShow} tvId={tvId!} />,
    episodesTab: (
      <EpisodesTab
        tvShow={tvShow}
        tvId={tvId!}
        selectedSeason={selectedSeason}
        setSelectedSeason={setSelectedSeason}
        seasonData={seasonData}
        isSeasonLoading={isSeasonLoading}
      />
    ),
    similarTab: (
      <SimilarContent
        title={tvShow.name}
        overview={tvShow.overview}
        mediaType="tv"
        currentTmdbId={tvShow.id}
      />
    ),
  };

  return <MediaDetails config={config} />;
}

function TVDetailsTab({ tvShow, tvId }: { tvShow: TVShowDetailsData; tvId: string }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4 sm:space-y-6 md:space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
        <Card>
          <CardHeader>
            <CardTitle>{t('mediaDetails.showInformation')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-semibold">{t('mediaDetails.status')}</h4>
              <p className="text-muted-foreground">{tvShow.status}</p>
            </div>

            <div>
              <h4 className="font-semibold">{t('mediaDetails.showType')}</h4>
              <p className="text-muted-foreground">{tvShow.type}</p>
            </div>

            <div>
              <h4 className="font-semibold">{t('mediaDetails.firstAirDate')}</h4>
              <p className="text-muted-foreground">{tvShow.first_air_date}</p>
            </div>

            {tvShow.last_air_date && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.lastAirDate')}</h4>
                <p className="text-muted-foreground">{tvShow.last_air_date}</p>
              </div>
            )}

            <div>
              <h4 className="font-semibold">{t('mediaDetails.numSeasons')}</h4>
              <p className="text-muted-foreground">{tvShow.number_of_seasons}</p>
            </div>

            <div>
              <h4 className="font-semibold">{t('mediaDetails.numEpisodes')}</h4>
              <p className="text-muted-foreground">{tvShow.number_of_episodes}</p>
            </div>

            {tvShow.episode_run_time.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.episodeRuntime')}</h4>
                <p className="text-muted-foreground">
                  {tvShow.episode_run_time.join(', ')} {t('mediaDetails.minutes')}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('mediaDetails.production')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {tvShow.created_by.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.createdBy')}</h4>
                <p className="text-muted-foreground">
                  {tvShow.created_by.map(creator => creator.name).join(', ')}
                </p>
              </div>
            )}

            {tvShow.networks.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.networks')}</h4>
                <p className="text-muted-foreground">
                  {tvShow.networks.map(network => network.name).join(', ')}
                </p>
              </div>
            )}

            {tvShow.production_companies.length > 0 && (
              <div>
                <h4 className="font-semibold">{t('mediaDetails.productionCompanies')}</h4>
                <p className="text-muted-foreground">
                  {tvShow.production_companies.map(company => company.name).join(', ')}
                </p>
              </div>
            )}

            <div>
              <h4 className="font-semibold">{t('mediaDetails.inProduction')}</h4>
              <p className="text-muted-foreground">
                {tvShow.in_production ? t('mediaDetails.yes') : t('mediaDetails.no')}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <WatchProviders tmdbId={parseInt(tvId || '0')} mediaType="tv" />
    </div>
  );
}

function EpisodesTab({
  tvShow,
  tvId,
  selectedSeason,
  setSelectedSeason,
  seasonData,
  isSeasonLoading
}: {
  tvShow: TVShowDetailsData;
  tvId: string;
  selectedSeason: number;
  setSelectedSeason: (season: number) => void;
  seasonData?: SeasonDetails;
  isSeasonLoading: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      {tvShow?.seasons && tvShow.seasons.length > 0 && (
        <div className="flex items-center gap-4">
          <label htmlFor="season-select" className="font-semibold">{t('mediaDetails.seasonLabel')}</label>
          <Select
            value={selectedSeason.toString()}
            onValueChange={(value) => setSelectedSeason(parseInt(value))}
          >
            <SelectTrigger id="season-select" className="w-48">
              <SelectValue placeholder={t('mediaDetails.selectSeason')} />
            </SelectTrigger>
            <SelectContent>
              {tvShow.seasons
                .filter(season => season.season_number > 0)
                .map((season) => (
                  <SelectItem key={season.id} value={season.season_number.toString()}>
                    {season.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {isSeasonLoading ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-muted-foreground">{t('mediaDetails.loadingEpisodes')}</p>
          </CardContent>
        </Card>
      ) : seasonData?.episodes ? (
        <div className="space-y-4">
          {seasonData.episodes.map((episode) => (
            <Card key={episode.id} className="hover:shadow-lg transition-shadow">
              <CardContent className="p-6">
                <div className="grid md:grid-cols-4 gap-4">
                  <div className="aspect-video bg-muted rounded flex items-center justify-center">
                    {episode.still_path ? (
                      <img
                        src={`https://image.tmdb.org/t/p/w500${episode.still_path}`}
                        alt={episode.name}
                        className="w-full h-full object-cover rounded"
                        loading="lazy"
                      />
                    ) : (
                      <Play className="h-8 w-8 text-muted-foreground" />
                    )}
                  </div>

                  <div className="md:col-span-3 space-y-2">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-semibold text-lg">
                          {episode.episode_number}. {episode.name}
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          {episode.air_date} {episode.runtime && `• ${episode.runtime} min`}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="text-sm">{episode.vote_average.toFixed(1)}</span>
                      </div>
                    </div>

                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {episode.overview || t('mediaDetails.noDescription')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-6">
            <p className="text-center text-muted-foreground">
              {t('mediaDetails.noEpisodes')}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
