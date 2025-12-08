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

const SidebarContext = createContext<SidebarContextType | null>(null);

export function useSidebarContext() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebarContext must be used within SidebarProvider");
  }
  return context;
}

interface SidebarProviderProps {
  children: ReactNode;
  storageKey?: string;
}

export function SidebarProvider({
  children,
  storageKey = "admin-sidebar",
}: SidebarProviderProps) {
  const sidebar = useSidebar(storageKey);

  return (
    <SidebarContext.Provider value={sidebar}>
      {children}
    </SidebarContext.Provider>
  );
}
