/**
 * Parse a local JWT token and extract user information.
 *
 * The token structure matches Keycloak format for compatibility.
 */

import type { AuthUser } from "@/types/auth";
import { parseJwtPayload } from "./local-storage";

interface LocalJwtClaims {
  sub: string;
  email: string;
  email_verified?: boolean;
  preferred_username?: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  realm_access?: {
    roles?: string[];
  };
  resource_access?: Record<string, { roles?: string[] }>;
  org_id?: string;
  token_type?: string;
}

/**
 * Parse a local JWT access token and extract user information.
 */
export function parseLocalUser(accessToken: string): AuthUser | null {
  const claims = parseJwtPayload(accessToken) as LocalJwtClaims | null;

  if (!claims || !claims.sub) {
    return null;
  }

  // Extract realm roles
  const realmRoles = claims.realm_access?.roles || [];

  // Extract client roles (flatten all client roles into one array)
  const clientRoles: string[] = [];
  if (claims.resource_access) {
    for (const resource of Object.values(claims.resource_access)) {
      if (resource.roles) {
        clientRoles.push(...resource.roles);
      }
    }
  }

  // Build full name
  const name =
    claims.name ||
    [claims.given_name, claims.family_name].filter(Boolean).join(" ") ||
    claims.preferred_username ||
    claims.email;

  return {
    sub: claims.sub,
    email: claims.email,
    name: name || "",
    preferred_username: claims.preferred_username,
    realmRoles,
    clientRoles,
    orgId: claims.org_id,
    authProvider: "local",
    emailVerified: claims.email_verified,
  };
}
