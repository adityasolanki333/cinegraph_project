import { useState, useMemo, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { MediaCard } from "@/components/media-card";
import { User, Heart, Star, Calendar, TrendingUp, Eye, Film, Tv, Settings, Edit3, BookOpen, Clock, ListChecks, Database, Key, Plus, Loader2, Users as UsersIcon, Trophy, List as ListIcon, UserPlus, UserMinus, Sparkles, Trash2, Bookmark } from "lucide-react";
import { useQuery, useMutation } from "@tanstack/react-query";
import type { Movie } from "@shared/schema";
import { useAuth } from "@/hooks/useAuth";
import { useLocation, Link, useRoute } from "wouter";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { CreateListDialog } from "@/components/create-list-dialog";
import { ListCard } from "@/components/list-card";
import { UserBadges } from "@/components/UserBadges";
import { UserImpactDashboard } from "@/components/user-impact-dashboard";
import { PatternInsights } from "@/components/pattern-insights";
import { getLevelBadge, getLevelProgress } from "@shared/helpers";

export default function Profile() {
  const [, setLocation] = useLocation();
  const { user, isAuthenticated, isLoading: authLoading, refetchUser } = useAuth();
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [bio, setBio] = useState("");
  const { toast } = useToast();

  const [match, params] = useRoute("/profile/:username");
  const username = params?.username;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      setLocation('/login');
    }
  }, [authLoading, isAuthenticated, setLocation]);

  const { data: profileUser } = useQuery({
    queryKey: ['/api/users/by-username', username],
    queryFn: async () => {
      if (!username) return user;
      const response = await fetch(`/api/users/by-username/${username}`);
      if (!response.ok) return null;
      return response.json();
    },
    enabled: !!username || !!user,
  });

  const displayUser = username ? profileUser : user;
  const profileUserId = displayUser?.id;
  const isOwnProfile = !username || displayUser?.id === user?.id;

  const getDisplayName = () => {
    if (displayUser?.firstName && displayUser?.lastName) {
      return `${displayUser.firstName} ${displayUser.lastName}`;
    }
    if (displayUser?.email) {
      const u = displayUser.email.split('@')[0];
      return u.replace(/[._]/g, ' ').split(' ')
        .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
    }
    return "User";
  };

  const displayName = getDisplayName();
  const initials = displayUser?.firstName && displayUser?.lastName
    ? `${displayUser.firstName[0]}${displayUser.lastName[0]}`
    : displayUser?.email?.[0]?.toUpperCase() || "U";

  // ── Ratings / Reviews ────────────────────────────────────────────────────
  const { data: userRatings, isLoading: ratingsLoading } = useQuery({
    queryKey: ['/api/users', profileUserId, 'reviews'],
    queryFn: async () => {
      if (!profileUserId) return [];
      const response = await fetch(`/api/users/${profileUserId}/reviews`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.ratings || data.reviews || (Array.isArray(data) ? data : []);
    },
    enabled: !!profileUserId,
    refetchInterval: 30000,
  });

  // ── Favorites (own profile only — 403 for others) ────────────────────────
  const { data: userFavorites, isLoading: favoritesLoading } = useQuery({
    queryKey: ['/api/users', profileUserId, 'favorites'],
    queryFn: async () => {
      if (!profileUserId) return [];
      const response = await fetch(`/api/users/${profileUserId}/favorites`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.items || (Array.isArray(data) ? data : []);
    },
    enabled: isOwnProfile && !!profileUserId,
    refetchInterval: 30000,
  });

  // ── Watched (own profile only — 403 for others) ──────────────────────────
  const { data: userWatched, isLoading: watchedLoading } = useQuery({
    queryKey: ['/api/users', profileUserId, 'watched'],
    queryFn: async () => {
      if (!profileUserId) return [];
      const response = await fetch(`/api/users/${profileUserId}/watched`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.items || (Array.isArray(data) ? data : []);
    },
    enabled: isOwnProfile && !!profileUserId,
    refetchInterval: 30000,
  });

  // ── Watchlist (own profile only — 403 for others) ────────────────────────
  const { data: userWatchlist, isLoading: watchlistLoading } = useQuery({
    queryKey: ['/api/users', profileUserId, 'watchlist'],
    queryFn: async () => {
      if (!profileUserId) return [];
      const response = await fetch(`/api/users/${profileUserId}/watchlist`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.items || (Array.isArray(data) ? data : []);
    },
    enabled: isOwnProfile && !!profileUserId,
    staleTime: 0,
    refetchOnMount: true,
    refetchInterval: 30000,
  });

  // ── Stats ────────────────────────────────────────────────────────────────
  const { data: userStats, isLoading: statsLoading } = useQuery<{
    experiencePoints: number;
    totalFollowers: number;
    totalFollowing: number;
    totalReviews: number;
    totalLists: number;
    totalAwardsGiven: number;
    totalAwardsReceived: number;
  }>({
    queryKey: ['/api/users', profileUserId, 'stats'],
    enabled: !!profileUserId,
    queryFn: async () => {
      if (!profileUserId) return null;
      const response = await fetch(`/api/users/${profileUserId}/stats`);
      if (!response.ok) return null;
      const data = await response.json();
      return data.stats || data; // backend wraps in { stats: {...} }
    },
    refetchInterval: 30000,
  });

  // ── User lists ───────────────────────────────────────────────────────────
  const { data: userLists, isLoading: listsLoading } = useQuery({
    queryKey: ['/api/community/users', profileUserId, 'lists'],
    queryFn: async () => {
      if (!profileUserId) return [];
      const response = await fetch(`/api/community/users/${profileUserId}/lists`);
      if (!response.ok) return [];
      const data = await response.json();
      return data.lists || (Array.isArray(data) ? data : []);
    },
    enabled: !!profileUserId,
  });

  // ── Follow status ────────────────────────────────────────────────────────
  const { data: followStatus } = useQuery({
    queryKey: ['/api/users/is-following', user?.id, profileUserId],
    queryFn: async () => {
      if (isOwnProfile || !user?.id || !profileUserId) return { isFollowing: false };
      const response = await fetch(`/api/users/${user.id}/is-following/${profileUserId}`);
      if (!response.ok) return { isFollowing: false };
      return response.json();
    },
    enabled: !isOwnProfile && !!user?.id && !!profileUserId,
  });

  // ── Follow / Unfollow mutation ───────────────────────────────────────────
  const followMutation = useMutation({
    mutationFn: async (action: 'follow' | 'unfollow') => {
      if (!user?.id || !profileUserId) throw new Error("User not found");
      if (action === 'follow') {
        const res = await apiRequest("POST", `/api/users/${user.id}/follow`, { targetUserId: profileUserId });
        return res.json();
      } else {
        const res = await apiRequest("DELETE", `/api/users/${user.id}/follow/${profileUserId}`);
        return res.json();
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users/is-following', user?.id, profileUserId] });
      queryClient.invalidateQueries({ queryKey: ['/api/users', profileUserId, 'stats'] });
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'stats'] });
      if (user?.id) {
        queryClient.invalidateQueries({ queryKey: [`/api/community/user-impact/${user.id}`] });
      }
      toast({
        title: followStatus?.isFollowing ? "Unfollowed" : "Following",
        description: followStatus?.isFollowing
          ? `You unfollowed ${displayName}.`
          : `You are now following ${displayName}.`,
      });
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to update follow status.", variant: "destructive" });
    },
  });

  // ── Viewing stats (computed) ─────────────────────────────────────────────
  const viewingStats = useMemo(() => {
    const ratings = userRatings || [];
    const favoriteItems = userFavorites || [];
    const watchedItems = userWatched || [];
    const watchlistItems = userWatchlist || [];
    const avgRating = ratings.length > 0
      ? ratings.reduce((sum: number, r: any) => sum + (r.rating || 0), 0) / ratings.length
      : 0;
    return {
      totalWatched: watchedItems.length,
      avgRating,
      watchlistCount: watchlistItems.length,
      favoritesCount: favoriteItems.length,
      reviewsCount: ratings.filter((r: any) => r.review).length,
    };
  }, [userRatings, userFavorites, userWatched, userWatchlist]);

  // ── Update profile ───────────────────────────────────────────────────────
  const updateProfileMutation = useMutation({
    mutationFn: async (data: { firstName: string; lastName: string; bio?: string }) => {
      if (!user?.id) throw new Error("User not found");
      const response = await apiRequest("PATCH", `/api/users/${user.id}`, data);
      return response.json();
    },
    onSuccess: async (updatedUser) => {
      await refetchUser();
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        localStorage.setItem('user', JSON.stringify({ ...JSON.parse(storedUser), ...updatedUser }));
      }
      window.dispatchEvent(new Event('storage'));
      await queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id] });
      setIsEditDialogOpen(false);
      toast({ title: "Profile updated", description: "Your profile has been updated successfully." });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to update profile",
        variant: "destructive",
      });
    },
  });

  const handleOpenEditDialog = () => {
    setFirstName(user?.firstName || "");
    setLastName(user?.lastName || "");
    setBio(user?.bio || "");
    setIsEditDialogOpen(true);
  };

  const handleUpdateProfile = (e: React.FormEvent) => {
    e.preventDefault();
    if (!firstName.trim() || !lastName.trim()) {
      toast({ title: "Error", description: "First name and last name are required", variant: "destructive" });
      return;
    }
    updateProfileMutation.mutate({ firstName, lastName, bio });
  };

  // ── Delete review ────────────────────────────────────────────────────────
  const deleteReviewMutation = useMutation({
    mutationFn: async (reviewId: number) => {
      if (!user?.id) throw new Error("User not found");
      const response = await fetch(`/api/users/${user.id}/reviews/${reviewId}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!response.ok) throw new Error('Failed to delete review');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'reviews'] });
      queryClient.invalidateQueries({ queryKey: ['/api/users', user?.id, 'stats'] });
      toast({ title: "Review deleted", description: "Your review has been deleted." });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to delete review",
        variant: "destructive",
      });
    },
  });

  const levelInfo = getLevelBadge(userStats?.experiencePoints || 0);
  const isLoading = authLoading || statsLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex flex-col lg:flex-row gap-6 lg:gap-8">
          <Card className="lg:w-1/3 w-full">
            <CardContent className="pt-6">
              <div className="flex flex-col items-center gap-3">
                <Skeleton className="h-32 w-32 rounded-full" />
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-4 w-56" />
                <Skeleton className="h-6 w-24" />
              </div>
            </CardContent>
          </Card>
          <div className="lg:w-2/3 grid grid-cols-2 md:grid-cols-3 gap-3">
            {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-24" />)}
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Profile Header */}
      <div className="flex flex-col lg:flex-row gap-6 lg:gap-8 mb-8">
        {/* User Info Card */}
        <Card className="lg:w-1/3 w-full">
          <CardContent className="pt-6">
            <div className="flex flex-col items-center text-center">
              <Avatar className="h-24 w-24 sm:h-32 sm:w-32 mb-4">
                <AvatarImage src={displayUser?.profileImageUrl || undefined} alt={displayName} />
                <AvatarFallback className="text-xl sm:text-2xl">{initials}</AvatarFallback>
              </Avatar>

              <h1 className="text-xl sm:text-2xl font-bold text-foreground mb-1" data-testid="text-user-name">
                {displayName}
              </h1>
              <p className="text-sm text-muted-foreground mb-2" data-testid="text-user-email">
                {displayUser?.email || ""}
              </p>

              {displayUser?.bio && (
                <p className="text-sm text-muted-foreground mb-3 max-w-md text-center" data-testid="text-user-bio">
                  {displayUser.bio}
                </p>
              )}

              <Badge className={`${levelInfo.color} text-white mb-3 shadow-lg`} data-testid="badge-user-level">
                <Trophy className="h-3 w-3 mr-1" />
                {levelInfo.name}
              </Badge>

              {/* XP Progress Bar */}
              <div className="w-full max-w-xs mb-3">
                <div className="flex justify-between text-xs text-muted-foreground mb-1">
                  <span>{userStats?.experiencePoints || 0} XP</span>
                  <span>{levelInfo.max === Infinity ? 'Max Level!' : `${levelInfo.max} XP`}</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full ${levelInfo.color} transition-all duration-500`}
                    style={{ width: `${getLevelProgress(userStats?.experiencePoints || 0)}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center text-sm text-muted-foreground mb-4">
                <Calendar className="h-4 w-4 mr-2" />
                <span>
                  Joined {displayUser?.createdAt
                    ? new Date(displayUser.createdAt).toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
                    : 'Recently'}
                </span>
              </div>

              {/* Followers / Following */}
              <div className="flex items-center gap-6 mb-6 text-sm">
                <div className="flex items-center gap-1">
                  <span className="font-semibold" data-testid="stat-followers">{userStats?.totalFollowers ?? 0}</span>
                  <span className="text-muted-foreground">Followers</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="font-semibold" data-testid="stat-following">{userStats?.totalFollowing ?? 0}</span>
                  <span className="text-muted-foreground">Following</span>
                </div>
              </div>

              {isOwnProfile ? (
                <div className="flex gap-2 w-full max-w-sm">
                  <Button size="sm" className="flex-1" data-testid="button-edit-profile" onClick={handleOpenEditDialog}>
                    <Edit3 className="h-4 w-4 mr-2" />
                    <span className="hidden sm:inline">Edit Profile</span>
                    <span className="sm:hidden">Edit</span>
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    data-testid="button-settings"
                    onClick={() => setLocation('/settings')}
                  >
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  className="w-full max-w-sm"
                  data-testid="button-follow"
                  onClick={() => followMutation.mutate(followStatus?.isFollowing ? 'unfollow' : 'follow')}
                  disabled={followMutation.isPending}
                  variant={followStatus?.isFollowing ? "outline" : "default"}
                >
                  {followMutation.isPending ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : followStatus?.isFollowing ? (
                    <UserMinus className="h-4 w-4 mr-2" />
                  ) : (
                    <UserPlus className="h-4 w-4 mr-2" />
                  )}
                  {followStatus?.isFollowing ? 'Unfollow' : 'Follow'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <div className="lg:w-2/3 w-full grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
          {isOwnProfile ? (
            <>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Bookmark className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-primary mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-watchlist">
                    {watchlistLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.watchlistCount}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Watchlist</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Eye className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-primary mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-watched">
                    {watchedLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.totalWatched}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Watched</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Heart className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-red-500 mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-favorites-count">
                    {favoritesLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.favoritesCount}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Favorites</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Film className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-accent mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-total-rated">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : (userRatings?.length || 0)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Rated</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Star className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-yellow-500 mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-avg-rating">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.avgRating.toFixed(1)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Avg Rating</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <BookOpen className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-accent mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-reviews">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.reviewsCount}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Reviews</div>
                </CardContent>
              </Card>
            </>
          ) : (
            <>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Film className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-accent mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-total-rated">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : (userRatings?.length || 0)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Rated</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Star className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-yellow-500 mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-avg-rating">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.avgRating.toFixed(1)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Avg Rating</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <BookOpen className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-accent mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-reviews">
                    {ratingsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : viewingStats.reviewsCount}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Reviews</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <ListIcon className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-primary mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-lists">
                    {statsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : (userStats?.totalLists ?? 0)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Lists</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <UsersIcon className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-primary mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-followers-grid">
                    {statsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : (userStats?.totalFollowers ?? 0)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Followers</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-3 sm:p-4 text-center">
                  <Trophy className="h-6 w-6 sm:h-8 sm:w-8 mx-auto text-amber-500 mb-2" />
                  <div className="text-xl sm:text-2xl font-bold" data-testid="stat-awards">
                    {statsLoading ? <Skeleton className="h-7 w-8 mx-auto" /> : (userStats?.totalAwardsReceived ?? 0)}
                  </div>
                  <div className="text-xs sm:text-sm text-muted-foreground">Awards</div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

      {/* Badges */}
      {profileUserId && (
        <div className="mb-8">
          <UserBadges userId={profileUserId} />
        </div>
      )}

      {/* Tabs */}
      <Tabs defaultValue="rated" className="w-full">
        <div className="overflow-x-auto scrollbar-none -mx-4 px-4 sm:mx-0 sm:px-0 mb-6">
          <TabsList className="inline-flex w-max gap-0.5" data-testid="tabs-profile">
            <TabsTrigger value="rated" data-testid="tab-rated-items">
              <Star className="h-4 w-4 mr-1.5" />
              Rated
            </TabsTrigger>
            {isOwnProfile && (
              <TabsTrigger value="watchlist" data-testid="tab-watchlist">
                <Bookmark className="h-4 w-4 mr-1.5" />
                Watchlist
              </TabsTrigger>
            )}
            {isOwnProfile && (
              <TabsTrigger value="favorites" data-testid="tab-favorites">
                <Heart className="h-4 w-4 mr-1.5" />
                Favorites
              </TabsTrigger>
            )}
            {isOwnProfile && (
              <TabsTrigger value="watched" data-testid="tab-watched">
                <Eye className="h-4 w-4 mr-1.5" />
                Watched
              </TabsTrigger>
            )}
            <TabsTrigger value="lists" data-testid="tab-my-lists">
              <ListIcon className="h-4 w-4 mr-1.5" />
              Lists
            </TabsTrigger>
            {isOwnProfile && (
              <TabsTrigger value="patterns" data-testid="tab-patterns">
                <TrendingUp className="h-4 w-4 mr-1.5" />
                <span className="hidden sm:inline">Patterns</span>
                <span className="sm:hidden">Stats</span>
              </TabsTrigger>
            )}
            {isOwnProfile && (
              <TabsTrigger value="impact" data-testid="tab-my-impact">
                <Sparkles className="h-4 w-4 mr-1.5" />
                <span className="hidden sm:inline">My Impact</span>
                <span className="sm:hidden">Impact</span>
              </TabsTrigger>
            )}
          </TabsList>
        </div>

        {/* Lists Tab */}
        <TabsContent value="lists">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <ListIcon className="h-5 w-5" />
                  {isOwnProfile ? 'My Lists' : `${displayUser?.firstName}'s Lists`}
                </CardTitle>
                {isOwnProfile && <CreateListDialog />}
              </div>
            </CardHeader>
            <CardContent>
              {listsLoading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[1,2,3].map(i => <Skeleton key={i} className="h-64" />)}
                </div>
              ) : userLists && Array.isArray(userLists) && userLists.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {userLists.map((list: any) => (
                    <ListCard key={list.id} list={list} showAuthor={false} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <ListIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground mb-4">
                    {isOwnProfile ? "You haven't created any lists yet" : "This user hasn't created any lists yet"}
                  </p>
                  {isOwnProfile && (
                    <CreateListDialog trigger={
                      <Button>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Your First List
                      </Button>
                    } />
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rated Items Tab */}
        <TabsContent value="rated">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Star className="h-5 w-5" />
                Rated Items ({userRatings?.length || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {ratingsLoading ? (
                <div className="space-y-2">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-16" />)}
                </div>
              ) : userRatings && userRatings.length > 0 ? (
                <div className="space-y-2">
                  {userRatings.map((item: any) => (
                    <Link
                      key={item.id}
                      href={item.mediaType === 'movie' ? `/movie/${item.tmdbId}` : `/tv/${item.tmdbId}`}
                      data-testid={`link-rated-item-${item.id}`}
                      className="block"
                    >
                      <div className="p-3 border rounded hover:bg-accent transition-colors cursor-pointer relative group" data-testid={`rated-item-${item.id}`}>
                        {isOwnProfile && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="absolute top-2 right-2 h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              if (window.confirm('Delete this review?')) {
                                deleteReviewMutation.mutate(item.id);
                              }
                            }}
                            disabled={deleteReviewMutation.isPending}
                            data-testid={`button-delete-review-${item.id}`}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        )}
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-sm font-medium flex-1 pr-8" data-testid={`rated-title-${item.id}`}>
                            {item.title || item.name}
                          </p>
                          <div className="flex items-center gap-0.5" data-testid={`rated-stars-${item.id}`}>
                            {[...Array(5)].map((_, i) => (
                              <Star key={i} className={`h-3.5 w-3.5 ${i < (item.rating || 0) ? 'fill-yellow-400 text-yellow-400' : 'text-muted-foreground'}`} />
                            ))}
                            <span className="text-sm ml-1 font-medium">{item.rating}/5</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs" data-testid={`rated-mediatype-${item.id}`}>
                            {item.mediaType === 'movie' ? <Film className="h-3 w-3 mr-1" /> : <Tv className="h-3 w-3 mr-1" />}
                            {item.mediaType === 'movie' ? 'Movie' : 'TV'}
                          </Badge>
                          {item.review && (
                            <span className="text-xs text-muted-foreground truncate" data-testid={`rated-review-${item.id}`}>
                              "{item.review}"
                            </span>
                          )}
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Star className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No rated items yet</p>
                  <Button variant="outline" className="mt-4" onClick={() => setLocation('/movies')}>
                    Browse movies to rate
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Watchlist Tab — own profile only */}
        {isOwnProfile && <TabsContent value="watchlist">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bookmark className="h-5 w-5" />
                Watchlist ({viewingStats.watchlistCount})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {watchlistLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="aspect-[2/3]" />)}
                </div>
              ) : userWatchlist && userWatchlist.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {userWatchlist.map((item: any) => (
                    <MediaCard
                      key={item.tmdbId || item.id}
                      item={{
                        id: item.tmdbId || item.id,
                        title: item.title || item.name,
                        vote_average: item.voteAverage || item.vote_average || 0,
                        poster_path: item.posterPath || item.poster_path,
                        type: item.mediaType || 'movie',
                      }}
                      mediaType={item.mediaType || 'movie'}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Bookmark className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Your watchlist is empty</p>
                  <Button variant="outline" className="mt-4" onClick={() => setLocation('/movies')}>
                    Browse movies to add
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>}

        {/* Favorites Tab — own profile only */}
        {isOwnProfile && <TabsContent value="favorites">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Heart className="h-5 w-5" />
                Favorites ({viewingStats.favoritesCount})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {favoritesLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="aspect-[2/3]" />)}
                </div>
              ) : userFavorites && userFavorites.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {userFavorites.map((item: any) => (
                    <MediaCard
                      key={item.tmdbId || item.id}
                      item={{
                        id: item.tmdbId || item.id,
                        title: item.title || item.name,
                        vote_average: item.voteAverage || item.vote_average || 0,
                        poster_path: item.posterPath || item.poster_path,
                        type: item.mediaType || 'movie',
                      }}
                      mediaType={item.mediaType || 'movie'}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Heart className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No favorites yet</p>
                  <Button variant="outline" className="mt-4" onClick={() => setLocation('/movies')}>
                    Browse movies to favorite
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>}

        {/* Watched Tab — own profile only */}
        {isOwnProfile && <TabsContent value="watched">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5" />
                Watched ({viewingStats.totalWatched})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {watchedLoading ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="aspect-[2/3]" />)}
                </div>
              ) : userWatched && userWatched.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                  {userWatched.map((item: any) => (
                    <MediaCard
                      key={item.tmdbId || item.id}
                      item={{
                        id: item.tmdbId || item.id,
                        title: item.title || item.name,
                        vote_average: item.voteAverage || item.vote_average || 0,
                        poster_path: item.posterPath || item.poster_path,
                        type: item.mediaType || 'movie',
                      }}
                      mediaType={item.mediaType || 'movie'}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Eye className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Nothing marked as watched yet</p>
                  <Button variant="outline" className="mt-4" onClick={() => setLocation('/movies')}>
                    Browse movies to watch
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>}

        {/* My Impact Tab */}
        {isOwnProfile && profileUserId && (
          <TabsContent value="impact" className="space-y-6" data-testid="tab-content-my-impact">
            <UserImpactDashboard userId={profileUserId} />
          </TabsContent>
        )}

        {/* Patterns Tab */}
        {isOwnProfile && (
          <TabsContent value="patterns" className="space-y-6" data-testid="tab-content-patterns">
            <PatternInsights />
          </TabsContent>
        )}
      </Tabs>

      {/* Edit Profile Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent data-testid="dialog-edit-profile">
          <DialogHeader>
            <DialogTitle>Edit Profile</DialogTitle>
            <DialogDescription>
              Update your profile information. Click save when you're done.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateProfile}>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="firstName">First Name</Label>
                <Input
                  id="firstName"
                  data-testid="input-first-name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Enter your first name"
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="lastName">Last Name</Label>
                <Input
                  id="lastName"
                  data-testid="input-last-name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Enter your last name"
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="bio">Bio</Label>
                <Textarea
                  id="bio"
                  data-testid="input-bio"
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  placeholder="Tell us about yourself (optional)"
                  maxLength={500}
                  rows={3}
                />
                <p className="text-xs text-muted-foreground">{bio.length}/500 characters</p>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsEditDialogOpen(false)} data-testid="button-cancel">
                Cancel
              </Button>
              <Button type="submit" disabled={updateProfileMutation.isPending} data-testid="button-save-profile">
                {updateProfileMutation.isPending ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Saving...</>
                ) : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
