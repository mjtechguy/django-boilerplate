import { describe, it, expect } from "vitest";
import type { User } from "oidc-client-ts";
import { parseUser, hasRole, hasAnyRole, hasAllRoles } from "./parse-user";
import type { AuthUser } from "@/types/auth";

describe("parse-user", () => {
  describe("parseUser", () => {
    it("extracts basic user info from OIDC user object", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          preferred_username: "johndoe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result).toEqual({
        sub: "user-123",
        email: "user@example.com",
        name: "John Doe",
        preferred_username: "johndoe",
        realmRoles: [],
        clientRoles: [],
        orgId: undefined,
        teamIds: undefined,
      });
    });

    it("extracts realm roles from realm_access", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          realm_access: {
            roles: ["platform_admin", "support_readonly"],
          },
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.realmRoles).toEqual(["platform_admin", "support_readonly"]);
      expect(result.clientRoles).toEqual([]);
    });

    it("extracts client roles from roles claim", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          roles: ["org_admin", "org_member"],
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.clientRoles).toEqual(["org_admin", "org_member"]);
      expect(result.realmRoles).toEqual([]);
    });

    it("extracts client roles from resource_access.api.roles", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          resource_access: {
            api: {
              roles: ["team_admin", "team_member"],
            },
          },
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.clientRoles).toEqual(["team_admin", "team_member"]);
    });

    it("prefers roles claim over resource_access for client roles", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          roles: ["org_admin"],
          resource_access: {
            api: {
              roles: ["team_member"],
            },
          },
        },
      } as User;

      const result = parseUser(oidcUser);

      // Should use roles claim, not resource_access
      expect(result.clientRoles).toEqual(["org_admin"]);
    });

    it("extracts both realm and client roles", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          realm_access: {
            roles: ["platform_admin"],
          },
          roles: ["org_admin", "org_member"],
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.realmRoles).toEqual(["platform_admin"]);
      expect(result.clientRoles).toEqual(["org_admin", "org_member"]);
    });

    it("extracts org_id and team_ids", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          org_id: "org-456",
          team_ids: ["team-1", "team-2"],
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.orgId).toBe("org-456");
      expect(result.teamIds).toEqual(["team-1", "team-2"]);
    });

    it("uses preferred_username as name fallback when name is missing", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          preferred_username: "johndoe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.name).toBe("johndoe");
    });

    it("handles missing name and preferred_username", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.name).toBe("");
    });

    it("handles missing sub with empty string", () => {
      const oidcUser = {
        profile: {
          email: "user@example.com",
          name: "John Doe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.sub).toBe("");
    });

    it("handles missing email with empty string", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          name: "John Doe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.email).toBe("");
    });

    it("handles empty realm_access.roles array", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          realm_access: {
            roles: [],
          },
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.realmRoles).toEqual([]);
    });

    it("handles missing realm_access entirely", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.realmRoles).toEqual([]);
    });

    it("handles missing resource_access entirely", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.clientRoles).toEqual([]);
    });

    it("handles resource_access without api property", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          resource_access: {
            other: {
              roles: ["some-role"],
            },
          },
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.clientRoles).toEqual([]);
    });

    it("handles complete user with all fields populated", () => {
      const oidcUser = {
        profile: {
          sub: "user-123",
          email: "user@example.com",
          name: "John Doe",
          preferred_username: "johndoe",
          realm_access: {
            roles: ["platform_admin"],
          },
          roles: ["org_admin", "org_member"],
          org_id: "org-456",
          team_ids: ["team-1", "team-2"],
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result).toEqual({
        sub: "user-123",
        email: "user@example.com",
        name: "John Doe",
        preferred_username: "johndoe",
        realmRoles: ["platform_admin"],
        clientRoles: ["org_admin", "org_member"],
        orgId: "org-456",
        teamIds: ["team-1", "team-2"],
      });
    });
  });

  describe("hasRole", () => {
    const createUser = (realmRoles: string[], clientRoles: string[]): AuthUser => ({
      sub: "user-123",
      email: "user@example.com",
      name: "John Doe",
      realmRoles,
      clientRoles,
    });

    it("returns true when user has one of the specified roles in realmRoles", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasRole(user, ["platform_admin"])).toBe(true);
    });

    it("returns true when user has one of the specified roles in clientRoles", () => {
      const user = createUser([], ["org_admin"]);

      expect(hasRole(user, ["org_admin"])).toBe(true);
    });

    it("returns true when user has role in either realm or client roles", () => {
      const user = createUser(["platform_admin"], ["org_admin"]);

      expect(hasRole(user, ["platform_admin"])).toBe(true);
      expect(hasRole(user, ["org_admin"])).toBe(true);
    });

    it("returns true when checking multiple roles and user has at least one", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasRole(user, ["platform_admin", "org_admin", "team_member"])).toBe(true);
    });

    it("returns false when user does not have any of the specified roles", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasRole(user, ["org_admin", "team_member"])).toBe(false);
    });

    it("returns false when user is null", () => {
      expect(hasRole(null, ["platform_admin"])).toBe(false);
    });

    it("returns false when roles array is empty", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasRole(user, [])).toBe(false);
    });

    it("returns false when user has no roles", () => {
      const user = createUser([], []);

      expect(hasRole(user, ["platform_admin"])).toBe(false);
    });

    it("checks both realm and client roles combined", () => {
      const user = createUser(["platform_admin"], ["org_admin", "team_member"]);

      // Should find roles from either list
      expect(hasRole(user, ["platform_admin"])).toBe(true);
      expect(hasRole(user, ["org_admin"])).toBe(true);
      expect(hasRole(user, ["team_member"])).toBe(true);
      expect(hasRole(user, ["support_readonly"])).toBe(false);
    });

    it("is case-sensitive for role matching", () => {
      const user = createUser(["platform_admin"], []);

      // Exact match required
      expect(hasRole(user, ["platform_admin"])).toBe(true);
      expect(hasRole(user, ["PLATFORM_ADMIN"])).toBe(false);
      expect(hasRole(user, ["Platform_Admin"])).toBe(false);
    });
  });

  describe("hasAnyRole", () => {
    const createUser = (realmRoles: string[], clientRoles: string[]): AuthUser => ({
      sub: "user-123",
      email: "user@example.com",
      name: "John Doe",
      realmRoles,
      clientRoles,
    });

    it("returns true when user has any of the specified roles", () => {
      const user = createUser(["platform_admin"], ["org_admin"]);

      expect(hasAnyRole(user, ["platform_admin", "team_member"])).toBe(true);
      expect(hasAnyRole(user, ["org_admin", "support_readonly"])).toBe(true);
    });

    it("returns false when user has none of the specified roles", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAnyRole(user, ["org_admin", "team_member"])).toBe(false);
    });

    it("returns false when user is null", () => {
      expect(hasAnyRole(null, ["platform_admin"])).toBe(false);
    });

    it("behaves identically to hasRole", () => {
      const user = createUser(["platform_admin"], ["org_admin"]);

      // hasAnyRole should be an alias for hasRole
      expect(hasAnyRole(user, ["platform_admin"])).toBe(hasRole(user, ["platform_admin"]));
      expect(hasAnyRole(user, ["org_admin"])).toBe(hasRole(user, ["org_admin"]));
      expect(hasAnyRole(user, ["team_member"])).toBe(hasRole(user, ["team_member"]));
    });

    it("returns true when checking single role that user has", () => {
      const user = createUser([], ["org_admin"]);

      expect(hasAnyRole(user, ["org_admin"])).toBe(true);
    });

    it("returns false when checking empty roles array", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAnyRole(user, [])).toBe(false);
    });
  });

  describe("hasAllRoles", () => {
    const createUser = (realmRoles: string[], clientRoles: string[]): AuthUser => ({
      sub: "user-123",
      email: "user@example.com",
      name: "John Doe",
      realmRoles,
      clientRoles,
    });

    it("returns true when user has all of the specified roles", () => {
      const user = createUser(["platform_admin"], ["org_admin", "org_member"]);

      expect(hasAllRoles(user, ["platform_admin", "org_admin"])).toBe(true);
      expect(hasAllRoles(user, ["org_admin", "org_member"])).toBe(true);
    });

    it("returns false when user has some but not all of the specified roles", () => {
      const user = createUser(["platform_admin"], ["org_admin"]);

      expect(hasAllRoles(user, ["platform_admin", "org_admin", "team_member"])).toBe(false);
    });

    it("returns false when user has none of the specified roles", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAllRoles(user, ["org_admin", "team_member"])).toBe(false);
    });

    it("returns false when user is null", () => {
      expect(hasAllRoles(null, ["platform_admin"])).toBe(false);
    });

    it("returns true when checking single role that user has", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAllRoles(user, ["platform_admin"])).toBe(true);
    });

    it("returns false when checking single role that user does not have", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAllRoles(user, ["org_admin"])).toBe(false);
    });

    it("checks both realm and client roles combined", () => {
      const user = createUser(["platform_admin"], ["org_admin", "org_member"]);

      // Can require roles from both lists
      expect(hasAllRoles(user, ["platform_admin", "org_admin"])).toBe(true);
      expect(hasAllRoles(user, ["platform_admin", "org_member"])).toBe(true);
      expect(hasAllRoles(user, ["org_admin", "org_member"])).toBe(true);
      expect(hasAllRoles(user, ["platform_admin", "org_admin", "org_member"])).toBe(true);
    });

    it("returns true when roles array is empty", () => {
      const user = createUser(["platform_admin"], []);

      // Every() returns true for empty array - user has all zero required roles
      expect(hasAllRoles(user, [])).toBe(true);
    });

    it("returns false for empty roles array when user is null", () => {
      expect(hasAllRoles(null, [])).toBe(false);
    });

    it("returns false when user has no roles but roles are required", () => {
      const user = createUser([], []);

      expect(hasAllRoles(user, ["platform_admin"])).toBe(false);
    });

    it("handles duplicate role requirements correctly", () => {
      const user = createUser(["platform_admin"], []);

      // Duplicate in requirements should not affect result
      expect(hasAllRoles(user, ["platform_admin", "platform_admin"])).toBe(true);
    });

    it("is case-sensitive for role matching", () => {
      const user = createUser(["platform_admin"], []);

      expect(hasAllRoles(user, ["platform_admin"])).toBe(true);
      expect(hasAllRoles(user, ["PLATFORM_ADMIN"])).toBe(false);
    });
  });

  describe("edge cases", () => {
    it("handles user with empty string values", () => {
      const oidcUser = {
        profile: {
          sub: "",
          email: "",
          name: "",
        },
      } as User;

      const result = parseUser(oidcUser);

      expect(result.sub).toBe("");
      expect(result.email).toBe("");
      expect(result.name).toBe("");
    });

    it("handles role checking with special characters in role names", () => {
      const user: AuthUser = {
        sub: "user-123",
        email: "user@example.com",
        name: "John Doe",
        realmRoles: ["role-with-dashes", "role_with_underscores"],
        clientRoles: ["role.with.dots"],
      };

      expect(hasRole(user, ["role-with-dashes"])).toBe(true);
      expect(hasRole(user, ["role_with_underscores"])).toBe(true);
      expect(hasRole(user, ["role.with.dots"])).toBe(true);
    });

    it("handles user with very long role arrays", () => {
      const manyRoles = Array.from({ length: 100 }, (_, i) => `role-${i}`);
      const user: AuthUser = {
        sub: "user-123",
        email: "user@example.com",
        name: "John Doe",
        realmRoles: manyRoles.slice(0, 50),
        clientRoles: manyRoles.slice(50),
      };

      expect(hasRole(user, ["role-0"])).toBe(true);
      expect(hasRole(user, ["role-99"])).toBe(true);
      expect(hasRole(user, ["role-100"])).toBe(false);
      expect(hasAllRoles(user, ["role-0", "role-50", "role-99"])).toBe(true);
    });

    it("handles undefined values in profile gracefully", () => {
      const oidcUser = {
        profile: {
          sub: undefined,
          email: undefined,
          name: undefined,
          preferred_username: undefined,
        },
      } as unknown as User;

      const result = parseUser(oidcUser);

      // Should default to empty strings
      expect(result.sub).toBe("");
      expect(result.email).toBe("");
      expect(result.name).toBe("");
    });
  });
});
