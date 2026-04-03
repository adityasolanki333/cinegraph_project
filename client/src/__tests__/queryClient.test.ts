import { describe, it, expect, vi, beforeEach } from "vitest";

describe("getAuthToken", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns token from localStorage", async () => {
    localStorage.setItem("auth_access_token", "test-jwt-token");
    const { getAuthToken } = await import("@/lib/queryClient");
    expect(getAuthToken()).toBe("test-jwt-token");
  });

  it("returns null when no token present", async () => {
    const { getAuthToken } = await import("@/lib/queryClient");
    expect(getAuthToken()).toBeNull();
  });
});

describe("apiRequest", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    localStorage.setItem("auth_access_token", "testtoken");
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not found"),
    } as Response);

    const { apiRequest } = await import("@/lib/queryClient");
    await expect(apiRequest("GET", "/api/test")).rejects.toThrow("404: Not found");
  });

  it("sends JSON body for POST requests", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ success: true }),
    } as Response);

    const { apiRequest } = await import("@/lib/queryClient");
    await apiRequest("POST", "/api/test", { key: "value" });

    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toBe("/api/test");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBe(JSON.stringify({ key: "value" }));
    expect(options?.headers).toHaveProperty("Authorization", "Bearer testtoken");
  });

  it("returns Response object on success", async () => {
    const mockResponse = {
      ok: true,
      status: 200,
      json: () => Promise.resolve({ data: "test" }),
    } as Response;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(mockResponse);

    const { apiRequest } = await import("@/lib/queryClient");
    const result = await apiRequest("GET", "/api/test");
    expect(result).toBe(mockResponse);
  });
});
