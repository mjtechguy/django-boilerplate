import { createFileRoute, redirect } from "@tanstack/react-router";
import { AdminLayout } from "@/components/layouts/admin-layout";

export const Route = createFileRoute("/admin/_layout")({
  beforeLoad: async ({ context }) => {
    const { auth } = context;

    // Check authentication
    if (!auth.isAuthenticated && !auth.isLoading) {
      throw redirect({ to: "/login" });
    }

    // Check role
    const roles = auth.user
      ? [...auth.user.realmRoles, ...auth.user.clientRoles]
      : [];

    if (!roles.includes("platform_admin")) {
      throw redirect({ to: "/unauthorized" });
    }
  },
  component: AdminLayout,
});
