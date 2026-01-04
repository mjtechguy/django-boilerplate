import { describe, it, expect, vi } from "vitest";
import { renderWithProviders } from "./test-utils";
import { createMockUser, mockUsers, createAuthenticatedContext } from "./mocks/auth";
import { useAuth, useUser, useIsAuthenticated } from "@/lib/auth/use-auth";

// Simple component that uses auth hooks for testing
function TestComponent() {
  const { isAuthenticated, user } = useAuth();

  return (
    <div>
      <div data-testid="auth-status">{isAuthenticated ? "Authenticated" : "Not Authenticated"}</div>
      <div data-testid="user-email">{user?.email ?? "No user"}</div>
    </div>
  );
}

describe("Test Utilities", () => {
  describe("renderWithProviders", () => {
    it("renders component with default unauthenticated state", () => {
      const { getByTestId } = renderWithProviders(<TestComponent />);

      expect(getByTestId("auth-status")).toHaveTextContent("Not Authenticated");
      expect(getByTestId("user-email")).toHaveTextContent("No user");
    });

    it("renders component with authenticated user", () => {
      const user = createMockUser({ email: "test@example.com" });

      const { getByTestId } = renderWithProviders(<TestComponent />, {
        authContext: {
          isAuthenticated: true,
          user,
        },
      });

      expect(getByTestId("auth-status")).toHaveTextContent("Authenticated");
      expect(getByTestId("user-email")).toHaveTextContent("test@example.com");
    });

    it("renders component with platform admin user", () => {
      const { getByTestId } = renderWithProviders(<TestComponent />, {
        authContext: {
          isAuthenticated: true,
          user: mockUsers.platformAdmin,
        },
      });

      expect(getByTestId("auth-status")).toHaveTextContent("Authenticated");
      expect(getByTestId("user-email")).toHaveTextContent("admin@example.com");
    });
  });

  describe("createMockUser", () => {
    it("creates user with default values", () => {
      const user = createMockUser();

      expect(user.sub).toBe("test-user-id");
      expect(user.email).toBe("test@example.com");
      expect(user.name).toBe("Test User");
      expect(user.clientRoles).toEqual([]);
      expect(user.emailVerified).toBe(true);
    });

    it("creates user with custom values", () => {
      const user = createMockUser({
        email: "custom@example.com",
        clientRoles: ["platform_admin"],
        orgId: "org-123",
      });

      expect(user.email).toBe("custom@example.com");
      expect(user.clientRoles).toContain("platform_admin");
      expect(user.orgId).toBe("org-123");
    });
  });

  describe("createAuthenticatedContext", () => {
    it("creates authenticated context with user", () => {
      const user = mockUsers.regular;
      const context = createAuthenticatedContext(user);

      expect(context.isAuthenticated).toBe(true);
      expect(context.user).toBe(user);
      expect(context.authProvider).toBe("local");
      expect(context.isLoading).toBe(false);
    });

    it("provides mock access token", async () => {
      const context = createAuthenticatedContext(mockUsers.regular);
      const token = await context.getAccessToken();

      expect(token).toBe("mock-access-token");
    });
  });

  describe("mockUsers", () => {
    it("provides platformAdmin with correct role", () => {
      const admin = mockUsers.platformAdmin;

      expect(admin.clientRoles).toContain("platform_admin");
      expect(admin.email).toBe("admin@example.com");
    });

    it("provides orgAdmin with correct roles", () => {
      const orgAdmin = mockUsers.orgAdmin;

      expect(orgAdmin.clientRoles).toContain("org_admin");
      expect(orgAdmin.clientRoles).toContain("org_member");
      expect(orgAdmin.orgId).toBe("org-123");
    });

    it("provides unverified user with emailVerified false", () => {
      const unverified = mockUsers.unverified;

      expect(unverified.emailVerified).toBe(false);
    });
  });
});
