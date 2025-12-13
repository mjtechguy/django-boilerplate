import { LogOut, Settings, User, ChevronDown } from "lucide-react";
import { useAuth, useUser } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useSidebarContext } from "./sidebar-context";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function SidebarUser() {
  const { isCollapsed } = useSidebarContext();
  const { logout } = useAuth();
  const user = useUser();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const trigger = (
    <DropdownMenuTrigger asChild>
      <button
        className={cn(
          "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-all duration-200",
          "hover:bg-sidebar-accent text-sidebar-foreground",
          isCollapsed && "justify-center px-2"
        )}
      >
        <Avatar className="h-8 w-8 shrink-0 border border-sidebar-border">
          <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
            {initials}
          </AvatarFallback>
        </Avatar>
        {!isCollapsed && (
          <>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </>
        )}
      </button>
    </DropdownMenuTrigger>
  );

  return (
    <div className="border-t border-sidebar-border p-3">
      <DropdownMenu>
        {isCollapsed ? (
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>{trigger}</TooltipTrigger>
              <TooltipContent side="right">
                <p className="font-medium">{user?.name}</p>
                <p className="text-xs opacity-70">{user?.email}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : (
          trigger
        )}
        <DropdownMenuContent
          side={isCollapsed ? "right" : "top"}
          align="start"
          className="w-56"
        >
          <DropdownMenuLabel>My Account</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <User className="mr-2 h-4 w-4" />
            Profile
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={logout}
            className="text-destructive focus:text-destructive"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
