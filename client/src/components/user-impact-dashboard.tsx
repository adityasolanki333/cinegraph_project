import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Star, 
  List, 
  Users, 
  Award, 
  MessageSquare, 
  Heart, 
  TrendingUp, 
  Trophy,
  Sparkles,
  Target
} from "lucide-react";
import type { UserImpactData } from "@shared/api-types";
import { getLevelBadge, getLevelProgress, calculateXPToNextLevel, LEVELS } from "@shared/helpers";

interface UserImpactDashboardProps {
  userId: string;
}

export function UserImpactDashboard({ userId }: UserImpactDashboardProps) {
  const { data: impactData, isLoading, error } = useQuery<UserImpactData>({
    queryKey: [`/api/community/user-impact/${userId}`],
    queryFn: async () => {
      const response = await fetch(`/api/community/user-impact/${userId}`);
      if (!response.ok) throw new Error('Failed to fetch impact data');
      const data = await response.json();
      return data.impact || data;
    },
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6" data-testid="impact-dashboard-loading">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error || !impactData) {
    return (
      <div className="text-center py-12" data-testid="impact-dashboard-error">
        <p className="text-muted-foreground">Failed to load impact data</p>
      </div>
    );
  }

  const { reviewStats, listStats, socialStats, engagementReceived, experiencePoints } = impactData;

  const levelInfo = getLevelBadge(experiencePoints);
  const progress = getLevelProgress(experiencePoints);
  const xpToNext = calculateXPToNextLevel(experiencePoints);

  const currentIdx = LEVELS.findIndex(l => l.name === levelInfo.name);
  const nextLevel = currentIdx < LEVELS.length - 1 ? LEVELS[currentIdx + 1] : null;

  return (
    <div className="space-y-6" data-testid="impact-dashboard">
      {/* Level / XP Header — matches profile header system */}
      <Card className={`border-0 ${levelInfo.color} text-white`} data-testid="rank-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <CardTitle className="text-2xl sm:text-3xl font-bold flex items-center gap-2" data-testid="rank-title">
                <Trophy className="h-7 w-7 sm:h-8 sm:w-8" />
                {levelInfo.name}
              </CardTitle>
              <CardDescription className="text-white/90 text-base sm:text-lg" data-testid="motivational-message">
                {levelInfo.name === "Legend"
                  ? "You're a legend! Keep inspiring the community!"
                  : levelInfo.name === "Expert"
                    ? "Amazing work! You're making a huge impact!"
                    : levelInfo.name === "Contributor"
                      ? "Great progress! Keep contributing to grow!"
                      : levelInfo.name === "Enthusiast"
                        ? "Nice momentum! Keep reviewing and engaging!"
                        : "Welcome! Start reviewing and listing to level up!"}
              </CardDescription>
            </div>
            <div className="text-right">
              <div className="text-3xl sm:text-4xl font-bold" data-testid="engagement-score">
                {experiencePoints}
              </div>
              <div className="text-sm text-white/80">XP</div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span data-testid="progress-label">
                {levelInfo.max === Infinity
                  ? "Max Level Achieved!"
                  : `Progress to ${nextLevel?.name || "next level"}`}
              </span>
              <span className="font-semibold" data-testid="progress-percentage">
                {Math.round(progress)}%
              </span>
            </div>
            <div className="h-3 bg-white/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-white/80 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
            {levelInfo.max !== Infinity && (
              <p className="text-xs text-white/70" data-testid="next-rank-score">
                {xpToNext} XP to {nextLevel?.name}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        <Card data-testid="card-review-stats">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Review Activity</CardTitle>
            <Star className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <div className="text-2xl font-bold" data-testid="total-reviews">
                  {reviewStats.totalReviews}
                </div>
                <p className="text-xs text-muted-foreground">Total Reviews</p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="font-semibold" data-testid="average-rating">
                    {reviewStats.averageRatingGiven > 0 ? reviewStats.averageRatingGiven.toFixed(1) : "0"}
                  </div>
                  <p className="text-xs text-muted-foreground">Avg Rating</p>
                </div>
                <div>
                  <div className="font-semibold capitalize" data-testid="most-active-genre">
                    {reviewStats.mostActiveGenre || "N/A"}
                  </div>
                  <p className="text-xs text-muted-foreground">Most Active</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="card-list-stats">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">List Creation</CardTitle>
            <List className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <div className="text-2xl font-bold" data-testid="total-lists">
                  {listStats.totalLists}
                </div>
                <p className="text-xs text-muted-foreground">Lists Created</p>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <div className="font-semibold" data-testid="total-list-followers">
                    {listStats.totalListFollowers}
                  </div>
                  <p className="text-xs text-muted-foreground">Followers</p>
                </div>
                <div>
                  <div className="font-semibold" data-testid="total-items-in-lists">
                    {listStats.totalItemsInLists}
                  </div>
                  <p className="text-xs text-muted-foreground">Items</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="card-social-stats">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Social Network</CardTitle>
            <Users className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <div className="text-2xl font-bold" data-testid="follower-count">
                  {socialStats.followerCount}
                </div>
                <p className="text-xs text-muted-foreground">Followers</p>
              </div>
              <div className="text-sm">
                <div className="font-semibold" data-testid="following-count">
                  {socialStats.followingCount}
                </div>
                <p className="text-xs text-muted-foreground">Following</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="card-awards-received">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Awards Earned</CardTitle>
            <Award className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="total-awards-received">
              {engagementReceived.totalAwardsReceived}
            </div>
            <p className="text-xs text-muted-foreground">
              Reviews recognized by the community
            </p>
          </CardContent>
        </Card>

        <Card data-testid="card-comments-received">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Comments Received</CardTitle>
            <MessageSquare className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="total-comments-received">
              {engagementReceived.totalCommentsReceived}
            </div>
            <p className="text-xs text-muted-foreground">
              Conversations sparked
            </p>
          </CardContent>
        </Card>

        <Card data-testid="card-review-likes">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Helpful Reviews</CardTitle>
            <Heart className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold" data-testid="total-review-likes">
              {engagementReceived.totalReviewLikes}
            </div>
            <p className="text-xs text-muted-foreground">
              People found your reviews helpful
            </p>
          </CardContent>
        </Card>
      </div>

      {/* How to Level Up */}
      {levelInfo.max !== Infinity && (
        <Card className="border-primary/50" data-testid="impact-summary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              How to Level Up
            </CardTitle>
            <CardDescription>
              Earn XP by reviewing, creating lists, following users, and engaging with the community.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-4">
              <div className="p-2 rounded-lg bg-green-500/10">
                <TrendingUp className="h-6 w-6 text-green-500" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold mb-1">
                  {xpToNext} XP to reach {nextLevel?.name}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {levelInfo.name === "Newbie" && "Write reviews (+10 XP), create lists (+15 XP), and follow other cinephiles (+5 XP) to level up!"}
                  {levelInfo.name === "Enthusiast" && "Keep reviewing and building lists to reach Contributor!"}
                  {levelInfo.name === "Contributor" && "Your contributions matter! Keep growing to reach Expert!"}
                  {levelInfo.name === "Expert" && "You're almost a Legend! Keep pushing to reach the top!"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
