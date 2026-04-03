import { z } from "zod";

export interface User {
  id: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  bio?: string;
  profileImageUrl?: string;
  createdAt?: Date;
}

export interface Movie {
  id: string;
  title: string;
  year: number;
  genre: string;
  genres?: string[];
  rating: number;
  synopsis?: string;
  posterUrl?: string;
  backdropUrl?: string;
  director?: string;
  cast?: string[];
  duration?: number;
  type: 'movie' | 'tv';
  seasons?: number;
  number_of_seasons?: number;
}

export interface UserRating {
  id: string;
  userId: string;
  tmdbId: number;
  mediaType: string;
  title: string;
  posterPath?: string;
  rating: number;
  review?: string;
  sentimentScore?: number;
  sentimentLabel?: string;
  helpfulCount?: number;
  isPublic?: boolean;
  createdAt?: Date;
}

export interface WatchlistItem {
  id: string;
  userId: string;
  tmdbId: number;
  mediaType: string;
  title: string;
  posterPath?: string;
  addedAt?: Date;
}

export interface UserList {
  id: string;
  userId: string;
  title: string;
  description?: string;
  isPublic?: boolean;
  followerCount?: number;
  itemCount?: number;
  createdAt?: Date;
}

export interface ListItem {
  id: string;
  listId: string;
  tmdbId: number;
  mediaType: string;
  title: string;
  posterPath?: string;
  note?: string;
  position?: number;
  addedAt?: Date;
}

export interface Recommendation {
  id: string;
  userId: string;
  tmdbId: number;
  mediaType: string;
  title: string;
  posterPath?: string;
  recommendationType: string;
  reason: string;
  confidence: number;
  relevanceScore: number;
  userInteracted?: boolean;
  userFeedback?: string;
  aiExplanation?: string;
}

export interface Notification {
  id: number;
  type: string;
  message: string;
  relatedUserId: number | null;
  relatedTmdbId: number | null;
  relatedMediaType: string | null;
  isRead: boolean;
  createdAt: string;
}

export interface UserCommunity {
  id: string;
  userId: string;
  communityName: string;
  matchPercentage: number;
  memberCount: number;
}

export interface ListCollaborator {
  id: string;
  listId: string;
  userId: string;
  permission: 'view' | 'edit' | 'admin';
  addedAt?: Date;
}

export const insertUserSchema = z.object({
  email: z.string().email().optional(),
  password: z.string().min(6).optional(),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
  bio: z.string().optional(),
  profileImageUrl: z.string().url().optional(),
});

export const insertRatingSchema = z.object({
  tmdbId: z.number(),
  mediaType: z.string(),
  title: z.string(),
  posterPath: z.string().optional(),
  rating: z.number().min(1).max(10),
  review: z.string().optional(),
});

export const insertWatchlistSchema = z.object({
  tmdbId: z.number(),
  mediaType: z.string(),
  title: z.string(),
  posterPath: z.string().optional(),
});

export const insertListCollaboratorSchema = z.object({
  listId: z.string(),
  userId: z.string(),
  permission: z.enum(['view', 'edit', 'admin']),
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type InsertRating = z.infer<typeof insertRatingSchema>;
export type InsertWatchlist = z.infer<typeof insertWatchlistSchema>;
export type InsertListCollaborator = z.infer<typeof insertListCollaboratorSchema>;

function resolvePosterUrl(posterUrl?: string, posterPath?: string): string | undefined {
  if (posterUrl) return posterUrl;
  if (!posterPath) return undefined;
  if (posterPath.startsWith('http')) return posterPath;
  return `https://image.tmdb.org/t/p/w500${posterPath}`;
}

function resolveBackdropUrl(backdropUrl?: string, backdropPath?: string): string | undefined {
  if (backdropUrl) return backdropUrl;
  if (!backdropPath) return undefined;
  if (backdropPath.startsWith('http')) return backdropPath;
  return `https://image.tmdb.org/t/p/w1280${backdropPath}`;
}

export function normalizeToMovie(item: any): Movie {
  return {
    id: (item.tmdbId ?? item.id)?.toString() ?? '',
    title: item.title || item.name || 'Unknown',
    year: item.releaseDate ? new Date(item.releaseDate).getFullYear() : (item.year || 0),
    genre: item.genre || '',
    rating: item.voteAverage || item.rating || 0,
    synopsis: item.overview || item.synopsis || '',
    posterUrl: resolvePosterUrl(item.posterUrl, item.posterPath),
    backdropUrl: resolveBackdropUrl(item.backdropUrl, item.backdropPath),
    director: item.director || '',
    cast: item.cast || [],
    duration: item.duration || item.runtime || 0,
    type: (item.type || item.mediaType || 'movie') as 'movie' | 'tv',
    seasons: item.seasons || item.number_of_seasons,
    number_of_seasons: item.number_of_seasons,
  };
}
