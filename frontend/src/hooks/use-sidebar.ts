import { useCallback } from "react";
import { useLocalStorage } from "./use-local-storage";

interface SidebarState {
  isCollapsed: boolean;
  width: number;
}

const DEFAULT_WIDTH = 256;
const MIN_WIDTH = 200;
const MAX_WIDTH = 400;
const COLLAPSED_WIDTH = 64;

export function useSidebar(storageKey: string = "sidebar-state") {
  const [state, setState] = useLocalStorage<SidebarState>(storageKey, {
    isCollapsed: false,
    width: DEFAULT_WIDTH,
  });

  const toggle = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isCollapsed: !prev.isCollapsed,
    }));
  }, [setState]);

  const collapse = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isCollapsed: true,
    }));
  }, [setState]);

  const expand = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isCollapsed: false,
    }));
  }, [setState]);

  const setWidth = useCallback(
    (width: number) => {
      const clampedWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, width));
      setState((prev) => ({
        ...prev,
        width: clampedWidth,
      }));
    },
    [setState]
  );

  return {
    isCollapsed: state.isCollapsed,
    width: state.isCollapsed ? COLLAPSED_WIDTH : state.width,
    expandedWidth: state.width,
    toggle,
    collapse,
    expand,
    setWidth,
    minWidth: MIN_WIDTH,
    maxWidth: MAX_WIDTH,
    collapsedWidth: COLLAPSED_WIDTH,
  };
}
