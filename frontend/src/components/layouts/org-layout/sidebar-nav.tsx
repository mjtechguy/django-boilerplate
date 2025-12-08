import { Link, useMatchRoute } from "@tanstack/react-router";
import {
  LayoutDashboard,
  Users,
  UsersRound,
  Settings,
  CreditCard,
  FileText,
  Webhook,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrgSidebarContext } from "./sidebar-context";
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
  { title: "Dashboard", href: "/org", icon: LayoutDashboard },
  { title: "Teams", href: "/org/teams", icon: UsersRound },
  { title: "Users", href: "/org/users", icon: Users },
  { title: "Billing", href: "/org/billing", icon: CreditCard },
  { title: "Audit Logs", href: "/org/audit", icon: FileText },
  { title: "Webhooks", href: "/org/webhooks", icon: Webhook },
  { title: "Settings", href: "/org/settings", icon: Settings },
];

export function OrgSidebarNav() {
  const { isCollapsed } = useOrgSidebarContext();
  const matchRoute = useMatchRoute();

  return (
    <TooltipProvider delayDuration={0}>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = matchRoute({ to: item.href, fuzzy: true });
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
                  isActive ? "text-emerald-400" : "text-slate-400 group-hover:text-slate-200"
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
