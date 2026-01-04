import { createContext, useContext, type ReactNode } from "react";
import { useSidebar } from "@/hooks/use-sidebar";

export interface SidebarContextType {
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

interface SidebarProviderProps {
  children: ReactNode;
}

export function createSidebarContext(storageKey: string) {
  const SidebarContext = createContext<SidebarContextType | null>(null);

  function useSidebarContext() {
    const context = useContext(SidebarContext);
    if (!context) {
      throw new Error(
        `useSidebarContext must be used within a SidebarProvider created with storageKey "${storageKey}"`
      );
    }
    return context;
  }

  function Provider({ children }: SidebarProviderProps) {
    const sidebar = useSidebar(storageKey);

    return (
      <SidebarContext.Provider value={sidebar}>
        {children}
      </SidebarContext.Provider>
    );
  }

  return {
    Provider,
    useSidebarContext,
  };
}
