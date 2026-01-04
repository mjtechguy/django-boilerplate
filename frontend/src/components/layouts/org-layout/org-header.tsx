import { Building2 } from "lucide-react";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import {
  HeaderShell,
  HeaderSearch,
  HeaderActions,
  NotificationDropdown,
} from "@/components/shared/header";

const orgNotifications = [
  {
    title: "New team member joined",
    description: "John Doe joined Engineering team",
  },
  {
    title: "Billing update",
    description: "Your subscription renews in 7 days",
  },
];

export function OrgHeader() {
  return (
    <HeaderShell
      leftContent={
        <div className="flex items-center gap-4 flex-1 max-w-xl">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Building2 className="h-4 w-4" />
            <span className="text-sm font-medium">Acme Corp</span>
          </div>
          <HeaderSearch placeholder="Search teams, users..." />
        </div>
      }
      rightContent={
        <HeaderActions>
          <ThemeToggle />
          <NotificationDropdown notifications={orgNotifications} />
        </HeaderActions>
      }
    />
  );
}
