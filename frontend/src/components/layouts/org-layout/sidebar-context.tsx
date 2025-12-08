import { createContext, useContext, type ReactNode } from "react";
import { useSidebar } from "@/hooks/use-sidebar";

interface SidebarContextType {
  isCollapsed: boolean;
  width: number;
  expandedWidth: number;
  toggle: () => void;
  collapse: () => void;
  expand: () => void;
  setWidth: (width: number) => void;
  minWidth: number;
  maxWidth: number;
  collapsedWidth: number;
}

const OrgSidebarContext = createContext<SidebarContextType | null>(null);

export function useOrgSidebarContext() {
  const context = useContext(OrgSidebarContext);
  if (!context) {
    throw new Error("useOrgSidebarContext must be used within OrgSidebarProvider");
  }
  return context;
}

interface OrgSidebarProviderProps {
  children: ReactNode;
}

export function OrgSidebarProvider({ children }: OrgSidebarProviderProps) {
  const sidebar = useSidebar("org-sidebar");

  return (
    <OrgSidebarContext.Provider value={sidebar}>
      {children}
    </OrgSidebarContext.Provider>
  );
}
