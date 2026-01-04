import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { ReactNode } from "react";
import { AuthContext } from "./auth-context";
import {
  useAuth,
  useUser,
  useIsAuthenticated,
  useHasRole,
  useHasAnyRole,
  useHasAllRoles,
  useIsPlatformAdmin,
  useIsOrgAdmin,
} from "./use-auth";
import {
  createMockAuthContext,
  createAuthenticatedContext,
  mockUsers,
  createMockUser,
  createMockUserWithRoles,
} from "@/test/mocks/auth";
import type { AuthContextType } from "@/types/auth";

/**
 * Helper to create a wrapper with AuthContext
 */
function createWrapper(authContext: AuthContextType) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AuthContext.Provider value={authContext}>
        {children}
      </AuthContext.Provider>
    );
  };
}

describe("useAuth", () => {
  describe("error handling", () => {
    it("throws error when used outside AuthProvider", () => {
      // Suppress console.error for this test since we expect an error
      const consoleError = console.error;
      console.error = () => {};

      expect(() => {
        renderHook(() => useAuth());
      }).toThrow("useAuth must be used within an AuthProvider");

      console.error = consoleError;
    });

    it("returns context when used within AuthProvider", () => {
      const mockContext = createMockAuthContext();
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current).toBe(mockContext);
    });
  });

  describe("context values", () => {
    it("returns complete auth context with all properties", () => {
      const mockContext = createAuthenticatedContext(mockUsers.regular);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current).toHaveProperty("isAuthenticated");
      expect(result.current).toHaveProperty("isLoading");
      expect(result.current).toHaveProperty("user");
      expect(result.current).toHaveProperty("authProvider");
      expect(result.current).toHaveProperty("login");
      expect(result.current).toHaveProperty("logout");
      expect(result.current).toHaveProperty("getAccessToken");
      expect(result.current).toHaveProperty("loginLocal");
      expect(result.current).toHaveProperty("register");
    });

    it("returns unauthenticated context correctly", () => {
      const mockContext = createMockAuthContext();
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isAuthenticated).toBe(false);
      expect(result.current.user).toBeNull();
      expect(result.current.authProvider).toBeNull();
    });

    it("returns authenticated context correctly", () => {
      const mockContext = createAuthenticatedContext(mockUsers.regular);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isAuthenticated).toBe(true);
      expect(result.current.user).toBe(mockUsers.regular);
      expect(result.current.authProvider).toBe("local");
    });

    it("returns loading state correctly", () => {
      const mockContext = createMockAuthContext({ isLoading: true });
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useAuth(), { wrapper });

      expect(result.current.isLoading).toBe(true);
    });
  });
});

describe("useUser", () => {
  it("returns null when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current).toBeNull();
  });

  it("returns user when authenticated", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current).toBe(mockUsers.regular);
    expect(result.current?.email).toBe("user@example.com");
    expect(result.current?.name).toBe("Regular User");
  });

  it("returns platform admin user correctly", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current).toBe(mockUsers.platformAdmin);
    expect(result.current?.clientRoles).toContain("platform_admin");
  });

  it("returns org admin user correctly", () => {
    const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current).toBe(mockUsers.orgAdmin);
    expect(result.current?.clientRoles).toContain("org_admin");
    expect(result.current?.orgId).toBe("org-123");
  });

  it("returns user with custom properties", () => {
    const customUser = createMockUser({
      email: "custom@example.com",
      name: "Custom User",
      orgId: "custom-org",
      teamIds: ["team-1", "team-2"],
    });
    const mockContext = createAuthenticatedContext(customUser);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useUser(), { wrapper });

    expect(result.current?.email).toBe("custom@example.com");
    expect(result.current?.name).toBe("Custom User");
    expect(result.current?.orgId).toBe("custom-org");
    expect(result.current?.teamIds).toEqual(["team-1", "team-2"]);
  });
});

describe("useIsAuthenticated", () => {
  it("returns false when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsAuthenticated(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true when user is authenticated", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsAuthenticated(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns false during loading state when not authenticated", () => {
    const mockContext = createMockAuthContext({ isLoading: true });
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsAuthenticated(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true during loading state when already authenticated", () => {
    const mockContext = createMockAuthContext({
      isAuthenticated: true,
      isLoading: true,
      user: mockUsers.regular,
    });
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsAuthenticated(), { wrapper });

    expect(result.current).toBe(true);
  });
});

