import { Outlet } from "@tanstack/react-router";
import { AppHeader } from "./app-header";
import { ScrollArea } from "@/components/ui/scroll-area";

export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <AppHeader />

      {/* Main content */}
      <ScrollArea className="flex-1">
        <main className="container mx-auto px-4 py-6">
          <Outlet />
        </main>
      </ScrollArea>
    </div>
  );
}

export { AppHeader };
