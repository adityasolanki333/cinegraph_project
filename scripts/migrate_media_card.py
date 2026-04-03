import os
import glob
import re

src_dir = r"c:\Users\solan\Desktop\Cinema-Guide\Cinema-Guide\client\src"

# 1. Update MediaCard content to contain MovieCard's logic
media_card_path = os.path.join(src_dir, 'components', 'media-card.tsx')
movie_card_path = os.path.join(src_dir, 'components', 'movie-card.tsx')

with open(movie_card_path, 'r', encoding='utf-8') as f:
    movie_card_content = f.read()

# Replace props
movie_card_content = re.sub(
    r'interface MovieCardProps \{.*?\}(?=\n\n|\nexport)',
    '''export interface MediaItem {
  id: number | string;
  title?: string;
  name?: string;
  rating?: number;
  vote_average?: number;
  year?: string | number;
  first_air_date?: string;
  last_air_date?: string;
  release_date?: string;
  genre?: string;
  genres?: Array<{ id: number; name: string }>;
  duration?: number;
  number_of_seasons?: number;
  synopsis?: string;
  overview?: string;
  poster_path?: string;
  posterUrl?: string;
  type?: 'movie' | 'tv';
  media_type?: 'movie' | 'tv';
  seasons?: number;
}

export interface MediaCardProps {
  item?: MediaItem;
  movie?: any;
  mediaType?: 'movie' | 'tv';
  isInWatchlist?: boolean;
  onAddToWatchlist?: (itemId: string) => void;
  onRemoveFromWatchlist?: (itemId: string) => void;
  onRate?: (itemId: string, rating: number) => void;
  userRating?: number;
  showRemoveButton?: boolean;
  showFeedback?: boolean;
  recommendationStrategy?: string;
  recommendationScore?: number;
  recommendationReason?: string;
  experimentId?: string;
  showExplanation?: boolean;
  priority?: boolean;
  children?: React.ReactNode;
}''', movie_card_content, flags=re.DOTALL)

# Replace signature
func_sig = '''export function MediaCard({
  item: propItem,
  movie: propMovie,
  mediaType,
  isInWatchlist: propIsInWatchlist,
  onAddToWatchlist,
  onRemoveFromWatchlist,
  onRate,
  userRating,
  showRemoveButton = false,
  showFeedback = false,
  recommendationStrategy,
  recommendationScore,
  recommendationReason,
  experimentId,
  priority = false,
  showExplanation = false,
  children,
}: MediaCardProps) {
  const item = propItem || propMovie;
  if (!item) return null;

  const type = mediaType || item.type || item.media_type || (item.name ? 'tv' : 'movie');
  const title = item.title || item.name || 'Untitled';
  const rating = item.rating || item.vote_average || 0;

  let yearStr = item.year || '';
  if (!yearStr) {
    if (type === 'tv') {
      if (item.last_air_date) {
        yearStr = new Date(item.last_air_date).getFullYear().toString();
      } else if (item.first_air_date) {
        yearStr = new Date(item.first_air_date).getFullYear().toString();
      }
    } else if (item.release_date) {
      yearStr = new Date(item.release_date).getFullYear().toString();
    }
  }

  const synopsis = item.synopsis || item.overview || '';
  const posterUrl = item.posterUrl || (item.poster_path ? `https://image.tmdb.org/t/p/w342${item.poster_path}` : undefined);
  const genreDisplay = item.genre || (item.genres && item.genres.length > 0 ? item.genres[0].name : '');

  const movie = {
    id: item.id.toString(),
    title: title,
    year: parseInt(yearStr) || new Date().getFullYear(),
    genre: genreDisplay || 'Unknown',
    rating: rating,
    synopsis: synopsis,
    posterUrl: posterUrl,
    type: type,
    seasons: item.number_of_seasons || item.seasons || undefined,
    duration: item.duration || undefined,
  };'''

movie_card_content = re.sub(
    r'export function MovieCard\(\{[\s\S]*?\} *: *(?:MovieCardProps & \{ priority\?: boolean \}|MovieCardProps)\) *\{',
    func_sig,
    movie_card_content
)

# Fix remaining MovieCard references
movie_card_content = movie_card_content.replace('MovieCardProps', 'MediaCardProps')

# Add children rendering
children_render = '''        </Card>
      </Link>
      {children && (
        <div className="mt-2" onClick={(e) => e.preventDefault()}>
          {children}
        </div>
      )}'''
movie_card_content = movie_card_content.replace('        </Card>\n      </Link>', children_render)

with open(media_card_path, 'w', encoding='utf-8') as f:
    f.write(movie_card_content)

# 2. Update imports and usages
for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith('.tsx') or file.endswith('.ts'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            new_content = new_content.replace('import { MovieCard } from "@/components/movie-card"', 'import { MediaCard } from "@/components/media-card"')
            new_content = new_content.replace('import { MovieCard } from "./movie-card"', 'import { MediaCard } from "./media-card"')
            new_content = new_content.replace('import { MovieCard } from "../components/movie-card"', 'import { MediaCard } from "../components/media-card"')
            new_content = new_content.replace('<MovieCard', '<MediaCard')
            new_content = new_content.replace('</MovieCard>', '</MediaCard>')
            
            # also, we might have `export { MovieCard }` somehwere
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

print("Migration completed successfully")
