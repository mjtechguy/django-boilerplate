import type { User } from "oidc-client-ts";
import type { AuthUser } from "@/types/auth";

interface TokenClaims {
  sub?: string;
  email?: string;
  name?: string;
  preferred_username?: string;
  roles?: string[];
  realm_access?: {
    roles?: string[];
  };
  resource_access?: {
    api?: {
      roles?: string[];
    };
    [key: string]: { roles?: string[] } | undefined;
  };
  org_id?: string;
  team_ids?: string[];
}

export function parseUser(oidcUser: User): AuthUser {
  const profile = oidcUser.profile as TokenClaims;

  // Extract realm roles
  const realmRoles = profile.realm_access?.roles ?? [];

  // Extract client roles from 'roles' claim (Keycloak maps client roles there)
  // or from resource_access.api.roles
  const clientRoles =
    profile.roles ??
    profile.resource_access?.api?.roles ??
    [];

  return {
    sub: profile.sub ?? "",
    email: profile.email ?? "",
    name: profile.name ?? profile.preferred_username ?? "",
    preferred_username: profile.preferred_username,
    realmRoles,
    clientRoles,
    orgId: profile.org_id,
    teamIds: profile.team_ids,
  };
}

export function hasRole(user: AuthUser | null, roles: string[]): boolean {
  if (!user) return false;

  const userRoles = [...user.realmRoles, ...user.clientRoles];
  return roles.some((role) => userRoles.includes(role));
}

export function hasAnyRole(user: AuthUser | null, roles: string[]): boolean {
  return hasRole(user, roles);
}

export function hasAllRoles(user: AuthUser | null, roles: string[]): boolean {
  if (!user) return false;

  const userRoles = [...user.realmRoles, ...user.clientRoles];
  return roles.every((role) => userRoles.includes(role));
}
