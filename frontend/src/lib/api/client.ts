import ky, { type KyInstance, type Options } from "ky";
import { getUserManager } from "@/lib/auth";
import { getLocalTokens, isLocalTokenExpired, clearLocalTokens } from "@/lib/auth/local-storage";

const API_URL = import.meta.env.VITE_API_URL || "";

async function getAuthorizationHeader(): Promise<string | undefined> {
  // 1. Check for local tokens first
  const localTokens = getLocalTokens();
  if (localTokens && !isLocalTokenExpired(localTokens)) {
    return `Bearer ${localTokens.accessToken}`;
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
      async (_request, _options, response) => {
        if (response.status === 401) {
          // Token expired or invalid - clear local tokens and redirect to login page
          clearLocalTokens();
          window.location.href = "/login";
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
