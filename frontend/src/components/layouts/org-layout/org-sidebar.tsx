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
        "bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950",
        "border-r border-white/5",
        "transition-[width] duration-300 ease-in-out",
        isCollapsed && "w-16"
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          "flex h-16 items-center border-b border-white/10 px-4",
          isCollapsed && "justify-center px-2"
        )}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/20">
            <Building2 className="h-5 w-5 text-white" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-white">Org Admin</span>
              <span className="text-[10px] text-slate-400 uppercase tracking-wider">
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
                className="h-6 w-6 rounded-full border-slate-700 bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white shadow-lg"
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
