import { createFileRoute, redirect } from "@tanstack/react-router";
import { AppLayout } from "@/components/layouts/app-layout";

export const Route = createFileRoute("/app/_layout")({
  beforeLoad: async ({ context }) => {
    const { auth } = context;

    // Check authentication - any authenticated user can access
    if (!auth.isAuthenticated && !auth.isLoading) {
      throw redirect({ to: "/login" });
    }
  },
  component: AppLayout,
});
