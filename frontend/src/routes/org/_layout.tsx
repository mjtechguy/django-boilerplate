import { createFileRoute, redirect } from "@tanstack/react-router";
import { OrgLayout } from "@/components/layouts/org-layout";

export const Route = createFileRoute("/org/_layout")({
  beforeLoad: async ({ context }) => {
    const { auth } = context;

    // Check authentication
    if (!auth.isAuthenticated && !auth.isLoading) {
      throw redirect({ to: "/login" });
    }

    // Check role - org_admin or higher can access
    const roles = auth.user
      ? [...auth.user.realmRoles, ...auth.user.clientRoles]
      : [];

    const allowedRoles = ["platform_admin", "org_admin"];
    const hasAccess = allowedRoles.some((role) => roles.includes(role));

    if (!hasAccess) {
      throw redirect({ to: "/unauthorized" });
    }
  },
  component: OrgLayout,
});
