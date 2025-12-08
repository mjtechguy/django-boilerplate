import { createFileRoute, redirect } from "@tanstack/react-router";
import { LandingPage } from "@/components/landing";

export const Route = createFileRoute("/")({
  beforeLoad: async ({ context }) => {
    const { auth } = context;

    // If loading, wait for auth to resolve
    if (auth.isLoading) {
      return;
    }

    // If not authenticated, show landing page (handled by component)
    if (!auth.isAuthenticated) {
      return;
    }

    // Get user roles
    const roles = auth.user
      ? [...auth.user.realmRoles, ...auth.user.clientRoles]
      : [];

    // Role-based redirect logic for authenticated users
    // 1. Platform admins go to /admin
    if (roles.includes("platform_admin")) {
      throw redirect({ to: "/admin" });
    }

    // 2. Org admins go to /org
    if (roles.includes("org_admin")) {
      throw redirect({ to: "/org" });
    }

    // 3. All other authenticated users go to /app
    throw redirect({ to: "/app" });
  },
  component: LandingPage,
});
