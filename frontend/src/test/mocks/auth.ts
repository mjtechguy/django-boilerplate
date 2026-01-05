import type { AuthContextType, AuthUser, AuthProvider, UserRole } from "@/types/auth";
import { vi } from "vitest";

/**
 * Options for creating a mock user
 */
interface MockUserOptions {
  sub?: string;
  email?: string;
  name?: string;
  preferred_username?: string;
  realmRoles?: string[];
  clientRoles?: string[];
  orgId?: string;
  teamIds?: string[];
  authProvider?: AuthProvider;
  emailVerified?: boolean;
}

/**
 * Creates a mock AuthUser with sensible defaults
 * Can be customized with partial options
 *
 * @example
 * ```tsx
 * const user = createMockUser({
 *   email: 'admin@example.com',
 *   clientRoles: ['platform_admin']
 * });
 * ```
 */
export function createMockUser(options: MockUserOptions = {}): AuthUser {
  return {
    sub: options.sub ?? "test-user-id",
    email: options.email ?? "test@example.com",
    name: options.name ?? "Test User",
    preferred_username: options.preferred_username ?? "testuser",
    realmRoles: options.realmRoles ?? [],
    clientRoles: options.clientRoles ?? [],
    orgId: options.orgId,
    teamIds: options.teamIds ?? [],
    authProvider: options.authProvider ?? "local",
    emailVerified: options.emailVerified ?? true,
  };
}

/**
 * Creates a mock user with specific roles
 *
 * @example
 * ```tsx
 * const admin = createMockUserWithRoles(['platform_admin']);
 * const orgUser = createMockUserWithRoles(['org_admin', 'org_member'], {
 *   email: 'org@example.com',
 *   orgId: 'org-123'
 * });
 * ```
 */
export function createMockUserWithRoles(
  roles: UserRole[],
  options: MockUserOptions = {}
): AuthUser {
  return createMockUser({
    ...options,
    clientRoles: roles,
  });
}

/**
 * Common mock users for testing
 */
export const mockUsers = {
  /**
   * Unauthenticated user (null)
   */
  unauthenticated: null,

  /**
   * Regular authenticated user with no special roles
   */
  regular: createMockUser({
    email: "user@example.com",
    name: "Regular User",
  }),

  /**
   * Platform administrator with full access
   */
  platformAdmin: createMockUserWithRoles(["platform_admin"], {
    email: "admin@example.com",
    name: "Platform Admin",
  }),

  /**
   * Organization administrator
   */
  orgAdmin: createMockUserWithRoles(["org_admin", "org_member"], {
    email: "orgadmin@example.com",
    name: "Org Admin",
    orgId: "org-123",
  }),

  /**
   * Organization member
   */
  orgMember: createMockUserWithRoles(["org_member"], {
    email: "member@example.com",
    name: "Org Member",
    orgId: "org-123",
  }),

  /**
   * Team administrator
   */
  teamAdmin: createMockUserWithRoles(["team_admin", "team_member"], {
    email: "teamadmin@example.com",
    name: "Team Admin",
    orgId: "org-123",
    teamIds: ["team-456"],
  }),

  /**
   * User with unverified email
   */
  unverified: createMockUser({
    email: "unverified@example.com",
    name: "Unverified User",
    emailVerified: false,
  }),
};

/**
 * Creates a mock AuthContext with sensible defaults and mock functions
 * Can be customized with partial options
 *
 * @example
 * ```tsx
 * // Unauthenticated context
 * const context = createMockAuthContext();
 *
 * // Authenticated context with specific user
 * const context = createMockAuthContext({
 *   user: mockUsers.platformAdmin,
 *   isAuthenticated: true,
 * });
 * ```
 */
export function createMockAuthContext(
  overrides: Partial<AuthContextType> = {}
): AuthContextType {
  const defaultContext: AuthContextType = {
    isAuthenticated: false,
    isLoading: false,
    user: null,
    authProvider: null,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn().mockResolvedValue(undefined),
    getAccessToken: vi.fn().mockResolvedValue(null),
    loginLocal: vi.fn().mockResolvedValue(undefined),
    register: vi.fn().mockResolvedValue(undefined),
  };

  return {
    ...defaultContext,
    ...overrides,
  };
}

/**
 * Creates a mock AuthContext for an authenticated user
 *
 * @example
 * ```tsx
 * const context = createAuthenticatedContext(mockUsers.platformAdmin);
 * ```
 */
export function createAuthenticatedContext(
  user: AuthUser,
  authProvider: AuthProvider = "local"
): AuthContextType {
  return createMockAuthContext({
    isAuthenticated: true,
    user,
    authProvider,
    getAccessToken: vi.fn().mockResolvedValue("mock-access-token"),
  });
}

/**
 * Creates a mock AuthContext for a loading state
 *
 * @example
 * ```tsx
 * const context = createLoadingAuthContext();
 * ```
 */
export function createLoadingAuthContext(): AuthContextType {
  return createMockAuthContext({
    isLoading: true,
  });
}

/**
 * Mock implementation of login that simulates successful authentication
 * Useful for testing login flows
 */
export function createMockLogin(user: AuthUser = mockUsers.regular) {
  return vi.fn().mockImplementation(async () => {
    // Simulate async login delay
    await new Promise(resolve => setTimeout(resolve, 100));
    return user;
  });
}

/**
 * Mock implementation of login that simulates authentication failure
 * Useful for testing error handling
 */
export function createMockLoginFailure(errorMessage = "Invalid credentials") {
  return vi.fn().mockRejectedValue(new Error(errorMessage));
}

/**
 * Mock implementation of logout
 */
export function createMockLogout() {
  return vi.fn().mockResolvedValue(undefined);
}
