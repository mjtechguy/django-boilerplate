import { Link, useMatchRoute } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Building2,
  Users,
  Users2,
  Settings,
  Shield,
  FileText,
  Activity,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebarContext } from "./sidebar-context";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
}

const navItems: NavItem[] = [
  { title: "Dashboard", href: "/admin", icon: LayoutDashboard },
  { title: "Organizations", href: "/admin/organizations", icon: Building2 },
  { title: "Teams", href: "/admin/teams", icon: Users2 },
  { title: "Users", href: "/admin/users", icon: Users },
  { title: "Audit Logs", href: "/admin/audit", icon: FileText },
  { title: "Monitoring", href: "/admin/monitoring", icon: Activity },
  { title: "Policies", href: "/admin/policies", icon: Shield },
  { title: "Settings", href: "/admin/settings", icon: Settings },
];

export function SidebarNav() {
  const { isCollapsed } = useSidebarContext();
  const matchRoute = useMatchRoute();

  return (
    <TooltipProvider delayDuration={0}>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          // Use exact match for dashboard (/admin) to prevent it staying highlighted on other routes
          // Use fuzzy match for other routes to handle nested routes properly
          const isActive = item.href === "/admin"
            ? matchRoute({ to: item.href, fuzzy: false })
            : matchRoute({ to: item.href, fuzzy: true });
          const Icon = item.icon;

          const linkContent = (
            <Link
              to={item.href}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                "hover:bg-white/10",
                isActive
                  ? "bg-white/15 text-white shadow-sm"
                  : "text-slate-300 hover:text-white",
                isCollapsed && "justify-center px-2"
              )}
            >
              <Icon
                className={cn(
                  "h-5 w-5 shrink-0 transition-colors",
                  isActive ? "text-amber-400" : "text-slate-400 group-hover:text-slate-200"
                )}
              />
              {!isCollapsed && <span>{item.title}</span>}
            </Link>
          );

          if (isCollapsed) {
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                <TooltipContent side="right" className="font-medium">
                  {item.title}
                </TooltipContent>
              </Tooltip>
            );
          }

          return <div key={item.href}>{linkContent}</div>;
        })}
      </nav>
    </TooltipProvider>
  );
}
