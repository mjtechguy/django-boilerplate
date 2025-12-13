import { createFileRoute } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import {
  Activity,
  Bell,
  User,
  ArrowRight,
  CheckCircle2,
  Clock,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/shared/page-header";
import { useUser } from "@/lib/auth";

export const Route = createFileRoute("/app/_layout/")({
  component: AppDashboard,
});

function AppDashboard() {
  const user = useUser();
  const firstName = user?.name?.split(" ")[0] || "User";

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${firstName}`}
        description="Here's what's happening with your account"
      />

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <QuickStatCard
          title="Profile Completion"
          value="75%"
          icon={User}
          status="warning"
          description="Complete your profile"
        />
        <QuickStatCard
          title="Active Sessions"
          value="2"
          icon={Activity}
          status="success"
          description="devices connected"
        />
        <QuickStatCard
          title="Notifications"
          value="3"
          icon={Bell}
          status="info"
          description="unread messages"
        />
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-3">
            <QuickActionCard
              title="View Profile"
              description="View and edit your profile information"
              href="/app/profile"
            />
            <QuickActionCard
              title="Notifications"
              description="Check your latest notifications"
              href="/app/notifications"
            />
            <QuickActionCard
              title="Security"
              description="Manage your security settings"
              href="/app/profile"
            />
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <ActivityItem
              title="Login from new device"
              description="Chrome on macOS"
              time="2 hours ago"
              status="info"
            />
            <ActivityItem
              title="Profile updated"
              description="Changed display name"
              time="Yesterday"
              status="success"
            />
            <ActivityItem
              title="Password changed"
              description="Password was updated successfully"
              time="3 days ago"
              status="success"
            />
            <ActivityItem
              title="Email verified"
              description="Email address was verified"
              time="1 week ago"
              status="success"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface QuickStatCardProps {
  title: string;
  value: string;
  icon: React.ElementType;
  status: "success" | "warning" | "info";
  description: string;
}

function QuickStatCard({
  title,
  value,
  icon: Icon,
  status,
  description,
}: QuickStatCardProps) {
  const statusColors = {
    success: "text-green-600 dark:text-green-500",
    warning: "text-yellow-600 dark:text-yellow-500",
    info: "text-primary",
  };

  const bgColors = {
    success: "bg-green-500/10",
    warning: "bg-yellow-500/10",
    info: "bg-primary/10",
  };

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className={`text-2xl font-bold ${statusColors[status]}`}>
              {value}
            </p>
            <p className="text-xs text-muted-foreground mt-1">{description}</p>
          </div>
          <div
            className={`flex h-12 w-12 items-center justify-center rounded-full ${bgColors[status]}`}
          >
            <Icon className={`h-6 w-6 ${statusColors[status]}`} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface QuickActionCardProps {
  title: string;
  description: string;
  href: string;
}

function QuickActionCard({ title, description, href }: QuickActionCardProps) {
  return (
    <Link to={href} className="block">
      <div className="group rounded-lg border p-4 hover:border-primary/50 hover:bg-accent/50 transition-colors">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">{title}</p>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
        </div>
      </div>
    </Link>
  );
}

interface ActivityItemProps {
  title: string;
  description: string;
  time: string;
  status: "success" | "info";
}

function ActivityItem({ title, description, time, status }: ActivityItemProps) {
  return (
    <div className="flex items-start gap-3">
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          status === "success" ? "bg-green-500/10" : "bg-primary/10"
        }`}
      >
        <CheckCircle2
          className={`h-4 w-4 ${
            status === "success" ? "text-green-600 dark:text-green-500" : "text-primary"
          }`}
        />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {time}
      </span>
    </div>
  );
}
