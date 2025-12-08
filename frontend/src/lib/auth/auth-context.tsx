import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import type { User } from "oidc-client-ts";
import { getUserManager } from "./oidc-config";
import { parseUser } from "./parse-user";
import { parseLocalUser } from "./parse-local-user";
import {
  clearLocalTokens,
  getLocalTokens,
  isLocalTokenExpired,
  storeLocalTokens,
  updateAccessToken,
} from "./local-storage";
import {
  loginLocal as loginLocalApi,
  logout as logoutLocalApi,
  refreshAccessToken,
  register as registerApi,
} from "@/lib/api/auth";
import type {
  AuthContextType,
  AuthProvider as AuthProviderType,
  AuthUser,
  RegisterData,
} from "@/types/auth";

export const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authProvider, setAuthProvider] = useState<AuthProviderType | null>(null);

  const userManager = getUserManager();

  // OIDC event handlers
  const handleUserLoaded = useCallback((oidcUser: User) => {
    setUser(parseUser(oidcUser));
    setAuthProvider("oidc");
    setIsLoading(false);
  }, []);

  const handleUserUnloaded = useCallback(() => {
    setUser(null);
    setAuthProvider(null);
    setIsLoading(false);
  }, []);

  // Initialize: Check for both OIDC and local tokens
  useEffect(() => {
    // Register OIDC event handlers
    userManager.events.addUserLoaded(handleUserLoaded);
    userManager.events.addUserUnloaded(handleUserUnloaded);
    userManager.events.addSilentRenewError(() => {
      console.error("Silent renew error");
      if (authProvider === "oidc") {
        setUser(null);
        setAuthProvider(null);
      }
    });
    userManager.events.addAccessTokenExpired(() => {
      console.warn("Access token expired");
      if (authProvider === "oidc") {
        setUser(null);
        setAuthProvider(null);
      }
    });

    // Check for existing authentication
    const initAuth = async () => {
      // 1. Check for OIDC user first
      try {
        const oidcUser = await userManager.getUser();
        if (oidcUser && !oidcUser.expired) {
          setUser(parseUser(oidcUser));
          setAuthProvider("oidc");
          setIsLoading(false);
          return;
        }
      } catch (error) {
        console.error("Failed to get OIDC user:", error);
      }

      // 2. Check for local tokens
      const tokens = getLocalTokens();
      if (tokens) {
        if (!isLocalTokenExpired(tokens)) {
          // Token is valid, parse and set user
          const parsedUser = parseLocalUser(tokens.accessToken);
          if (parsedUser) {
            setUser(parsedUser);
            setAuthProvider("local");
            setIsLoading(false);
            return;
          }
        } else if (tokens.refreshToken) {
          // Try to refresh the token
          try {
            const response = await refreshAccessToken(tokens.refreshToken);
            updateAccessToken(response.access_token, response.expires_in);
            const parsedUser = parseLocalUser(response.access_token);
            if (parsedUser) {
              setUser(parsedUser);
              setAuthProvider("local");
              setIsLoading(false);
              return;
            }
          } catch (error) {
            console.error("Failed to refresh token:", error);
            clearLocalTokens();
          }
        }
      }

      // No valid auth found
      setIsLoading(false);
    };

    initAuth();

    return () => {
      userManager.events.removeUserLoaded(handleUserLoaded);
      userManager.events.removeUserUnloaded(handleUserUnloaded);
    };
  }, [userManager, handleUserLoaded, handleUserUnloaded, authProvider]);

  // OIDC Login (redirect to Keycloak)
  const login = useCallback(async () => {
    try {
      await userManager.signinRedirect();
    } catch (error) {
      console.error("OIDC login failed:", error);
      throw error;
    }
  }, [userManager]);

  // Local Login (username/password)
  const loginLocal = useCallback(async (email: string, password: string) => {
    try {
      const response = await loginLocalApi(email, password);
      storeLocalTokens(response);

      const parsedUser = parseLocalUser(response.access_token);
      if (parsedUser) {
        setUser(parsedUser);
        setAuthProvider("local");
      } else {
        throw new Error("Failed to parse user from token");
      }
    } catch (error) {
      console.error("Local login failed:", error);
      throw error;
    }
  }, []);

  // Register new user
  const register = useCallback(async (data: RegisterData) => {
    try {
      await registerApi(data);
      // Registration successful - user needs to verify email
    } catch (error) {
      console.error("Registration failed:", error);
      throw error;
    }
  }, []);

  // Unified logout
  const logout = useCallback(async () => {
    try {
      if (authProvider === "oidc") {
        await userManager.signoutRedirect();
      } else if (authProvider === "local") {
        const tokens = getLocalTokens();
        if (tokens) {
          try {
            await logoutLocalApi(tokens.refreshToken, tokens.accessToken);
          } catch (e) {
            // Ignore logout API errors - we'll clear tokens anyway
            console.error("Logout API error:", e);
          }
        }
        clearLocalTokens();
        setUser(null);
        setAuthProvider(null);
      }
    } catch (error) {
      console.error("Logout failed:", error);
      // Clear local state even if API call fails
      clearLocalTokens();
      setUser(null);
      setAuthProvider(null);
      throw error;
    }
  }, [userManager, authProvider]);

  // Get access token (works for both OIDC and local)
  const getAccessToken = useCallback(async (): Promise<string | null> => {
    try {
      if (authProvider === "oidc") {
        const oidcUser = await userManager.getUser();
        return oidcUser?.access_token ?? null;
      }

      if (authProvider === "local") {
        let tokens = getLocalTokens();

        if (!tokens) return null;

        // Check if token needs refresh
        if (isLocalTokenExpired(tokens)) {
          if (tokens.refreshToken) {
            try {
              const response = await refreshAccessToken(tokens.refreshToken);
              updateAccessToken(response.access_token, response.expires_in);
              return response.access_token;
            } catch (error) {
              console.error("Failed to refresh token:", error);
              // Token refresh failed, clear auth state
              clearLocalTokens();
              setUser(null);
              setAuthProvider(null);
              return null;
            }
          }
          return null;
        }

        return tokens.accessToken;
      }

      return null;
    } catch (error) {
      console.error("Failed to get access token:", error);
      return null;
    }
  }, [userManager, authProvider]);

  const value: AuthContextType = {
    isAuthenticated: !!user,
    isLoading,
    user,
    authProvider,
    login,
    logout,
    getAccessToken,
    loginLocal,
    register,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
