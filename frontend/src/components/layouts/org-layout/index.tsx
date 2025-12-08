import { Outlet } from "@tanstack/react-router";
import { OrgSidebarProvider } from "./sidebar-context";
import { OrgSidebar } from "./org-sidebar";
import { OrgHeader } from "./org-header";
import { ScrollArea } from "@/components/ui/scroll-area";

export function OrgLayout() {
  return (
    <OrgSidebarProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Sidebar */}
        <OrgSidebar />

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <OrgHeader />

          {/* Page content */}
          <ScrollArea className="flex-1">
            <main className="p-6">
              <Outlet />
            </main>
          </ScrollArea>
        </div>
      </div>
    </OrgSidebarProvider>
  );
}

export { OrgSidebarProvider, OrgSidebar, OrgHeader };
