import { describe, it, expect, vi, beforeEach } from "vitest";

describe("getCsrfToken", () => {
  beforeEach(() => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      configurable: true,
      value: "",
    });
  });

  it("extracts csrftoken from cookies", async () => {
    document.cookie = "csrftoken=abc123; othercookie=xyz";
    const { getCsrfToken } = await import("@/lib/queryClient");
    expect(getCsrfToken()).toBe("abc123");
  });

  it("returns empty string when no csrftoken present", async () => {
    document.cookie = "othercookie=xyz";
    const { getCsrfToken } = await import("@/lib/queryClient");
    expect(getCsrfToken()).toBe("");
  });

  it("handles url-encoded csrftoken value", async () => {
    document.cookie = "csrftoken=abc%20def";
    const { getCsrfToken } = await import("@/lib/queryClient");
    expect(getCsrfToken()).toBe("abc def");
  });
});

describe("apiRequest", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(document, "cookie", {
      writable: true,
      configurable: true,
      value: "csrftoken=testtoken",
    });
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
    expect(options?.headers).toHaveProperty("X-CSRFToken", "testtoken");
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
