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
import { useWebSocket } from "@/lib/websocket/ws-context";

export const Route = createFileRoute("/app/_layout/notifications/")({
  component: NotificationsPage,
});

/**
 * Format a timestamp as relative time (e.g., "5 min ago", "2 hours ago")
 */
function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) {
    return "Just now";
  } else if (diffMin < 60) {
    return `${diffMin} min ago`;
  } else if (diffHour < 24) {
    return `${diffHour} hour${diffHour === 1 ? "" : "s"} ago`;
  } else if (diffDay < 7) {
    return `${diffDay} day${diffDay === 1 ? "" : "s"} ago`;
  } else {
    return then.toLocaleDateString();
  }
}

interface UINotification {
  id: string;
  type: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
}

/**
 * Map WebSocket notification format to UI format
 */
function mapNotificationForUI(notification: {
  id: string;
  title: string;
  body: string;
  timestamp: string;
  read?: boolean;
}): UINotification {
  return {
    id: notification.id,
    type: "info", // Default type, can be enhanced later
    title: notification.title,
    message: notification.body,
    time: formatRelativeTime(notification.timestamp),
    read: notification.read ?? false,
  };
}

function NotificationsPage() {
  const { notifications, unreadCount, notificationStatus } = useWebSocket();

  // Map notifications from WebSocket format to UI format
  const uiNotifications = notifications.map(mapNotificationForUI);

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
          {uiNotifications.length} total
        </Badge>
        {unreadCount > 0 && (
          <Badge
            variant="default"
            className="bg-primary/10 text-primary hover:bg-primary/20"
          >
            {unreadCount} unread
          </Badge>
        )}
      </div>

      {/* Notifications List */}
      <Card>
        <CardContent className="p-0 divide-y">
          {uiNotifications.map((notification) => (
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
  notification: UINotification;
}

function NotificationItem({ notification }: NotificationItemProps) {
  const typeConfig = {
    info: {
      icon: Info,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    warning: {
      icon: AlertTriangle,
      color: "text-yellow-600 dark:text-yellow-500",
      bg: "bg-yellow-500/10",
    },
    success: {
      icon: Check,
      color: "text-green-600 dark:text-green-500",
      bg: "bg-green-500/10",
    },
    error: {
      icon: AlertCircle,
      color: "text-destructive",
      bg: "bg-destructive/10",
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
            <div className="h-2 w-2 rounded-full bg-primary shrink-0 mt-2" />
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
