import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  storeLocalTokens,
  getLocalTokens,
  clearLocalTokens,
  isLocalTokenExpired,
  updateAccessToken,
  parseJwtPayload,
} from "./local-storage";
import type { LoginResponse, LocalTokens } from "@/types/auth";

describe("local-storage", () => {
  beforeEach(() => {
    // Clear sessionStorage before each test
    sessionStorage.clear();
    // Clear console.error mock
    vi.clearAllMocks();
  });

  describe("storeLocalTokens", () => {
    it("stores tokens in sessionStorage correctly", () => {
      const loginResponse: LoginResponse = {
        access_token: "test-access-token",
        refresh_token: "test-refresh-token",
        token_type: "Bearer",
        expires_in: 3600,
      };

      const beforeTime = Date.now();
      storeLocalTokens(loginResponse);
      const afterTime = Date.now();

      const stored = sessionStorage.getItem("local_auth_tokens");
      expect(stored).not.toBeNull();

      const parsed = JSON.parse(stored!) as LocalTokens;
      expect(parsed.accessToken).toBe("test-access-token");
      expect(parsed.refreshToken).toBe("test-refresh-token");
      expect(parsed.expiresAt).toBeGreaterThanOrEqual(beforeTime + 3600 * 1000);
      expect(parsed.expiresAt).toBeLessThanOrEqual(afterTime + 3600 * 1000);
    });

    it("calculates expiresAt correctly from expires_in", () => {
      const loginResponse: LoginResponse = {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "Bearer",
        expires_in: 7200, // 2 hours
      };

      const beforeTime = Date.now();
      storeLocalTokens(loginResponse);

      const stored = sessionStorage.getItem("local_auth_tokens");
      const parsed = JSON.parse(stored!) as LocalTokens;

      // Should be approximately 2 hours from now
      const expectedExpiry = beforeTime + 7200 * 1000;
      expect(parsed.expiresAt).toBeGreaterThanOrEqual(expectedExpiry - 100); // Allow 100ms margin
      expect(parsed.expiresAt).toBeLessThanOrEqual(expectedExpiry + 100);
    });

    it("handles storage errors gracefully", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      // Mock sessionStorage.setItem to throw an error
      const originalSetItem = sessionStorage.setItem;
      sessionStorage.setItem = vi.fn(() => {
        throw new Error("Storage quota exceeded");
      });

      const loginResponse: LoginResponse = {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "Bearer",
        expires_in: 3600,
      };

      // Should not throw
      expect(() => storeLocalTokens(loginResponse)).not.toThrow();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to store tokens:",
        expect.any(Error)
      );

      // Restore original
      sessionStorage.setItem = originalSetItem;
      consoleErrorSpy.mockRestore();
    });

    it("overwrites existing tokens", () => {
      const firstResponse: LoginResponse = {
        access_token: "first-token",
        refresh_token: "first-refresh",
        token_type: "Bearer",
        expires_in: 3600,
      };

      const secondResponse: LoginResponse = {
        access_token: "second-token",
        refresh_token: "second-refresh",
        token_type: "Bearer",
        expires_in: 7200,
      };

      storeLocalTokens(firstResponse);
      storeLocalTokens(secondResponse);

      const stored = sessionStorage.getItem("local_auth_tokens");
      const parsed = JSON.parse(stored!) as LocalTokens;

      expect(parsed.accessToken).toBe("second-token");
      expect(parsed.refreshToken).toBe("second-refresh");
    });
  });

  describe("getLocalTokens", () => {
    it("retrieves stored tokens correctly", () => {
      const tokens: LocalTokens = {
        accessToken: "test-access-token",
        refreshToken: "test-refresh-token",
        expiresAt: Date.now() + 3600 * 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(tokens));

      const result = getLocalTokens();

      expect(result).toEqual(tokens);
    });

    it("returns null when no tokens are stored", () => {
      const result = getLocalTokens();

      expect(result).toBeNull();
    });

    it("returns null when stored value is malformed JSON", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      sessionStorage.setItem("local_auth_tokens", "not valid json {{{");

      const result = getLocalTokens();

      expect(result).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to get tokens:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it("handles storage errors gracefully", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      // Mock sessionStorage.getItem to throw an error
      const originalGetItem = sessionStorage.getItem;
      sessionStorage.getItem = vi.fn(() => {
        throw new Error("Storage access denied");
      });

      const result = getLocalTokens();

      expect(result).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to get tokens:",
        expect.any(Error)
      );

      // Restore original
      sessionStorage.getItem = originalGetItem;
      consoleErrorSpy.mockRestore();
    });

    it("parses all LocalTokens fields correctly", () => {
      const tokens: LocalTokens = {
        accessToken: "access-123",
        refreshToken: "refresh-456",
        expiresAt: 1234567890123,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(tokens));

      const result = getLocalTokens();

      expect(result).not.toBeNull();
      expect(result?.accessToken).toBe("access-123");
      expect(result?.refreshToken).toBe("refresh-456");
      expect(result?.expiresAt).toBe(1234567890123);
    });
  });

  describe("clearLocalTokens", () => {
    it("removes tokens from sessionStorage", () => {
      const tokens: LocalTokens = {
        accessToken: "test-token",
        refreshToken: "test-refresh",
        expiresAt: Date.now() + 3600 * 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(tokens));
      expect(sessionStorage.getItem("local_auth_tokens")).not.toBeNull();

      clearLocalTokens();

      expect(sessionStorage.getItem("local_auth_tokens")).toBeNull();
    });

    it("handles clearing when no tokens exist", () => {
      expect(sessionStorage.getItem("local_auth_tokens")).toBeNull();

      // Should not throw
      expect(() => clearLocalTokens()).not.toThrow();

      expect(sessionStorage.getItem("local_auth_tokens")).toBeNull();
    });

    it("handles storage errors gracefully", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      // Mock sessionStorage.removeItem to throw an error
      const originalRemoveItem = sessionStorage.removeItem;
      sessionStorage.removeItem = vi.fn(() => {
        throw new Error("Storage access denied");
      });

      // Should not throw
      expect(() => clearLocalTokens()).not.toThrow();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to clear tokens:",
        expect.any(Error)
      );

      // Restore original
      sessionStorage.removeItem = originalRemoveItem;
      consoleErrorSpy.mockRestore();
    });
  });

  describe("isLocalTokenExpired", () => {
    it("returns true for null tokens", () => {
      expect(isLocalTokenExpired(null)).toBe(true);
    });

    it("returns true when token is expired", () => {
      const expiredTokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() - 1000, // Expired 1 second ago
      };

      expect(isLocalTokenExpired(expiredTokens)).toBe(true);
    });

    it("returns false when token is not expired and outside buffer", () => {
      const validTokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 120 * 1000, // Expires in 2 minutes
      };

      expect(isLocalTokenExpired(validTokens)).toBe(false);
    });

    it("returns true when token expires within default buffer (60 seconds)", () => {
      const almostExpiredTokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 30 * 1000, // Expires in 30 seconds
      };

      expect(isLocalTokenExpired(almostExpiredTokens)).toBe(true);
    });

    it("uses custom buffer when provided", () => {
      const tokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 150 * 1000, // Expires in 150 seconds
      };

      // With 60 second buffer, should be valid
      expect(isLocalTokenExpired(tokens, 60)).toBe(false);

      // With 200 second buffer, should be expired
      expect(isLocalTokenExpired(tokens, 200)).toBe(true);
    });

    it("returns true when token expires exactly at buffer time", () => {
      const tokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 60 * 1000, // Expires in exactly 60 seconds
      };

      // At exactly buffer time, should be considered expired
      expect(isLocalTokenExpired(tokens, 60)).toBe(true);
    });

    it("handles zero buffer", () => {
      const tokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 1000, // Expires in 1 second
      };

      expect(isLocalTokenExpired(tokens, 0)).toBe(false);

      const expiredTokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() - 1, // Expired 1ms ago
      };

      expect(isLocalTokenExpired(expiredTokens, 0)).toBe(true);
    });

    it("handles large buffer values", () => {
      const tokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now() + 3600 * 1000, // Expires in 1 hour
      };

      // Even with 2 hour buffer, should be marked as expired
      expect(isLocalTokenExpired(tokens, 7200)).toBe(true);
    });
  });

  describe("updateAccessToken", () => {
    it("updates access token and expiresAt correctly", () => {
      const initialTokens: LocalTokens = {
        accessToken: "old-token",
        refreshToken: "refresh-token",
        expiresAt: Date.now() + 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(initialTokens));

      const beforeTime = Date.now();
      updateAccessToken("new-access-token", 7200);
      const afterTime = Date.now();

      const updated = getLocalTokens();

      expect(updated).not.toBeNull();
      expect(updated?.accessToken).toBe("new-access-token");
      expect(updated?.refreshToken).toBe("refresh-token"); // Should remain unchanged
      expect(updated?.expiresAt).toBeGreaterThanOrEqual(beforeTime + 7200 * 1000);
      expect(updated?.expiresAt).toBeLessThanOrEqual(afterTime + 7200 * 1000);
    });

    it("preserves refresh token when updating access token", () => {
      const initialTokens: LocalTokens = {
        accessToken: "old-token",
        refreshToken: "original-refresh-token",
        expiresAt: Date.now() + 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(initialTokens));

      updateAccessToken("new-token", 3600);

      const updated = getLocalTokens();

      expect(updated?.refreshToken).toBe("original-refresh-token");
    });

    it("does nothing when no tokens exist", () => {
      expect(sessionStorage.getItem("local_auth_tokens")).toBeNull();

      updateAccessToken("new-token", 3600);

      expect(sessionStorage.getItem("local_auth_tokens")).toBeNull();
    });

    it("handles storage errors gracefully", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      const initialTokens: LocalTokens = {
        accessToken: "old-token",
        refreshToken: "refresh-token",
        expiresAt: Date.now() + 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(initialTokens));

      // Mock sessionStorage.setItem to throw an error
      const originalSetItem = sessionStorage.setItem;
      sessionStorage.setItem = vi.fn(() => {
        throw new Error("Storage quota exceeded");
      });

      // Should not throw
      expect(() => updateAccessToken("new-token", 3600)).not.toThrow();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to update tokens:",
        expect.any(Error)
      );

      // Restore original
      sessionStorage.setItem = originalSetItem;
      consoleErrorSpy.mockRestore();
    });

    it("calculates new expiresAt correctly from expiresIn", () => {
      const initialTokens: LocalTokens = {
        accessToken: "old-token",
        refreshToken: "refresh-token",
        expiresAt: Date.now() + 1000,
      };

      sessionStorage.setItem("local_auth_tokens", JSON.stringify(initialTokens));

      const beforeTime = Date.now();
      updateAccessToken("new-token", 1800); // 30 minutes

      const updated = getLocalTokens();
      const expectedExpiry = beforeTime + 1800 * 1000;

      expect(updated?.expiresAt).toBeGreaterThanOrEqual(expectedExpiry - 100);
      expect(updated?.expiresAt).toBeLessThanOrEqual(expectedExpiry + 100);
    });
  });

  describe("parseJwtPayload", () => {
    // Helper to create a valid JWT token for testing
    function createTestJwt(payload: Record<string, unknown>): string {
      const header = { alg: "HS256", typ: "JWT" };
      const encodedHeader = btoa(JSON.stringify(header));
      const encodedPayload = btoa(JSON.stringify(payload));
      const signature = "fake-signature";
      return `${encodedHeader}.${encodedPayload}.${signature}`;
    }

    it("parses JWT payload correctly", () => {
      const payload = {
        sub: "user-123",
        email: "user@example.com",
        exp: 1234567890,
      };

      const jwt = createTestJwt(payload);
      const result = parseJwtPayload(jwt);

      expect(result).toEqual(payload);
    });

    it("parses JWT with complex payload", () => {
      const payload = {
        sub: "user-456",
        email: "admin@example.com",
        name: "Admin User",
        roles: ["admin", "user"],
        org_id: "org-123",
        team_ids: ["team-1", "team-2"],
        exp: 9999999999,
        iat: 1234567890,
      };

      const jwt = createTestJwt(payload);
      const result = parseJwtPayload(jwt);

      expect(result).toEqual(payload);
    });

    it("returns null for invalid JWT with wrong number of parts", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(parseJwtPayload("invalid")).toBeNull();
      expect(parseJwtPayload("invalid.token")).toBeNull();
      expect(parseJwtPayload("invalid.token.with.too.many.parts")).toBeNull();

      consoleErrorSpy.mockRestore();
    });

    it("returns null for JWT with invalid base64 encoding", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      const invalidJwt = "header.!!!invalid-base64!!!.signature";
      const result = parseJwtPayload(invalidJwt);

      expect(result).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to parse JWT:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it("returns null for JWT with invalid JSON in payload", () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      const invalidPayload = btoa("not valid json {{{");
      const invalidJwt = `header.${invalidPayload}.signature`;
      const result = parseJwtPayload(invalidJwt);

      expect(result).toBeNull();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to parse JWT:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });

    it("handles JWT with empty payload", () => {
      const jwt = createTestJwt({});
      const result = parseJwtPayload(jwt);

      expect(result).toEqual({});
    });

    it("handles JWT with base64url encoding (- and _)", () => {
      // base64url uses - instead of + and _ instead of /
      // Create a payload that when base64 encoded will have + or /
      const payload = { test: "value with special chars >>> ??? <<<" };
      const payloadStr = JSON.stringify(payload);
      const base64 = btoa(payloadStr);

      // Convert to base64url format
      const base64url = base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");

      const jwt = `header.${base64url}.signature`;
      const result = parseJwtPayload(jwt);

      expect(result).toEqual(payload);
    });

    it("handles nested objects in payload", () => {
      const payload = {
        user: {
          id: "123",
          profile: {
            name: "John Doe",
            email: "john@example.com",
          },
        },
        metadata: {
          created: "2024-01-01",
          updated: "2024-01-02",
        },
      };

      const jwt = createTestJwt(payload);
      const result = parseJwtPayload(jwt);

      expect(result).toEqual(payload);
    });

    it("handles payload with various data types", () => {
      const payload = {
        string: "text",
        number: 42,
        boolean: true,
        nullValue: null,
        array: [1, 2, 3],
        object: { nested: "value" },
      };

      const jwt = createTestJwt(payload);
      const result = parseJwtPayload(jwt);

      expect(result).toEqual(payload);
    });
  });

  describe("edge cases", () => {
    it("handles concurrent storage operations", () => {
      const response1: LoginResponse = {
        access_token: "token1",
        refresh_token: "refresh1",
        token_type: "Bearer",
        expires_in: 3600,
      };

      const response2: LoginResponse = {
        access_token: "token2",
        refresh_token: "refresh2",
        token_type: "Bearer",
        expires_in: 7200,
      };

      // Store and retrieve multiple times
      storeLocalTokens(response1);
      const tokens1 = getLocalTokens();
      storeLocalTokens(response2);
      const tokens2 = getLocalTokens();

      expect(tokens1?.accessToken).toBe("token1");
      expect(tokens2?.accessToken).toBe("token2");
    });

    it("handles very long token strings", () => {
      const longToken = "a".repeat(10000);
      const response: LoginResponse = {
        access_token: longToken,
        refresh_token: longToken,
        token_type: "Bearer",
        expires_in: 3600,
      };

      storeLocalTokens(response);
      const tokens = getLocalTokens();

      expect(tokens?.accessToken).toBe(longToken);
      expect(tokens?.refreshToken).toBe(longToken);
    });

    it("handles token expiration at exact current time", () => {
      const tokens: LocalTokens = {
        accessToken: "token",
        refreshToken: "refresh",
        expiresAt: Date.now(),
      };

      // At exact current time with 0 buffer, should be expired
      expect(isLocalTokenExpired(tokens, 0)).toBe(true);
    });

    it("handles negative expires_in values", () => {
      const response: LoginResponse = {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "Bearer",
        expires_in: -3600, // Negative expiry
      };

      storeLocalTokens(response);
      const tokens = getLocalTokens();

      // Should store but the token will be expired immediately
      expect(tokens).not.toBeNull();
      expect(isLocalTokenExpired(tokens, 0)).toBe(true);
    });

    it("handles special characters in tokens", () => {
      const response: LoginResponse = {
        access_token: "token-with-special!@#$%^&*()_+chars",
        refresh_token: "refresh-with-unicode-\u00e9\u00f1",
        token_type: "Bearer",
        expires_in: 3600,
      };

      storeLocalTokens(response);
      const tokens = getLocalTokens();

      expect(tokens?.accessToken).toBe("token-with-special!@#$%^&*()_+chars");
      expect(tokens?.refreshToken).toBe("refresh-with-unicode-\u00e9\u00f1");
    });

    it("handles zero expires_in", () => {
      const response: LoginResponse = {
        access_token: "token",
        refresh_token: "refresh",
        token_type: "Bearer",
        expires_in: 0,
      };

      storeLocalTokens(response);
      const tokens = getLocalTokens();

      expect(tokens).not.toBeNull();
      expect(isLocalTokenExpired(tokens, 0)).toBe(true);
    });
  });
});
