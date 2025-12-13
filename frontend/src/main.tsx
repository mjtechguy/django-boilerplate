import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { RouterProvider, createRouter } from "@tanstack/react-router";
import { AuthProvider, useAuth } from "@/lib/auth";
import { WebSocketProvider } from "@/lib/websocket";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { DynamicTheme } from "@/components/providers/dynamic-theme";
import { queryClient } from "@/lib/api";
import { routeTree } from "./routeTree.gen";
import "./index.css";

// Create router instance
const router = createRouter({
  routeTree,
  context: {
    auth: undefined!,
    queryClient,
  },
  defaultPreload: "intent",
  defaultPreloadStaleTime: 0,
});

// Register router for type safety
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

function InnerApp() {
  const auth = useAuth();
  return (
    <WebSocketProvider>
      <RouterProvider router={router} context={{ auth, queryClient }} />
    </WebSocketProvider>
  );
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="theme">
      <QueryClientProvider client={queryClient}>
        <DynamicTheme>
          <AuthProvider>
            <InnerApp />
          </AuthProvider>
        </DynamicTheme>
        {import.meta.env.DEV && <ReactQueryDevtools buttonPosition="bottom-left" />}
      </QueryClientProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
