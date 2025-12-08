import { Outlet } from "@tanstack/react-router";
import { SidebarProvider } from "./sidebar-context";
import { AdminSidebar } from "./admin-sidebar";
import { AdminHeader } from "./admin-header";
import { ScrollArea } from "@/components/ui/scroll-area";

export function AdminLayout() {
  return (
    <SidebarProvider storageKey="admin-sidebar">
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Sidebar */}
        <AdminSidebar />

        {/* Main content area */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <AdminHeader />

          {/* Page content */}
          <ScrollArea className="flex-1">
            <main className="p-6">
              <Outlet />
            </main>
          </ScrollArea>
        </div>
      </div>
    </SidebarProvider>
  );
}

export { SidebarProvider, AdminSidebar, AdminHeader };
