import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

interface ChildrenProps {
  children?: ReactNode;
}

interface LinkProps extends ChildrenProps {
  href?: string;
  to?: string;
}

interface RouteProps {
  component?: React.ComponentType;
}

vi.mock("wouter", () => ({
  useLocation: () => ["/", vi.fn()],
  useRoute: () => [false, {}],
  useParams: () => ({}),
  Link: ({ children, ...props }: LinkProps) => <a {...props}>{children}</a>,
  Switch: ({ children }: ChildrenProps) => <>{children}</>,
  Route: ({ component: Component }: RouteProps) => Component ? <Component /> : null,
}));

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: ChildrenProps) => <>{children}</>,
  useAuthContext: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    refetchUser: vi.fn(),
  }),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    refetchUser: vi.fn(),
  }),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  getAuthToken: () => null,
}));

vi.mock("@/hooks/useWatchlist", () => ({
  useWatchlist: () => ({
    watchlist: [],
    isLoading: false,
    addToWatchlist: vi.fn(),
    removeFromWatchlist: vi.fn(),
    isInWatchlist: () => false,
  }),
}));

vi.mock("@/hooks/useWebSocket", () => ({
  useWebSocket: () => ({
    isConnected: false,
    sendMessage: vi.fn(),
    lastMessage: null,
  }),
}));

vi.mock("@/hooks/usePageMeta", () => ({
  usePageMeta: vi.fn(),
}));

vi.mock("@/lib/tmdb", () => ({
  tmdbService: {
    getTrending: vi.fn().mockResolvedValue({ results: [] }),
    getPopular: vi.fn().mockResolvedValue({ results: [] }),
  },
}));

vi.mock("@/components/media-details", () => ({
  MediaDetails: ({ config }: { config: { title: string } }) => (
    <div data-testid="media-details">{config.title}</div>
  ),
}));

vi.mock("@/components/movie-details-skeleton", () => ({
  default: () => <div data-testid="movie-details-skeleton">Loading...</div>,
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: ChildrenProps) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("Login page", () => {
  it("renders without crashing", async () => {
    const Login = (await import("@/pages/login")).default;
    const { container } = render(<Login />, { wrapper: createWrapper() });
    expect(container).toBeTruthy();
  });

  it("renders sign-in form elements", async () => {
    const Login = (await import("@/pages/login")).default;
    render(<Login />, { wrapper: createWrapper() });
    const emailField = screen.queryByTestId("input-email") ?? screen.queryByLabelText(/email/i);
    expect(emailField).toBeTruthy();
  });
});

describe("Home page", () => {
  it("renders without crashing", async () => {
    const Home = (await import("@/pages/home")).default;
    const { container } = render(<Home />, { wrapper: createWrapper() });
    expect(container).toBeTruthy();
  });
});

describe("MovieDetails page", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("renders without crashing when movie ID is provided", async () => {
    const wouterMock = await import("wouter");
    vi.spyOn(wouterMock, "useParams").mockReturnValue({ id: "27205" });

    const MovieDetails = (await import("@/pages/movie-details")).default;
    const { container } = render(<MovieDetails />, { wrapper: createWrapper() });
    expect(container).toBeTruthy();
  });
});
