import { createRootRouteWithContext, Outlet } from "@tanstack/react-router";
import { TanStackRouterDevtools } from "@tanstack/react-router-devtools";
import { Toaster } from "sonner";
import type { QueryClient } from "@tanstack/react-query";
import type { AuthContextType } from "@/types/auth";

export interface RouterContext {
  auth: AuthContextType;
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootComponent,
});

function RootComponent() {
  return (
    <>
      <Outlet />
      <Toaster
        position="top-right"
        toastOptions={{
          classNames: {
            toast: "bg-background border-border",
            title: "text-foreground",
            description: "text-muted-foreground",
            error: "bg-destructive border-destructive text-destructive-foreground",
            success: "bg-background border-primary",
          },
        }}
      />
      {import.meta.env.DEV && <TanStackRouterDevtools position="bottom-right" />}
    </>
  );
}
