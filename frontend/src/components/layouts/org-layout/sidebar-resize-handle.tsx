import { useCallback, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useOrgSidebarContext } from "./sidebar-context";

export function OrgSidebarResizeHandle() {
  const { setWidth, isCollapsed, minWidth, maxWidth } = useOrgSidebarContext();
  const [isResizing, setIsResizing] = useState(false);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isCollapsed) return;
      e.preventDefault();
      setIsResizing(true);
    },
    [isCollapsed]
  );

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = e.clientX;
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, setWidth, minWidth, maxWidth]);

  if (isCollapsed) return null;

  return (
    <div
      onMouseDown={handleMouseDown}
      className={cn(
        "absolute right-0 top-0 z-10 h-full w-1 cursor-col-resize",
        "bg-transparent hover:bg-primary/20 transition-colors duration-200",
        "after:absolute after:inset-y-0 after:right-0 after:w-4 after:-translate-x-1/2",
        isResizing && "bg-primary/30"
      )}
    />
  );
}
