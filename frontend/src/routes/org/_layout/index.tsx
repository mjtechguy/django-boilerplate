import { createFileRoute } from "@tanstack/react-router";
import {
  UsersRound,
  Users,
  Activity,
  CreditCard,
  TrendingUp,
  Calendar,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/org/_layout/")({
  component: OrgDashboard,
});

function OrgDashboard() {
  // TODO: Replace with actual API calls
  const isLoading = false;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organization Dashboard"
        description="Overview of your organization's activity and resources"
      />

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Teams"
          value={8}
          icon={UsersRound}
          isLoading={isLoading}
          trend="+2"
        />
        <StatCard
          title="Active Members"
          value={47}
          icon={Users}
          isLoading={isLoading}
          trend="+5"
        />
        <StatCard
          title="API Usage (30d)"
          value={12450}
          icon={Activity}
          isLoading={isLoading}
          format="number"
        />
        <StatCard
          title="License Status"
          value="Active"
          icon={CreditCard}
          isLoading={isLoading}
          variant="success"
        />
      </div>

      {/* Activity & Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <ActivityItem
                action="User invited"
                description="john.doe@example.com was invited to Engineering"
                time="2 hours ago"
              />
              <ActivityItem
                action="Team created"
                description="New team 'Marketing' was created"
                time="Yesterday"
              />
              <ActivityItem
                action="Webhook configured"
                description="Slack integration webhook added"
                time="2 days ago"
              />
              <ActivityItem
                action="Settings updated"
                description="Organization name was changed"
                time="1 week ago"
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Calendar className="h-5 w-5" />
              Upcoming
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <UpcomingItem
                title="License Renewal"
                date="Dec 31, 2025"
                status="info"
              />
              <UpcomingItem
                title="Security Review"
                date="Jan 15, 2026"
                status="warning"
              />
              <UpcomingItem
                title="Quarterly Audit"
                date="Mar 1, 2026"
                status="default"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ElementType;
  isLoading: boolean;
  trend?: string;
  format?: "number" | "default";
  variant?: "default" | "success";
}

function StatCard({
  title,
  value,
  icon: Icon,
  isLoading,
  trend,
  format = "default",
  variant = "default",
}: StatCardProps) {
  const formattedValue =
    typeof value === "number" && format === "number"
      ? value.toLocaleString()
      : value.toString();

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {isLoading ? (
              <Skeleton className="mt-1 h-8 w-20" />
            ) : (
              <p
                className={`text-2xl font-bold ${variant === "success" ? "text-emerald-600" : ""}`}
              >
                {formattedValue}
              </p>
            )}
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
        {trend && (
          <div className="mt-2 flex items-center gap-1 text-sm text-emerald-600">
            <TrendingUp className="h-3 w-3" />
            {trend} this month
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface ActivityItemProps {
  action: string;
  description: string;
  time: string;
}

function ActivityItem({ action, description, time }: ActivityItemProps) {
  return (
    <div className="flex items-start gap-3">
      <div className="h-2 w-2 mt-2 rounded-full bg-emerald-500 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{action}</p>
        <p className="text-sm text-muted-foreground truncate">{description}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{time}</p>
      </div>
    </div>
  );
}

interface UpcomingItemProps {
  title: string;
  date: string;
  status: "info" | "warning" | "default";
}

function UpcomingItem({ title, date, status }: UpcomingItemProps) {
  const statusVariants = {
    info: "secondary",
    warning: "outline",
    default: "secondary",
  } as const;

  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{date}</p>
      </div>
      <Badge variant={statusVariants[status]} className="shrink-0">
        {status === "warning" ? "Action needed" : "Scheduled"}
      </Badge>
    </div>
  );
}
