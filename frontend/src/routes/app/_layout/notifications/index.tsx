import { createFileRoute } from "@tanstack/react-router";
import {
  Bell,
  Check,
  CheckCheck,
  Info,
  AlertTriangle,
  AlertCircle,
  Settings,
  Trash2,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/app/_layout/notifications/")({
  component: NotificationsPage,
});

// Mock data - replace with API calls
const notifications = [
  {
    id: "1",
    type: "info",
    title: "Welcome to the platform!",
    message: "Thanks for joining. Get started by completing your profile.",
    time: "Just now",
    read: false,
  },
  {
    id: "2",
    type: "warning",
    title: "Profile incomplete",
    message:
      "Complete your profile to unlock all features and improve your experience.",
    time: "5 min ago",
    read: false,
  },
  {
    id: "3",
    type: "success",
    title: "Email verified",
    message: "Your email address has been successfully verified.",
    time: "1 hour ago",
    read: true,
  },
  {
    id: "4",
    type: "info",
    title: "New login detected",
    message: "A new login was detected from Chrome on macOS.",
    time: "2 hours ago",
    read: true,
  },
  {
    id: "5",
    type: "info",
    title: "Security tip",
    message:
      "Enable two-factor authentication for enhanced security on your account.",
    time: "Yesterday",
    read: true,
  },
];

function NotificationsPage() {
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Notifications"
        description="Stay updated with your latest activity"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <CheckCheck className="mr-2 h-4 w-4" />
              Mark all read
            </Button>
            <Button variant="outline" size="sm">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </div>
        }
      />

      {/* Stats */}
      <div className="flex items-center gap-4">
        <Badge variant="secondary" className="text-sm">
          <Bell className="mr-1 h-3 w-3" />
          {notifications.length} total
        </Badge>
        {unreadCount > 0 && (
          <Badge
            variant="default"
            className="bg-blue-500/10 text-blue-600 hover:bg-blue-500/20"
          >
            {unreadCount} unread
          </Badge>
        )}
      </div>

      {/* Notifications List */}
      <Card>
        <CardContent className="p-0 divide-y">
          {notifications.map((notification) => (
            <NotificationItem key={notification.id} notification={notification} />
          ))}
        </CardContent>
      </Card>

      {/* Load More */}
      <div className="flex justify-center">
        <Button variant="outline">Load More</Button>
      </div>
    </div>
  );
}

interface NotificationItemProps {
  notification: {
    id: string;
    type: string;
    title: string;
    message: string;
    time: string;
    read: boolean;
  };
}

function NotificationItem({ notification }: NotificationItemProps) {
  const typeConfig = {
    info: {
      icon: Info,
      color: "text-blue-600",
      bg: "bg-blue-500/10",
    },
    warning: {
      icon: AlertTriangle,
      color: "text-amber-600",
      bg: "bg-amber-500/10",
    },
    success: {
      icon: Check,
      color: "text-emerald-600",
      bg: "bg-emerald-500/10",
    },
    error: {
      icon: AlertCircle,
      color: "text-red-600",
      bg: "bg-red-500/10",
    },
  };

  const config = typeConfig[notification.type as keyof typeof typeConfig] || typeConfig.info;
  const Icon = config.icon;

  return (
    <div
      className={`flex items-start gap-4 p-4 ${
        !notification.read ? "bg-accent/30" : ""
      }`}
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${config.bg}`}
      >
        <Icon className={`h-5 w-5 ${config.color}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className={`font-medium ${!notification.read ? "" : "text-muted-foreground"}`}>
              {notification.title}
            </p>
            <p className="text-sm text-muted-foreground mt-0.5">
              {notification.message}
            </p>
          </div>
          {!notification.read && (
            <div className="h-2 w-2 rounded-full bg-blue-500 shrink-0 mt-2" />
          )}
        </div>
        <div className="flex items-center gap-3 mt-2">
          <span className="text-xs text-muted-foreground">{notification.time}</span>
          {!notification.read && (
            <Button variant="ghost" size="sm" className="h-6 text-xs">
              Mark as read
            </Button>
          )}
        </div>
      </div>
      <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0">
        <Trash2 className="h-4 w-4 text-muted-foreground" />
      </Button>
    </div>
  );
}
