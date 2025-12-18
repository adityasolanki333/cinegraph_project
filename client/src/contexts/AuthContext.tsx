import { createContext, useContext, useState, useEffect, ReactNode } from "react";

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

    pendingFetch = (async () => {
      try {
        // Check if user explicitly logged out - don't auto-enable demo mode
        const hasLoggedOut = sessionStorage.getItem('explicit-logout') === 'true';
        
        // Check for demo mode first
        const isDemoMode = localStorage.getItem('demo-mode') === 'true';
        const demoUserStr = localStorage.getItem('demo-user');
        
        if (isDemoMode && demoUserStr) {
          try {
            const demoUser = JSON.parse(demoUserStr);
            setAuthState({
              user: demoUser,
              isLoading: false,
              isAuthenticated: true,
            });
            return;
          } catch (parseError) {
            localStorage.removeItem('demo-mode');
            localStorage.removeItem('demo-user');
          }
        }

        // If not in demo mode, check server session
        const headers: Record<string, string> = {};
        const response = await fetch('/api/auth/me', {
          credentials: 'include',
          headers,
        });

        if (response.ok || response.status === 304) {
          const data = await response.json();
          // Clear the logout flag since user is now authenticated
          sessionStorage.removeItem('explicit-logout');
          setAuthState({
            user: data.user,
            isLoading: false,
            isAuthenticated: true,
          });
        } else {
          // Only auto-enable demo mode if user hasn't explicitly logged out
          if (!hasLoggedOut) {
            const demoUser = {
              id: 'demo_user',
              email: 'demo@cinesuggest.com',
              firstName: 'Demo',
              lastName: 'User',
            };
            localStorage.setItem('demo-mode', 'true');
            localStorage.setItem('demo-user', JSON.stringify(demoUser));
            setAuthState({
              user: demoUser,
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
