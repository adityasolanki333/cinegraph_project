import { useAuthContext } from "@/contexts/AuthContext";

interface User {
  id: string;
  email?: string;
  firstName?: string;
  lastName?: string;
  bio?: string;
  profileImageUrl?: string;
  createdAt?: Date;
  updatedAt?: Date;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

function getCsrfToken(): string | null {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [cookieName, cookieValue] = cookie.trim().split('=');
    if (cookieName === name) {
      return cookieValue;
    }
  }
  return null;
}

async function ensureCsrfToken(): Promise<string | null> {
  let token = getCsrfToken();
  if (!token) {
    await fetch('/api/auth/csrf', { credentials: 'include' });
    token = getCsrfToken();
  }
  return token;
}

export function useAuth(): AuthState & { refetchUser: () => Promise<void> } {
  const { user, isLoading, isAuthenticated, refetchUser } = useAuthContext();
  return { user, isLoading, isAuthenticated, refetchUser };
}

export async function register(email: string, password: string, firstName: string, lastName: string): Promise<{ success: boolean; error?: string }> {
  try {
    const csrfToken = await ensureCsrfToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ email, password, firstName, lastName }),
    });

    const data = await response.json();

    if (response.ok) {
      window.dispatchEvent(new CustomEvent('auth-change'));
      return { success: true };
    } else {
      return { success: false, error: data.error || 'Registration failed' };
    }
  } catch (error) {
    return { success: false, error: 'Network error' };
  }
}

export async function login(email: string, password: string): Promise<{ success: boolean; error?: string }> {
  try {
    const csrfToken = await ensureCsrfToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      window.dispatchEvent(new CustomEvent('auth-change'));
      return { success: true };
    } else {
      return { success: false, error: data.error || 'Login failed' };
    }
  } catch (error) {
    return { success: false, error: 'Network error' };
  }
}



export async function logout() {
  try {
    const csrfToken = await ensureCsrfToken();

    const headers: Record<string, string> = {};
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }

    await fetch('/api/auth/logout', {
      method: 'POST',
      headers,
      credentials: 'include',
    });
  } catch (error) {
    console.error('Logout error:', error);
  }

  window.dispatchEvent(new CustomEvent('auth-change'));
  window.history.pushState({}, '', '/login');
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export function getAuthToken(): string | null {
  return null;
}
