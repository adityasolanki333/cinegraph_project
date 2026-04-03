import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Share } from "lucide-react";
import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { RecommendationComments } from "@/components/recommendation-comments";

export function UserRecommendationsSection({ forTmdbId, forMediaType, currentUserId, isAuthenticated }: {
  forTmdbId: number;
  forMediaType: string;
  currentUserId?: string;
  isAuthenticated: boolean;
}) {
  const [showForm, setShowForm] = useState(false);
  const [selectedMedia, setSelectedMedia] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [reason, setReason] = useState("");
  const { toast } = useToast();

  const { data: recommendations, isLoading: recommendationsLoading } = useQuery({
    queryKey: ['/api/users/recommendations/for', forTmdbId, forMediaType],
    queryFn: async () => {
      const url = currentUserId
        ? `/api/users/recommendations/for/${forTmdbId}/${forMediaType}?userId=${currentUserId}`
        : `/api/users/recommendations/for/${forTmdbId}/${forMediaType}`;
      const response = await fetch(url);
      if (!response.ok) return [];
      const data = await response.json();
      return Array.isArray(data) ? data : (data.recommendations || []);
    }
  });

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ['/api/tmdb/search', searchQuery],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return { results: [] };
      const response = await fetch(`/api/tmdb/search/multi?query=${encodeURIComponent(searchQuery)}`);
      if (!response.ok) return { results: [] };
      return response.json();
    },
    enabled: searchQuery.length >= 2
  });

  const submitRecommendationMutation = useMutation({
    mutationFn: async (data: any) => {
      if (!currentUserId) throw new Error("User not authenticated");
      return apiRequest('POST', `/api/users/${currentUserId}/recommendations`, {
        forTmdbId,
        forMediaType,
        recommendedTmdbId: data.recommendedTmdbId,
        recommendedMediaType: data.recommendedMediaType,
        recommendedTitle: data.recommendedTitle,
        recommendedPosterPath: data.recommendedPosterPath,
        reason: data.reason
      });
    },
    onSuccess: () => {
      toast({ title: "Recommendation submitted!", description: "Thanks for sharing your suggestion." });
      setShowForm(false);
      setSelectedMedia(null);
      setSearchQuery("");
      setReason("");
      queryClient.invalidateQueries({ queryKey: ['/api/users/recommendations/for', forTmdbId, forMediaType] });
    },
    onError: (error: any) => {
      const errorMessage = error.message || "Failed to submit recommendation";
      const isAlreadyRecommended = errorMessage.includes("already recommended");
      toast({
        title: isAlreadyRecommended ? "Already Recommended" : "Error",
        description: isAlreadyRecommended
          ? "You've already recommended this movie/show here"
          : errorMessage,
        variant: isAlreadyRecommended ? undefined : "destructive"
      });
    }
  });

  const deleteRecommendationMutation = useMutation({
    mutationFn: async (recommendationId: string) => {
      if (!currentUserId) throw new Error("User not authenticated");
      return apiRequest('DELETE', `/api/users/${currentUserId}/recommendations/${recommendationId}`);
    },
    onSuccess: () => {
      toast({ title: "Recommendation deleted" });
      queryClient.invalidateQueries({ queryKey: ['/api/users/recommendations/for', forTmdbId, forMediaType] });
    },
    onError: (error: any) => {
      const errorMessage = error.message || "Failed to delete recommendation";
      const cannotDelete = errorMessage.includes("Cannot delete") || errorMessage.includes("likes");
      toast({
        title: cannotDelete ? "Cannot Delete" : "Error",
        description: cannotDelete
          ? "This recommendation has likes from others and cannot be deleted"
          : errorMessage,
        variant: "destructive"
      });
    }
  });

  const voteMutation = useMutation({
    mutationFn: async ({ recommendationId, voteType }: { recommendationId: string; voteType: 'like' | 'dislike' }) => {
      if (!currentUserId) throw new Error("User not authenticated");
      return apiRequest('POST', `/api/users/${currentUserId}/recommendations/${recommendationId}/vote`, { voteType });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users/recommendations/for', forTmdbId, forMediaType] });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to vote",
        variant: "destructive"
      });
    }
  });

  const [showComments, setShowComments] = useState<Record<string, boolean>>({});

  const handleSubmitRecommendation = () => {
    if (!selectedMedia || !currentUserId) return;
    submitRecommendationMutation.mutate({
      recommendedTmdbId: selectedMedia.id,
      recommendedMediaType: selectedMedia.media_type || forMediaType,
      recommendedTitle: selectedMedia.title || selectedMedia.name,
      recommendedPosterPath: selectedMedia.poster_path,
      reason: reason.trim() || undefined
    });
  };

  const mediaLabel = forMediaType === 'movie' ? 'Movie' : 'Show';

  return (
    <div className="space-y-6">
      {isAuthenticated ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Share className="h-5 w-5" />
              Recommend a {mediaLabel}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!showForm ? (
              <Button onClick={() => setShowForm(true)} data-testid="button-add-recommendation">
                <Share className="h-4 w-4 mr-2" />
                Add Recommendation
              </Button>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">Search for a show or movie to recommend:</label>
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search for a show or movie..."
                    className="w-full px-3 py-2 border rounded-md bg-background text-foreground"
                    data-testid="input-search-recommendation"
                  />
                  {searchLoading && <p className="text-sm text-muted-foreground mt-2">Searching...</p>}
                  {searchResults?.results && searchResults.results.length > 0 && !selectedMedia && (
                    <div className="mt-2 max-h-48 overflow-y-auto border rounded-md">
                      {searchResults.results.slice(0, 5).map((item: any) => (
                        <div
                          key={item.id}
                          onClick={() => {
                            setSelectedMedia(item);
                            setSearchQuery(item.title || item.name);
                          }}
                          className="p-2 hover:bg-accent cursor-pointer flex items-center gap-3 select-none"
                          data-testid={`search-result-${item.id}`}
                        >
                          {item.poster_path && (
                            <img
                              src={`https://image.tmdb.org/t/p/w92${item.poster_path}`}
                              alt={item.title || item.name}
                              loading="lazy"
                              className="w-12 h-18 object-cover rounded"
                            />
                          )}
                          <div>
                            <p className="font-medium text-sm">{item.title || item.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {item.media_type === 'movie' ? 'Movie' : 'TV Show'} • {item.release_date || item.first_air_date}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {selectedMedia && (
                  <>
                    <div>
                      <label className="text-sm font-medium mb-2 block">Why do you recommend this? (optional)</label>
                      <textarea
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder={`Share why fans of this ${mediaLabel.toLowerCase()} would enjoy your recommendation...`}
                        className="w-full px-3 py-2 border rounded-md min-h-[80px] bg-background text-foreground"
                        data-testid="input-recommendation-reason"
                        maxLength={500}
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Help others discover great content by sharing what makes this recommendation special. {reason.length}/500 characters
                      </p>
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={handleSubmitRecommendation}
                        disabled={submitRecommendationMutation.isPending}
                        data-testid="button-submit-recommendation"
                      >
                        {submitRecommendationMutation.isPending ? "Submitting..." : "Submit Recommendation"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => {
                          setShowForm(false);
                          setSelectedMedia(null);
                          setSearchQuery("");
                          setReason("");
                        }}
                        data-testid="button-cancel-recommendation"
                      >
                        Cancel
                      </Button>
                    </div>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="py-8 text-center">
            <Share className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">Share Your Recommendations</h3>
            <p className="text-muted-foreground mb-4">Sign in to recommend {forMediaType === 'movie' ? 'movies' : 'shows'} to other fans</p>
            <Link href="/login">
              <Button>Sign In</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>User Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          {recommendationsLoading ? (
            <p className="text-center text-muted-foreground py-8">Loading recommendations...</p>
          ) : recommendations && recommendations.length > 0 ? (
            <div className="space-y-4">
              {recommendations.map((rec: any) => (
                <Card key={rec.id} className="hover:shadow-lg hover:scale-[1.01] transition-all duration-200 animate-in fade-in slide-in-from-bottom-2" data-testid={`recommendation-${rec.id}`}>
                  <CardContent className="p-4">
                    <div className="flex gap-4">
                      {rec.recommendedPosterPath && (
                        <Link href={`/${rec.recommendedMediaType}/${rec.recommendedTmdbId}`}>
                          <img
                            src={`https://image.tmdb.org/t/p/w185${rec.recommendedPosterPath}`}
                            alt={rec.recommendedTitle}
                            loading="lazy"
                            className="w-24 h-36 object-cover rounded cursor-pointer hover:opacity-80 hover:scale-105 transition-transform duration-200"
                          />
                        </Link>
                      )}
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <Link href={`/${rec.recommendedMediaType}/${rec.recommendedTmdbId}`}>
                              <h4 className="font-semibold hover:underline cursor-pointer flex items-center gap-2" data-testid={`recommendation-title-${rec.id}`}>
                                <span>✨</span>
                                {rec.recommendedTitle}
                              </h4>
                            </Link>
                            <p className="text-sm text-muted-foreground flex items-center gap-1">
                              <span>👤</span>
                              Recommended by {rec.userFirstName && rec.userLastName
                                ? `${rec.userFirstName} ${rec.userLastName}`
                                : rec.userEmail || 'Anonymous'}
                            </p>
                          </div>
                          {currentUserId === rec.userId && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteRecommendationMutation.mutate(rec.id)}
                              disabled={deleteRecommendationMutation.isPending || (rec.likeCount && rec.likeCount > 0)}
                              data-testid={`button-delete-recommendation-${rec.id}`}
                              title={rec.likeCount > 0 ? `Cannot delete - ${rec.likeCount} ${rec.likeCount === 1 ? 'person has' : 'people have'} liked this` : 'Delete recommendation'}
                            >
                              Delete
                            </Button>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-3">
                          <Badge variant="outline" className="flex items-center gap-1">
                            <span>{rec.recommendedMediaType === 'movie' ? '🎬' : '📺'}</span>
                            {rec.recommendedMediaType === 'movie' ? 'Movie' : 'TV Show'}
                          </Badge>
                          {rec.score !== undefined && (
                            <span className="text-sm font-medium flex items-center gap-1" data-testid={`recommendation-score-${rec.id}`}>
                              {rec.score > 0 ? '🔥' : rec.score < 0 ? '❄️' : '➖'}
                              Score: {rec.score > 0 ? '+' : ''}{rec.score}
                            </span>
                          )}
                        </div>

                        <div className="mt-3 pt-3 border-t">
                          <div className="flex items-center gap-4">
                            {isAuthenticated ? (
                              <>
                                <div className="flex items-center gap-1">
                                  <Button
                                    variant={rec.userVote === 'like' ? 'default' : 'ghost'}
                                    size="sm"
                                    onClick={() => voteMutation.mutate({ recommendationId: rec.id, voteType: 'like' })}
                                    disabled={voteMutation.isPending}
                                    data-testid={`button-like-${rec.id}`}
                                    className="hover:scale-110 transition-transform duration-200 active:scale-95"
                                  >
                                    <span className={`text-base mr-1 ${rec.userVote === 'like' ? 'animate-bounce' : ''}`}>👍</span>
                                    {rec.likeCount || 0}
                                  </Button>
                                  <Button
                                    variant={rec.userVote === 'dislike' ? 'default' : 'ghost'}
                                    size="sm"
                                    onClick={() => voteMutation.mutate({ recommendationId: rec.id, voteType: 'dislike' })}
                                    disabled={voteMutation.isPending}
                                    data-testid={`button-dislike-${rec.id}`}
                                    className="hover:scale-110 transition-transform duration-200 active:scale-95"
                                  >
                                    <span className={`text-base mr-1 ${rec.userVote === 'dislike' ? 'animate-bounce' : ''}`}>👎</span>
                                    {rec.dislikeCount || 0}
                                  </Button>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setShowComments(prev => ({ ...prev, [rec.id]: !prev[rec.id] }))}
                                  data-testid={`button-comments-${rec.id}`}
                                  className="hover:scale-110 transition-transform duration-200 active:scale-95"
                                >
                                  <span className={`text-base mr-1 ${showComments[rec.id] ? 'animate-pulse' : ''}`}>💬</span>
                                  {rec.commentCount || 0} {rec.commentCount === 1 ? 'comment' : 'comments'}
                                </Button>
                              </>
                            ) : (
                              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <span className="text-base">👍</span> {rec.likeCount || 0}
                                </span>
                                <span className="flex items-center gap-1">
                                  <span className="text-base">👎</span> {rec.dislikeCount || 0}
                                </span>
                                <span className="flex items-center gap-1">
                                  <span className="text-base">💬</span> {rec.commentCount || 0}
                                </span>
                              </div>
                            )}
                          </div>

                          {showComments[rec.id] && (
                            <RecommendationComments
                              recommendationId={rec.id}
                              currentUserId={currentUserId}
                              reason={rec.reason}
                            />
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 animate-in fade-in duration-500">
              <div className="text-6xl mb-4">💡</div>
              <p className="text-muted-foreground text-lg font-medium mb-2">No recommendations yet</p>
              <p className="text-muted-foreground text-sm">Be the first to suggest a {forMediaType === 'movie' ? 'movie' : 'show'}!</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