describe("useHasRole", () => {
  describe("single role checks", () => {
    it("returns false when user is not authenticated", () => {
      const mockContext = createMockAuthContext();
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("platform_admin"), { wrapper });

      expect(result.current).toBe(false);
    });

    it("returns true when user has the role in clientRoles", () => {
      const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("platform_admin"), { wrapper });

      expect(result.current).toBe(true);
    });

    it("returns false when user does not have the role", () => {
      const mockContext = createAuthenticatedContext(mockUsers.regular);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("platform_admin"), { wrapper });

      expect(result.current).toBe(false);
    });

    it("returns true when user has the role in realmRoles", () => {
      const user = createMockUser({
        realmRoles: ["platform_admin"],
        clientRoles: [],
      });
      const mockContext = createAuthenticatedContext(user);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("platform_admin"), { wrapper });

      expect(result.current).toBe(true);
    });

    it("checks org_admin role correctly", () => {
      const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("org_admin"), { wrapper });

      expect(result.current).toBe(true);
    });

    it("checks org_member role correctly", () => {
      const mockContext = createAuthenticatedContext(mockUsers.orgMember);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("org_member"), { wrapper });

      expect(result.current).toBe(true);
    });

    it("checks team_admin role correctly", () => {
      const mockContext = createAuthenticatedContext(mockUsers.teamAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole("team_admin"), { wrapper });

      expect(result.current).toBe(true);
    });
  });

  describe("multiple role checks", () => {
    it("returns true when user has any of the specified roles (array)", () => {
      const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(
        () => useHasRole(["platform_admin", "org_admin"]),
        { wrapper }
      );

      expect(result.current).toBe(true);
    });

    it("returns true when user has at least one role from array", () => {
      const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(
        () => useHasRole(["platform_admin", "org_admin", "support_readonly"]),
        { wrapper }
      );

      expect(result.current).toBe(true);
    });

    it("returns false when user has none of the specified roles", () => {
      const mockContext = createAuthenticatedContext(mockUsers.regular);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(
        () => useHasRole(["platform_admin", "org_admin"]),
        { wrapper }
      );

      expect(result.current).toBe(false);
    });

    it("handles empty array by returning false", () => {
      const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(() => useHasRole([]), { wrapper });

      expect(result.current).toBe(false);
    });
  });

  describe("edge cases", () => {
    it("is case-sensitive for role names", () => {
      const user = createMockUserWithRoles(["platform_admin"]);
      const mockContext = createAuthenticatedContext(user);
      const wrapper = createWrapper(mockContext);

      const { result } = renderHook(
        () => useHasRole("PLATFORM_ADMIN" as any),
        { wrapper }
      );

      expect(result.current).toBe(false);
    });

    it("handles user with multiple roles correctly", () => {
      const user = createMockUserWithRoles([
        "org_admin",
        "org_member",
        "team_admin",
        "team_member",
      ]);
      const mockContext = createAuthenticatedContext(user);
      const wrapper = createWrapper(mockContext);

      const { result: result1 } = renderHook(() => useHasRole("org_admin"), { wrapper });
      expect(result1.current).toBe(true);

      const { result: result2 } = renderHook(() => useHasRole("team_member"), { wrapper });
      expect(result2.current).toBe(true);

      const { result: result3 } = renderHook(() => useHasRole("platform_admin"), { wrapper });
      expect(result3.current).toBe(false);
    });
  });
});

