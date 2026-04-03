import { useAuthContext } from "@/contexts/AuthContext";
import { setTokens, clearTokens, getAuthHeaders } from "@/lib/queryClient";

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

export function useAuth(): AuthState & { refetchUser: () => Promise<void> } {
  const { user, isLoading, isAuthenticated, refetchUser } = useAuthContext();
  return { user, isLoading, isAuthenticated, refetchUser };
}

export async function register(email: string, password: string, firstName: string, lastName: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, firstName, lastName }),
    });

    const data = await response.json();

    if (response.ok) {
      if (data.tokens) {
        setTokens(data.tokens.access, data.tokens.refresh);
      }
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
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      if (data.tokens) {
        setTokens(data.tokens.access, data.tokens.refresh);
      }
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
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        ...getAuthHeaders(),
      },
    });
  } catch (error) {
    console.error('Logout error:', error);
  }

  clearTokens();
  window.dispatchEvent(new CustomEvent('auth-change'));
  window.history.pushState({}, '', '/login');
  window.dispatchEvent(new PopStateEvent('popstate'));
}

export async function deleteAccount(confirmation: string): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch('/api/auth/delete-account', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ confirmation }),
    });

    const data = await response.json();

    if (response.ok) {
      clearTokens();
      window.dispatchEvent(new CustomEvent('auth-change'));
      return { success: true };
    } else {
      return { success: false, error: data.error || 'Failed to delete account' };
    }
  } catch (error) {
    return { success: false, error: 'Network error' };
  }
}

export { getAuthToken } from "@/lib/queryClient";
