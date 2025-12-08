import type { ReactNode } from "react";
import { useHasAnyRole } from "@/lib/auth";
import type { UserRole } from "@/types/auth";

interface RequireRoleProps {
  roles: UserRole | UserRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RequireRole({ roles, children, fallback = null }: RequireRoleProps) {
  const roleArray = Array.isArray(roles) ? roles : [roles];
  const hasRole = useHasAnyRole(roleArray);

  if (!hasRole) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

interface HideForRoleProps {
  roles: UserRole | UserRole[];
  children: ReactNode;
}

export function HideForRole({ roles, children }: HideForRoleProps) {
  const roleArray = Array.isArray(roles) ? roles : [roles];
  const hasRole = useHasAnyRole(roleArray);

  if (hasRole) {
    return null;
  }

  return <>{children}</>;
}
