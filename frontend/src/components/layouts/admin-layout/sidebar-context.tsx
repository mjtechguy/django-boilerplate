import { createSidebarContext } from "@/components/shared/sidebar-context";

// Create admin-specific sidebar context with 'admin-sidebar' storage key
const { Provider, useSidebarContext: useAdminSidebarContext } =
  createSidebarContext("admin-sidebar");

// Export with backward-compatible names for existing consumers
export const SidebarProvider = Provider;
export const useSidebarContext = useAdminSidebarContext;
