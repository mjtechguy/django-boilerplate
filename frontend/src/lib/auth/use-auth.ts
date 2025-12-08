import { useContext } from "react";
import { AuthContext } from "./auth-context";
import { hasRole, hasAnyRole, hasAllRoles } from "./parse-user";
import type { AuthContextType, UserRole } from "@/types/auth";

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

export function useUser() {
  const { user } = useAuth();
  return user;
}

export function useIsAuthenticated(): boolean {
  const { isAuthenticated } = useAuth();
  return isAuthenticated;
}

export function useHasRole(roles: UserRole | UserRole[]): boolean {
  const { user } = useAuth();
  const roleArray = Array.isArray(roles) ? roles : [roles];
  return hasRole(user, roleArray);
}

export function useHasAnyRole(roles: UserRole[]): boolean {
  const { user } = useAuth();
  return hasAnyRole(user, roles);
}

export function useHasAllRoles(roles: UserRole[]): boolean {
  const { user } = useAuth();
  return hasAllRoles(user, roles);
}

export function useIsPlatformAdmin(): boolean {
  return useHasRole("platform_admin");
}

export function useIsOrgAdmin(): boolean {
  return useHasAnyRole(["platform_admin", "org_admin"]);
}
