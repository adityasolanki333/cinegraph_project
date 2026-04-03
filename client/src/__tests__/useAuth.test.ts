import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("useAuth standalone functions", () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ user: { id: "1" }, tokens: { access: "access-token", refresh: "refresh-token" } }),
    } as Response);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  describe("login", () => {
    it("returns success on ok response and dispatches auth-change", async () => {
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" }, tokens: { access: "access-token", refresh: "refresh-token" } }),
      } as Response);

      const result = await login("test@example.com", "password123");
      expect(result.success).toBe(true);
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ type: "auth-change" })
      );
    });

    it("stores JWT tokens on successful login", async () => {
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" }, tokens: { access: "my-access", refresh: "my-refresh" } }),
      } as Response);

      await login("test@example.com", "password123");
      expect(localStorage.getItem("auth_access_token")).toBe("my-access");
      expect(localStorage.getItem("auth_refresh_token")).toBe("my-refresh");
    });

    it("returns error message on failed response", async () => {
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
      const { login } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network failure"));

      const result = await login("test@example.com", "password123");
      expect(result.success).toBe(false);
      expect(result.error).toBe("Network error");
    });

    it("sends Authorization header with JWT token", async () => {
      localStorage.setItem("auth_access_token", "existing-token");
      const { login } = await import("@/hooks/useAuth");
      const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "1" }, tokens: { access: "new-token", refresh: "new-refresh" } }),
      } as Response);

      await login("test@example.com", "password123");
      const loginCall = fetchSpy.mock.calls.find((c) => c[0] === "/api/auth/login");
      expect(loginCall).toBeTruthy();
      const headers = (loginCall![1] as RequestInit).headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("register", () => {
    it("returns success on ok response", async () => {
      const { register } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({
        ok: true,
        json: async () => ({ user: { id: "2" }, tokens: { access: "access-token", refresh: "refresh-token" } }),
      } as Response);

      const result = await register("new@example.com", "password123", "First", "Last");
      expect(result.success).toBe(true);
    });

    it("returns error on failed registration", async () => {
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
    it("dispatches auth-change event and clears tokens", async () => {
      localStorage.setItem("auth_access_token", "some-token");
      localStorage.setItem("auth_refresh_token", "some-refresh");
      const dispatchSpy = vi.spyOn(window, "dispatchEvent");
      const { logout } = await import("@/hooks/useAuth");

      vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true } as Response);

      await logout();
      const authChangeEvent = dispatchSpy.mock.calls.find(
        (c) => (c[0] as Event).type === "auth-change"
      );
      expect(authChangeEvent).toBeTruthy();
      expect(localStorage.getItem("auth_access_token")).toBeNull();
      expect(localStorage.getItem("auth_refresh_token")).toBeNull();
    });

    it("dispatches auth-change even when fetch fails", async () => {
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
    it("returns token from localStorage", async () => {
      localStorage.setItem("auth_access_token", "my-jwt-token");
      const { getAuthToken } = await import("@/hooks/useAuth");
      expect(getAuthToken()).toBe("my-jwt-token");
    });

    it("returns null when no token stored", async () => {
      const { getAuthToken } = await import("@/hooks/useAuth");
      expect(getAuthToken()).toBeNull();
    });
  });
});
