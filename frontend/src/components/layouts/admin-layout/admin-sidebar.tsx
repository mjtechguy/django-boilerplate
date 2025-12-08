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
        "bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950",
        "border-r border-white/5",
        "transition-[width] duration-300 ease-in-out",
        "shadow-xl shadow-black/20"
      )}
    >
      {/* Subtle texture overlay */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCI+CjxyZWN0IHdpZHRoPSI2MCIgaGVpZ2h0PSI2MCIgZmlsbD0idHJhbnNwYXJlbnQiPjwvcmVjdD4KPGNpcmNsZSBjeD0iMzAiIGN5PSIzMCIgcj0iMSIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjAyKSI+PC9jaXJjbGU+Cjwvc3ZnPg==')] opacity-50 pointer-events-none" />

      {/* Logo / Brand */}
      <div className="relative flex h-16 items-center justify-between border-b border-white/5 px-4">
        <div
          className={cn(
            "flex items-center gap-3 overflow-hidden transition-all duration-300",
            isCollapsed && "w-0 opacity-0"
          )}
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25">
            <span className="text-sm font-bold text-white">A</span>
          </div>
          <span className="text-lg font-semibold text-white tracking-tight whitespace-nowrap">
            Admin Portal
          </span>
        </div>

        {isCollapsed && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25 mx-auto">
            <span className="text-sm font-bold text-white">A</span>
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
                  className="h-8 w-8 shrink-0 text-slate-400 hover:text-white hover:bg-white/10"
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
                  className="w-full h-9 text-slate-400 hover:text-white hover:bg-white/10"
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
