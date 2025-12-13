import { Building2, PanelLeftClose, PanelLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrgSidebarContext } from "./sidebar-context";
import { OrgSidebarNav } from "./sidebar-nav";
import { OrgSidebarUser } from "./sidebar-user";
import { OrgSidebarResizeHandle } from "./sidebar-resize-handle";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function OrgSidebar() {
  const { isCollapsed, width, toggle } = useOrgSidebarContext();

  return (
    <aside
      style={{ width: isCollapsed ? undefined : width }}
      className={cn(
        "relative flex h-screen flex-col",
        "bg-sidebar text-sidebar-foreground",
        "border-r border-sidebar-border",
        "transition-[width] duration-300 ease-in-out",
        isCollapsed && "w-16"
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-16 items-center border-b border-sidebar-border px-4",
          isCollapsed && "justify-center px-2"
        )}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Building2 className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-semibold">Org Admin</span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
                Management
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <OrgSidebarNav />

      {/* User */}
      <OrgSidebarUser />

      {/* Collapse button */}
      <div className="absolute -right-3 top-20 z-20">
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                onClick={toggle}
                className="h-6 w-6 rounded-full border-border bg-background text-muted-foreground hover:bg-accent hover:text-foreground shadow-lg"
              >
                {isCollapsed ? (
                  <PanelLeft className="h-3 w-3" />
                ) : (
                  <PanelLeftClose className="h-3 w-3" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              {isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* Resize handle */}
      <OrgSidebarResizeHandle />
    </aside>
  );
}