describe("useHasAnyRole", () => {
  it("returns false when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAnyRole(["platform_admin", "org_admin"]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });

  it("returns true when user has any of the specified roles", () => {
    const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAnyRole(["platform_admin", "org_admin"]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("returns true when user has one role from many", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAnyRole([
        "support_readonly",
        "org_admin",
        "platform_admin",
        "team_admin",
      ]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("returns false when user has none of the specified roles", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAnyRole(["platform_admin", "org_admin", "team_admin"]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });

  it("returns true when user has multiple specified roles", () => {
    const user = createMockUserWithRoles(["org_admin", "org_member"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAnyRole(["org_admin", "org_member"]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("handles empty array by returning false", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useHasAnyRole([]), { wrapper });

    expect(result.current).toBe(false);
  });

  it("checks both realmRoles and clientRoles", () => {
    const user = createMockUser({
      realmRoles: ["realm_role_1"],
      clientRoles: ["client_role_1"],
    });
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result: result1 } = renderHook(
      () => useHasAnyRole(["realm_role_1" as any, "other_role" as any]),
      { wrapper }
    );
    expect(result1.current).toBe(true);

    const { result: result2 } = renderHook(
      () => useHasAnyRole(["client_role_1" as any, "other_role" as any]),
      { wrapper }
    );
    expect(result2.current).toBe(true);
  });
});

describe("useHasAllRoles", () => {
  it("returns false when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["org_admin", "org_member"]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });

  it("returns true when user has all specified roles", () => {
    const user = createMockUserWithRoles(["org_admin", "org_member"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["org_admin", "org_member"]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("returns false when user has only some of the specified roles", () => {
    const user = createMockUserWithRoles(["org_admin"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["org_admin", "org_member"]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });

  it("returns false when user has none of the specified roles", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["platform_admin", "org_admin"]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });

  it("returns true when user has all roles plus additional roles", () => {
    const user = createMockUserWithRoles([
      "platform_admin",
      "org_admin",
      "org_member",
      "team_admin",
    ]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["org_admin", "org_member"]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("handles empty array by returning true", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useHasAllRoles([]), { wrapper });

    expect(result.current).toBe(true);
  });

  it("handles single role requirement", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useHasAllRoles(["platform_admin"]), { wrapper });

    expect(result.current).toBe(true);
  });

  it("checks both realmRoles and clientRoles", () => {
    const user = createMockUser({
      realmRoles: ["realm_role_1"],
      clientRoles: ["client_role_1"],
    });
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles(["realm_role_1" as any, "client_role_1" as any]),
      { wrapper }
    );

    expect(result.current).toBe(true);
  });

  it("returns false when missing one role from mixed sources", () => {
    const user = createMockUser({
      realmRoles: ["realm_role_1"],
      clientRoles: ["client_role_1"],
    });
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(
      () => useHasAllRoles([
        "realm_role_1" as any,
        "client_role_1" as any,
        "missing_role" as any,
      ]),
      { wrapper }
    );

    expect(result.current).toBe(false);
  });
});

describe("useIsPlatformAdmin", () => {
  it("returns false when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true when user is platform admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns false when user is org admin but not platform admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns false when user is team admin but not platform admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.teamAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns false when user is regular user", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true when user has platform_admin in realmRoles", () => {
    const user = createMockUser({
      realmRoles: ["platform_admin"],
      clientRoles: [],
    });
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns true when user has multiple roles including platform_admin", () => {
    const user = createMockUserWithRoles([
      "platform_admin",
      "org_admin",
      "team_admin",
    ]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsPlatformAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });
});

describe("useIsOrgAdmin", () => {
  it("returns false when user is not authenticated", () => {
    const mockContext = createMockAuthContext();
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true when user is platform admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns true when user is org admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.orgAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns false when user is team admin but not org admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.teamAdmin);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns false when user is org member but not admin", () => {
    const mockContext = createAuthenticatedContext(mockUsers.orgMember);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns false when user is regular user", () => {
    const mockContext = createAuthenticatedContext(mockUsers.regular);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(false);
  });

  it("returns true when user has org_admin role only", () => {
    const user = createMockUserWithRoles(["org_admin"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns true when user has platform_admin role only", () => {
    const user = createMockUserWithRoles(["platform_admin"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("returns true when user has both platform_admin and org_admin", () => {
    const user = createMockUserWithRoles(["platform_admin", "org_admin"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => useIsOrgAdmin(), { wrapper });

    expect(result.current).toBe(true);
  });

  it("checks both realmRoles and clientRoles", () => {
    const user1 = createMockUser({
      realmRoles: ["org_admin"],
      clientRoles: [],
    });
    const mockContext1 = createAuthenticatedContext(user1);
    const wrapper1 = createWrapper(mockContext1);

    const { result: result1 } = renderHook(() => useIsOrgAdmin(), { wrapper: wrapper1 });
    expect(result1.current).toBe(true);

    const user2 = createMockUser({
      realmRoles: [],
      clientRoles: ["platform_admin"],
    });
    const mockContext2 = createAuthenticatedContext(user2);
    const wrapper2 = createWrapper(mockContext2);

    const { result: result2 } = renderHook(() => useIsOrgAdmin(), { wrapper: wrapper2 });
    expect(result2.current).toBe(true);
  });
});

describe("integration scenarios", () => {
  it("handles authentication state changes correctly", () => {
    // Start unauthenticated
    const mockContext1 = createMockAuthContext();
    const wrapper1 = createWrapper(mockContext1);

    const { result: result1 } = renderHook(() => ({
      isAuth: useIsAuthenticated(),
      user: useUser(),
      isPlatformAdmin: useIsPlatformAdmin(),
    }), { wrapper: wrapper1 });

    expect(result1.current.isAuth).toBe(false);
    expect(result1.current.user).toBeNull();
    expect(result1.current.isPlatformAdmin).toBe(false);

    // Authenticate as platform admin
    const mockContext2 = createAuthenticatedContext(mockUsers.platformAdmin);
    const wrapper2 = createWrapper(mockContext2);

    const { result: result2 } = renderHook(() => ({
      isAuth: useIsAuthenticated(),
      user: useUser(),
      isPlatformAdmin: useIsPlatformAdmin(),
    }), { wrapper: wrapper2 });

    expect(result2.current.isAuth).toBe(true);
    expect(result2.current.user).toBe(mockUsers.platformAdmin);
    expect(result2.current.isPlatformAdmin).toBe(true);
  });

  it("handles role-based access control scenarios", () => {
    const user = createMockUserWithRoles(["org_admin", "org_member"]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => ({
      hasOrgAdmin: useHasRole("org_admin"),
      hasOrgMember: useHasRole("org_member"),
      hasPlatformAdmin: useHasRole("platform_admin"),
      hasAnyAdmin: useHasAnyRole(["platform_admin", "org_admin"]),
      hasBothOrgRoles: useHasAllRoles(["org_admin", "org_member"]),
      isOrgAdmin: useIsOrgAdmin(),
      isPlatformAdmin: useIsPlatformAdmin(),
    }), { wrapper });

    expect(result.current.hasOrgAdmin).toBe(true);
    expect(result.current.hasOrgMember).toBe(true);
    expect(result.current.hasPlatformAdmin).toBe(false);
    expect(result.current.hasAnyAdmin).toBe(true);
    expect(result.current.hasBothOrgRoles).toBe(true);
    expect(result.current.isOrgAdmin).toBe(true);
    expect(result.current.isPlatformAdmin).toBe(false);
  });

  it("handles user with no roles correctly", () => {
    const user = createMockUserWithRoles([]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => ({
      hasAnyRole: useHasRole(["platform_admin", "org_admin"]),
      hasAllRoles: useHasAllRoles(["platform_admin", "org_admin"]),
      isOrgAdmin: useIsOrgAdmin(),
      isPlatformAdmin: useIsPlatformAdmin(),
    }), { wrapper });

    expect(result.current.hasAnyRole).toBe(false);
    expect(result.current.hasAllRoles).toBe(false);
    expect(result.current.isOrgAdmin).toBe(false);
    expect(result.current.isPlatformAdmin).toBe(false);
  });

  it("handles complex multi-role scenarios", () => {
    const user = createMockUserWithRoles([
      "platform_admin",
      "org_admin",
      "org_member",
      "team_admin",
      "team_member",
    ]);
    const mockContext = createAuthenticatedContext(user);
    const wrapper = createWrapper(mockContext);

    const { result } = renderHook(() => ({
      hasSingleRole: useHasRole("platform_admin"),
      hasAnyOfMany: useHasAnyRole([
        "platform_admin",
        "support_readonly",
        "billing_admin",
      ]),
      hasAllRequired: useHasAllRoles(["platform_admin", "org_admin"]),
      hasAllTeam: useHasAllRoles(["team_admin", "team_member"]),
      isOrgAdmin: useIsOrgAdmin(),
      isPlatformAdmin: useIsPlatformAdmin(),
    }), { wrapper });

    expect(result.current.hasSingleRole).toBe(true);
    expect(result.current.hasAnyOfMany).toBe(true);
    expect(result.current.hasAllRequired).toBe(true);
    expect(result.current.hasAllTeam).toBe(true);
    expect(result.current.isOrgAdmin).toBe(true);
    expect(result.current.isPlatformAdmin).toBe(true);
  });
});
