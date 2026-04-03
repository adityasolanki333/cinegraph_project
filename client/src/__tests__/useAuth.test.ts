import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("useAuth standalone functions", () => {
  let originalCookie: PropertyDescriptor | undefined;

  beforeEach(() => {
    vi.resetModules();
    originalCookie = Object.getOwnPropertyDescriptor(document, "cookie");
    Object.defineProperty(document, "cookie", {
      writable: true,
      configurable: true,
      value: "",
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ user: { id: "1" } }),
    } as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    if (originalCookie) {
      Object.defineProperty(document, "cookie", originalCookie);
    }
  });

  describe("login", () => {
    it("returns success on ok response and dispatches auth-change", async () => {
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      document.cookie = "csrftoken=abc123";
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" } }),
      } as Response);

      const result = await login("test@example.com", "password123");
      expect(result.success).toBe(true);
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ type: "auth-change" })
      );
    });

    it("returns error message on failed response", async () => {
      document.cookie = "csrftoken=abc123";
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Invalid credentials" }),
      } as Response);

      const result = await login("test@example.com", "wrong");
      expect(result.success).toBe(false);
      expect(result.error).toBe("Invalid credentials");
    });

    it("returns network error on fetch failure", async () => {
      document.cookie = "csrftoken=abc123";
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network failure"));

      const result = await login("test@example.com", "password123");
      expect(result.success).toBe(false);
      expect(result.error).toBe("Network error");
    });

    it("fetches CSRF token when cookie is missing", async () => {
      const { login } = await import("@/hooks/useAuth");
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" } }),
      } as Response);

      await login("test@example.com", "password123");
      expect(fetchSpy).toHaveBeenCalledWith(
        "/api/auth/csrf",
        expect.objectContaining({ credentials: "include" })
      );
    });

    it("includes X-CSRFToken header when token is available", async () => {
      document.cookie = "csrftoken=mytoken";
      const { login } = await import("@/hooks/useAuth");
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" } }),
      } as Response);

      await login("test@example.com", "password123");
      const loginCall = fetchSpy.mock.calls.find((c) => c[0] === "/api/auth/login");
      expect(loginCall).toBeTruthy();
      const headers = (loginCall![1] as RequestInit).headers as Record<string, string>;
      expect(headers["X-CSRFToken"]).toBe("mytoken");
    });
  });

  describe("register", () => {
    it("returns success on ok response", async () => {
      document.cookie = "csrftoken=abc123";
      const { register } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "2" } }),
      } as Response);

      const result = await register("new@example.com", "password123", "First", "Last");
      expect(result.success).toBe(true);
    });

    it("returns error on failed registration", async () => {
      document.cookie = "csrftoken=abc123";
      const { register } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: false,
        json: async () => ({ error: "Email already exists" }),
      } as Response);

      const result = await register("existing@example.com", "password123", "First", "Last");
      expect(result.success).toBe(false);
      expect(result.error).toBe("Email already exists");
    });
  });

  describe("logout", () => {
    it("dispatches auth-change event", async () => {
      document.cookie = "csrftoken=abc123";
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      const { logout } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true } as Response);

      await logout();
      const authChangeEvent = dispatchSpy.mock.calls.find(
        (c) => (c[0] as Event).type === "auth-change"
      );
      expect(authChangeEvent).toBeTruthy();
    });

    it("dispatches auth-change even when fetch fails", async () => {
      document.cookie = "csrftoken=abc123";
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      const { logout } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network failure"));

      await logout();
      const authChangeEvent = dispatchSpy.mock.calls.find(
        (c) => (c[0] as Event).type === "auth-change"
      );
      expect(authChangeEvent).toBeTruthy();
    });
  });

  describe("getAuthToken", () => {
    it("returns null", async () => {
      const { getAuthToken } = await import("@/hooks/useAuth");
      expect(getAuthToken()).toBeNull();
    });
  });
});
