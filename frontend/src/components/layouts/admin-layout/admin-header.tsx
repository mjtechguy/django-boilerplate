import { ThemeToggle } from "@/components/shared/theme-toggle";
import {
  HeaderShell,
  HeaderSearch,
  HeaderActions,
  NotificationDropdown,
} from "@/components/shared/header";

const adminNotifications = [
  {
    title: "New organization created",
    description: "Acme Corp was added 5 minutes ago",
  },
  {
    title: "License expiring soon",
    description: "TechStart license expires in 7 days",
  },
  {
    title: "System health warning",
    description: "High queue depth detected",
  },
];

export function AdminHeader() {
  return (
    <HeaderShell
      leftContent={
        <div className="flex items-center gap-4 flex-1 max-w-xl">
          <HeaderSearch placeholder="Search organizations, users..." />
        </div>
      }
      rightContent={
        <HeaderActions>
          <ThemeToggle />
          <NotificationDropdown notifications={adminNotifications} />
        </HeaderActions>
      }
    />
  );
}
