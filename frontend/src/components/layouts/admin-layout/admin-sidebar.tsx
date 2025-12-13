import { PanelLeftClose, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebarContext } from "./sidebar-context";
import { SidebarNav } from "./sidebar-nav";
import { SidebarUser } from "./sidebar-user";
import { SidebarResizeHandle } from "./sidebar-resize-handle";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function AdminSidebar() {
  const { isCollapsed, width, toggle } = useSidebarContext();

  return (
    <aside
      style={{ width }}
      className={cn(
        "relative flex h-screen flex-col",
        "bg-sidebar text-sidebar-foreground",
        "border-r border-sidebar-border",
        "transition-[width] duration-300 ease-in-out"
      )}
    >
      {/* Logo / Brand */}
      <div className="relative flex h-16 items-center justify-between border-b border-sidebar-border px-4">
        <div
          className={cn(
            "flex items-center gap-3 overflow-hidden transition-all duration-300",
            isCollapsed && "w-0 opacity-0"
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <span className="text-sm font-bold">A</span>
          </div>
          <span className="text-lg font-semibold tracking-tight whitespace-nowrap">
            Admin Portal
          </span>
        </div>

        {isCollapsed && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground mx-auto">
            <span className="text-sm font-bold">A</span>
          </div>
        )}

        {!isCollapsed && (
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggle}
                  className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
                >
                  <PanelLeftClose className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Collapse sidebar</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {/* Expand button when collapsed */}
      {isCollapsed && (
        <div className="relative px-3 pt-3">
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggle}
                  className="w-full h-9 text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
                >
                  <PanelLeft className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right">Expand sidebar</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}

      {/* Navigation */}
      <SidebarNav />

      {/* User section */}
      <SidebarUser />

      {/* Resize handle */}
      <SidebarResizeHandle />
    </aside>
  );
}
