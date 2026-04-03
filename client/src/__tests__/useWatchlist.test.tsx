import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

const mockUser = { id: "42", email: "test@example.com" };

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockUser,
    isLoading: false,
    isAuthenticated: true,
    refetchUser: vi.fn(),
  }),
}));

vi.mock("@/lib/queryClient", async () => {
  const { QueryClient } = await import("@tanstack/react-query");
  return {
    queryClient: new QueryClient(),
    apiRequest: vi.fn(),
  };
});

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("useWatchlist", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns empty watchlist initially", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    } as Response);

    const { useWatchlist } = await import("@/hooks/useWatchlist");
    const { result } = renderHook(() => useWatchlist(), {
      wrapper: createWrapper(),
    });

    expect(result.current.watchlist).toEqual([]);
  });

  it("isInWatchlist returns false for absent movie", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    } as Response);

    const { useWatchlist } = await import("@/hooks/useWatchlist");
    const { result } = renderHook(() => useWatchlist(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isInWatchlist("999")).toBe(false);
  });

  it("isInWatchlist returns true for present movie", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ tmdbId: 123, title: "Inception", posterPath: "/p.jpg", mediaType: "movie" }],
      }),
    } as Response);

    const { useWatchlist } = await import("@/hooks/useWatchlist");
    const { result } = renderHook(() => useWatchlist(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.watchlist.length).toBe(1);
    });
    expect(result.current.isInWatchlist("123")).toBe(true);
  });

  it("exposes addToWatchlist and removeFromWatchlist functions", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ items: [] }),
    } as Response);

    const { useWatchlist } = await import("@/hooks/useWatchlist");
    const { result } = renderHook(() => useWatchlist(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.addToWatchlist).toBe("function");
    expect(typeof result.current.removeFromWatchlist).toBe("function");
  });
});
