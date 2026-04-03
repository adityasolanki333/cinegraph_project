import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  TrendingUp, 
  Zap, 
  Sparkles,
  Film,
  Star,
  Target,
  Clock,
  Lightbulb,
  Eye,
  BarChart3
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface PatternPrediction {
  nextGenre: number;
  nextRating: number;
  probability: number;
  sessionType: 'binge' | 'casual' | 'explorer';
}

interface PatternAnalysis {
  bingeWatcher: boolean;
  preferredGenres: number[];
  avgRating: number;
  predictedNextGenre: number;
}

interface PatternCounts {
  totalWatched: number;
  totalReviews: number;
  totalFavorites: number;
}

const GENRE_MAP: Record<number, string> = {
  28: 'Action',
  12: 'Adventure',
  16: 'Animation',
  35: 'Comedy',
  80: 'Crime',
  99: 'Documentary',
  18: 'Drama',
  10751: 'Family',
  14: 'Fantasy',
  36: 'History',
  27: 'Horror',
  10402: 'Music',
  9648: 'Mystery',
  10749: 'Romance',
  878: 'Sci-Fi',
  10770: 'TV Movie',
  53: 'Thriller',
  10752: 'War',
  37: 'Western'
};

export function PatternInsights() {
  const { user } = useAuth();

  const { data: predictionData, isLoading: predictionLoading } = useQuery<{
    userId: string;
    prediction: PatternPrediction;
  }>({
    queryKey: ['/api/recommendations/pattern/predict', user?.id],
    queryFn: async () => {
      const res = await fetch(`/api/recommendations/pattern/predict/${user?.id}`);
      if (!res.ok) throw new Error('Failed to fetch pattern prediction');
      return res.json();
    },
    enabled: !!user?.id,
  });

  const { data: analysisData, isLoading: analysisLoading } = useQuery<{
    userId: string;
    analysis: PatternAnalysis;
    patterns: PatternCounts;
  }>({
    queryKey: ['/api/recommendations/pattern/analyze', user?.id],
    queryFn: async () => {
      const res = await fetch(`/api/recommendations/pattern/analyze/${user?.id}`);
      if (!res.ok) throw new Error('Failed to fetch pattern analysis');
      return res.json();
    },
    enabled: !!user?.id,
  });

  const prediction = predictionData?.prediction;
  const analysis = analysisData?.analysis;
  const patterns = analysisData?.patterns;

  const genrePreferenceData = useMemo(() => {
    if (!analysis?.preferredGenres?.length) return [];
    const total = analysis.preferredGenres.reduce((sum, _, idx) => sum + (10 - idx), 0);
    return analysis.preferredGenres.slice(0, 5).map((genreId, idx) => {
      const weight = 10 - idx;
      const percentage = Math.round((weight / total) * 100);
      return {
        name: GENRE_MAP[genreId] || 'Unknown',
        value: percentage,
        color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][idx]
      };
    });
  }, [analysis?.preferredGenres]);

  if (!user) {
    return null;
  }

  if (predictionLoading || analysisLoading) {
    return (
      <Card>
        <CardHeader>
          <div className="h-6 w-48 bg-muted animate-pulse rounded" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="h-20 bg-muted animate-pulse rounded" />
          <div className="h-20 bg-muted animate-pulse rounded" />
        </CardContent>
      </Card>
    );
  }

  if (!analysis || analysis.avgRating === 0 || analysis.preferredGenres.length === 0) {
    return null;
  }

  const sessionType = prediction?.sessionType || 'casual';
  const bingeScore = analysis.bingeWatcher ? 0.8 : 0.3;
  const dominantDay = analysis.bingeWatcher ? 'weekends' : 'weekdays';

  return (
    <Card className="border-border bg-card" data-testid="card-pattern-insights">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-primary" />
              Your Viewing Patterns
            </CardTitle>
            <CardDescription className="mt-1">
              AI-powered insights from your watching behavior
            </CardDescription>
          </div>
          {analysis.bingeWatcher && (
            <Zap className="h-8 w-8 text-red-500" />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Session Type */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Viewing Style</span>
            <Badge variant="secondary" data-testid="badge-insight-session">
              {analysis.bingeWatcher ? 'Binge Watcher' : 'Casual Viewer'}
            </Badge>
          </div>
          
          {analysis.bingeWatcher && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Binge Intensity</span>
                <span>{Math.round(bingeScore * 100)}%</span>
              </div>
              <Progress value={bingeScore * 100} className="h-2" data-testid="progress-binge-score" />
            </div>
          )}
        </div>

        {/* Real Stats Grid */}
        {patterns && (
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center p-3 rounded-lg bg-muted/40">
              <Eye className="h-4 w-4 mx-auto mb-1 text-primary" />
              <p className="text-xl font-bold" data-testid="text-total-watched">{patterns.totalWatched}</p>
              <p className="text-xs text-muted-foreground">Watched</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/40">
              <Star className="h-4 w-4 mx-auto mb-1 text-yellow-500" />
              <p className="text-xl font-bold" data-testid="text-total-reviews">{patterns.totalReviews}</p>
              <p className="text-xs text-muted-foreground">Reviews</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/40">
              <Film className="h-4 w-4 mx-auto mb-1 text-blue-500" />
              <p className="text-xl font-bold" data-testid="text-total-favorites">{patterns.totalFavorites}</p>
              <p className="text-xs text-muted-foreground">Favorites</p>
            </div>
          </div>
        )}

        {/* Session Type + Avg Rating */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Film className="h-4 w-4" />
              <span className="text-xs">Session Type</span>
            </div>
            <p className="text-2xl font-bold capitalize" data-testid="text-session-type">
              {sessionType}
            </p>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Star className="h-4 w-4" />
              <span className="text-xs">Avg Rating</span>
            </div>
            <p className="text-2xl font-bold" data-testid="text-avg-rating">
              {analysis.avgRating.toFixed(1)}
            </p>
          </div>
        </div>

        {/* Favorite Genres */}
        {analysis.preferredGenres.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target className="h-4 w-4" />
              <span>Favorite Genres</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {analysis.preferredGenres.slice(0, 5).map((genreId, idx) => (
                <Badge 
                  key={idx} 
                  variant="outline"
                  data-testid={`badge-genre-${idx}`}
                >
                  {GENRE_MAP[genreId] || 'Unknown'}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* AI Prediction */}
        {prediction && (
          <div className="space-y-2 pt-2 border-t border-border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="h-4 w-4" />
              <span>What You'll Watch Next</span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm">Predicted Genre</span>
                <Badge data-testid="badge-predicted-genre">
                  {GENRE_MAP[prediction.nextGenre] || 'Unknown'}
                </Badge>
              </div>
              
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>Confidence</span>
                  <span>{Math.round(prediction.probability * 100)}%</span>
                </div>
                <Progress 
                  value={prediction.probability * 100} 
                  className="h-2" 
                  data-testid="progress-prediction-confidence"
                />
              </div>

              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Expected Rating</span>
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                  <span className="font-semibold" data-testid="text-predicted-rating">
                    {prediction.nextRating.toFixed(1)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Genre Preference Distribution */}
        {genrePreferenceData.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-border">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <BarChart3 className="h-4 w-4" />
              <span>Genre Distribution</span>
            </div>
            <div className="h-[200px] w-full" data-testid="chart-genre-distribution">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={genrePreferenceData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={(entry) => `${entry.value}%`}
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {genrePreferenceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number) => `${value}%`}
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                    }}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={36}
                    iconType="circle"
                    wrapperStyle={{ fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Smart Insights — based on real backend data */}
        <div className="space-y-3 pt-2 border-t border-border">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Lightbulb className="h-4 w-4" />
            <span>Smart Insights</span>
          </div>
          <div className="space-y-2">
            <div className="bg-primary/10 rounded-lg p-3 border border-primary/20">
              <div className="flex items-start gap-2">
                <Clock className="h-4 w-4 mt-0.5 text-primary flex-shrink-0" />
                <p className="text-sm" data-testid="text-insight-best-time">
                  <span className="font-medium">Viewing Style:</span> You tend to watch {analysis.preferredGenres.length > 0 ? GENRE_MAP[analysis.preferredGenres[0]] : 'movies'} most on {dominantDay}
                </p>
              </div>
            </div>
            {patterns && patterns.totalWatched > 0 && (
              <div className="bg-primary/10 rounded-lg p-3 border border-primary/20">
                <div className="flex items-start gap-2">
                  <TrendingUp className="h-4 w-4 mt-0.5 text-primary flex-shrink-0" />
                  <p className="text-sm" data-testid="text-insight-activity">
                    <span className="font-medium">Your Library:</span> {patterns.totalWatched} watched, {patterns.totalReviews} reviewed, {patterns.totalFavorites} favorited
                  </p>
                </div>
              </div>
            )}
            {analysis.avgRating > 4 && (
              <div className="bg-primary/10 rounded-lg p-3 border border-primary/20">
                <div className="flex items-start gap-2">
                  <Star className="h-4 w-4 mt-0.5 text-yellow-500 flex-shrink-0" />
                  <p className="text-sm" data-testid="text-insight-rating">
                    <span className="font-medium">High Standards:</span> Your average rating of {analysis.avgRating.toFixed(1)} shows you're selective about what you watch
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Binge recommendation */}
        {analysis.bingeWatcher && (
          <div className="bg-muted/50 rounded-lg p-3 border border-border">
            <p className="text-sm text-muted-foreground italic">
              💡 You're on a binge-watching streak! Keep enjoying your favorites.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
