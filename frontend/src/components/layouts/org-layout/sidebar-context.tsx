import { createSidebarContext } from "@/components/shared/sidebar-context";

// Create org-specific sidebar context with 'org-sidebar' storage key
const { Provider, useSidebarContext: useOrgSidebarContextInternal } =
  createSidebarContext("org-sidebar");

// Export with backward-compatible names for existing consumers
export const OrgSidebarProvider = Provider;
export const useOrgSidebarContext = useOrgSidebarContextInternal;
