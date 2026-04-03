import { useEffect, lazy, Suspense } from "react";
import { Switch, Route, useLocation } from "wouter";
import { queryClient, prefetchCommonData } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ErrorBoundary } from "@/components/error-boundary";
import { AuthProvider } from "@/contexts/AuthContext";
import { useWebSocket } from "@/hooks/useWebSocket";
import { Loader2 } from "lucide-react";
import Navbar from "@/components/layout/navbar";
import MobileBottomNav from "@/components/layout/mobile-bottom-nav";
import { OnboardingWizard } from "@/components/onboarding-wizard";

// Lazy load pages
const NotFound = lazy(() => import("@/pages/not-found"));
const Home = lazy(() => import("@/pages/home"));
const Movies = lazy(() => import("@/pages/movies"));
const TVShows = lazy(() => import("@/pages/tvshows"));
const Recommendations = lazy(() => import("@/pages/recommendations"));
const MyList = lazy(() => import("@/pages/my-list"));
const Profile = lazy(() => import("@/pages/profile"));
const Settings = lazy(() => import("@/pages/settings"));
const MovieDetails = lazy(() => import("@/pages/movie-details"));
const TVShowDetails = lazy(() => import("@/pages/tv-show-details"));
const Login = lazy(() => import("@/pages/login"));
const ForgotPassword = lazy(() => import("@/pages/forgot-password"));
const Community = lazy(() => import("@/pages/community"));
const ClubsList = lazy(() => import("@/pages/community/clubs-list"));
const ClubDetails = lazy(() => import("@/pages/community/club-details"));
const DiscussionThread = lazy(() => import("@/pages/community/discussion-thread"));
const CommunityLists = lazy(() => import("@/pages/community/community-lists"));
const ListDetail = lazy(() => import("@/pages/list-detail"));
const Notifications = lazy(() => import("@/pages/notifications"));

function ScrollToTop() {
  const [location] = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location]);

  return null;
}

function Router() {
  // Initialize WebSocket connection for real-time updates
  useWebSocket();
  
  useEffect(() => {
    prefetchCommonData();
  }, []);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-background pb-14 md:pb-0">
        <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg">
          Skip to main content
        </a>
        <ScrollToTop />
        <Navbar />
        <OnboardingWizard />
        <main id="main-content">
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[50vh]">
              <Loader2 className="h-8 w-8 animate-spin text-primary" aria-label="Loading page" />
            </div>
          }
        >
          <Switch>
            <Route path="/" component={Home} />
            <Route path="/movies" component={Movies} />
            <Route path="/tv-shows" component={TVShows} />
            <Route path="/recommendations" component={Recommendations} />
            <Route path="/my-list" component={MyList} />
            <Route path="/community" component={Community} />
            <Route path="/community/clubs" component={ClubsList} />
            <Route path="/community/clubs/:id" component={ClubDetails} />
            <Route path="/community/clubs/threads/:id" component={DiscussionThread} />
            <Route path="/community/lists" component={CommunityLists} />
            <Route path="/lists/:id" component={ListDetail} />
            <Route path="/notifications" component={Notifications} />
            <Route path="/profile/:userId" component={Profile} />
            <Route path="/profile" component={Profile} />
            <Route path="/settings" component={Settings} />
            <Route path="/movie/:id" component={MovieDetails} />
            <Route path="/tv/:id" component={TVShowDetails} />
            <Route path="/login" component={Login} />
            <Route path="/forgot-password" component={ForgotPassword} />
            <Route path="/reset-password" component={ForgotPassword} />
            <Route component={NotFound} />
          </Switch>
        </Suspense>
        </main>
        <MobileBottomNav />
      </div>
    </ErrorBoundary>
  );
}

function App() {
  // Initialize theme on app load
  useEffect(() => {
    const savedSettings = localStorage.getItem("userSettings");
    let theme = "system"; // default theme

    if (savedSettings) {
      try {
        const parsed = JSON.parse(savedSettings);
        theme = parsed.theme || "system";
      } catch (error) {
        console.error("Failed to parse saved settings:", error);
      }
    }

    const root = document.documentElement;

    // Remove all theme classes
    root.classList.remove("dark", "system");

    // Apply the selected theme class
    if (theme === "dark") {
      root.classList.add("dark");
    } else if (theme === "system") {
      root.classList.add("system");
    }
    // light theme has no class (uses default :root styles)
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
