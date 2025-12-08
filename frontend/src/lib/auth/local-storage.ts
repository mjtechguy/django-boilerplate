/**
 * Local token storage utilities.
 *
 * Handles storage and retrieval of local auth tokens in sessionStorage.
 * Uses sessionStorage for better security (cleared when browser closes).
 */

import type { LocalTokens, LoginResponse } from "@/types/auth";

const STORAGE_KEY = "local_auth_tokens";

/**
 * Store local auth tokens.
 */
export function storeLocalTokens(response: LoginResponse): void {
  const tokens: LocalTokens = {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    expiresAt: Date.now() + response.expires_in * 1000,
  };

  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
  } catch (e) {
    console.error("Failed to store tokens:", e);
  }
}

/**
 * Get stored local auth tokens.
 */
export function getLocalTokens(): LocalTokens | null {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (!stored) return null;

    return JSON.parse(stored) as LocalTokens;
  } catch (e) {
    console.error("Failed to get tokens:", e);
    return null;
  }
}

/**
 * Clear stored local auth tokens.
 */
export function clearLocalTokens(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.error("Failed to clear tokens:", e);
  }
}

/**
 * Check if the access token is expired or will expire soon.
 * Returns true if token is expired or expires within the buffer time.
 */
export function isLocalTokenExpired(
  tokens: LocalTokens | null,
  bufferSeconds: number = 60
): boolean {
  if (!tokens) return true;

  const bufferMs = bufferSeconds * 1000;
  return tokens.expiresAt - bufferMs <= Date.now();
}

/**
 * Update the stored access token after a refresh.
 */
export function updateAccessToken(accessToken: string, expiresIn: number): void {
  const tokens = getLocalTokens();
  if (!tokens) return;

  const updatedTokens: LocalTokens = {
    ...tokens,
    accessToken,
    expiresAt: Date.now() + expiresIn * 1000,
  };

  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(updatedTokens));
  } catch (e) {
    console.error("Failed to update tokens:", e);
  }
}

/**
 * Parse a JWT token and extract payload (without verification).
 * Used for reading claims from local tokens.
 */
export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const payload = parts[1];
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded);
  } catch (e) {
    console.error("Failed to parse JWT:", e);
    return null;
  }
}
