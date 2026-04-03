import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { getAuthToken, getAuthHeaders, clearTokens, getRefreshToken, setTokens } from "@/lib/queryClient";

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

interface AuthContextType extends AuthState {
  refetchUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

let pendingFetch: Promise<void> | null = null;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const fetchUser = async (force = false) => {
    if (pendingFetch && !force) {
      return pendingFetch;
    }

    const token = getAuthToken();
    if (!token) {
      setAuthState({
        user: null,
        isLoading: false,
        isAuthenticated: false,
      });
      return;
    }

    pendingFetch = (async () => {
      try {
        let response = await fetch('/api/auth/me', {
          headers: {
            ...getAuthHeaders(),
          },
        });

        if (response.status === 401) {
          const refreshToken = getRefreshToken();
          if (refreshToken) {
            try {
              const refreshResponse = await fetch('/api/auth/token/refresh', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken }),
              });
              if (refreshResponse.ok) {
                const refreshData = await refreshResponse.json();
                setTokens(refreshData.access, refreshData.refresh || refreshToken);
                response = await fetch('/api/auth/me', {
                  headers: { ...getAuthHeaders() },
                });
              } else {
                clearTokens();
              }
            } catch {
              clearTokens();
            }
          }
        }

        if (response.ok || response.status === 304) {
          const data = await response.json();
          setAuthState({
            user: data.user,
            isLoading: false,
            isAuthenticated: true,
          });
        } else {
          setAuthState({
            user: null,
            isLoading: false,
            isAuthenticated: false,
          });
        }
      } catch (error) {
        setAuthState({
          user: null,
          isLoading: false,
          isAuthenticated: false,
        });
      } finally {
        pendingFetch = null;
      }
    })();

    return pendingFetch;
  };

  useEffect(() => {
    fetchUser();

    const handleAuthChange = () => {
      fetchUser(true);
    };

    window.addEventListener('auth-change', handleAuthChange);
    window.addEventListener('storage', handleAuthChange);

    return () => {
      window.removeEventListener('auth-change', handleAuthChange);
      window.removeEventListener('storage', handleAuthChange);
    };
  }, []);

  const contextValue: AuthContextType = {
    ...authState,
    refetchUser: fetchUser,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
