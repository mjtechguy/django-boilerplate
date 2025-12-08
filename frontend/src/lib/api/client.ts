import ky, { type KyInstance, type Options } from "ky";
import { getUserManager } from "@/lib/auth";
import {
  getLocalTokens,
  isLocalTokenExpired,
  clearLocalTokens,
  updateAccessToken,
} from "@/lib/auth/local-storage";
import { refreshAccessToken } from "@/lib/api/auth";

const API_URL = import.meta.env.VITE_API_URL || "";

// Flag to prevent infinite refresh loops
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

/**
 * Attempt to refresh the access token using the refresh token.
 * Returns the new access token if successful, null otherwise.
 */
async function tryRefreshToken(): Promise<string | null> {
  const tokens = getLocalTokens();
  if (!tokens?.refreshToken) {
    return null;
  }

  // If already refreshing, wait for the existing refresh to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const response = await refreshAccessToken(tokens.refreshToken);
      updateAccessToken(response.access_token, response.expires_in);
      return response.access_token;
    } catch (error) {
      console.error("Token refresh failed:", error);
      return null;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

async function getAuthorizationHeader(): Promise<string | undefined> {
  // 1. Check for local tokens first
  const localTokens = getLocalTokens();
  if (localTokens) {
    // If token is expired but we have a refresh token, try to refresh proactively
    if (isLocalTokenExpired(localTokens) && localTokens.refreshToken) {
      const newAccessToken = await tryRefreshToken();
      if (newAccessToken) {
        return `Bearer ${newAccessToken}`;
      }
      // Refresh failed, fall through to OIDC or return undefined
    } else if (!isLocalTokenExpired(localTokens)) {
      return `Bearer ${localTokens.accessToken}`;
    }
  }

  // 2. Fall back to OIDC tokens
  try {
    const userManager = getUserManager();
    const user = await userManager.getUser();
    if (user?.access_token) {
      return `Bearer ${user.access_token}`;
    }
  } catch (error) {
    console.error("Failed to get authorization header:", error);
  }
  return undefined;
}

export const api: KyInstance = ky.create({
  prefixUrl: `${API_URL}/api/v1`,
  timeout: 30000,
  retry: {
    limit: 2,
    methods: ["get", "head", "options"],
    statusCodes: [408, 429, 500, 502, 503, 504],
  },
  hooks: {
    beforeRequest: [
      async (request) => {
        const authHeader = await getAuthorizationHeader();
        if (authHeader) {
          request.headers.set("Authorization", authHeader);
        }
      },
    ],
    afterResponse: [
      async (request, options, response) => {
        if (response.status === 401) {
          // Check if we have a refresh token and haven't already tried refreshing
          const tokens = getLocalTokens();
          if (tokens?.refreshToken && !isRefreshing) {
            const newAccessToken = await tryRefreshToken();
            if (newAccessToken) {
              // Retry the request with the new token
              request.headers.set("Authorization", `Bearer ${newAccessToken}`);
              return ky(request, options);
            }
          }

          // Refresh failed or no refresh token - clear tokens and redirect
          clearLocalTokens();
          const currentPath = window.location.pathname;
          window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`;
        }
        return response;
      },
    ],
  },
});

// Typed API helpers
export async function apiGet<T>(url: string, options?: Options): Promise<T> {
  return api.get(url, options).json<T>();
}

export async function apiPost<T, D = unknown>(
  url: string,
  data?: D,
  options?: Options
): Promise<T> {
  return api
    .post(url, {
      ...options,
      json: data,
    })
    .json<T>();
}

export async function apiPut<T, D = unknown>(
  url: string,
  data?: D,
  options?: Options
): Promise<T> {
  return api
    .put(url, {
      ...options,
      json: data,
    })
    .json<T>();
}

export async function apiPatch<T, D = unknown>(
  url: string,
  data?: D,
  options?: Options
): Promise<T> {
  return api
    .patch(url, {
      ...options,
      json: data,
    })
    .json<T>();
}

export async function apiDelete<T = void>(
  url: string,
  options?: Options
): Promise<T> {
  const response = await api.delete(url, options);
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json<T>();
}
