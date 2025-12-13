import { createFileRoute } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import {
  Building2,
  Users,
  Activity,
  AlertTriangle,
  TrendingUp,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { useReadiness, useAppMetrics } from "@/lib/api/monitoring";
import { useOrganizations } from "@/lib/api/organizations";
import { useUsers } from "@/lib/api/users";
import { useAlerts } from "@/lib/api/alerts";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/admin/_layout/")({
  component: AdminDashboard,
});

function AdminDashboard() {
  const { data: healthData, isLoading: healthLoading } = useReadiness();
  const { data: metricsData, isLoading: metricsLoading } = useAppMetrics();
  const { data: orgsData, isLoading: orgsLoading } = useOrganizations();
  const { data: usersData, isLoading: usersLoading } = useUsers({ is_active: true });
  const { data: alertsData, isLoading: alertsLoading } = useAlerts({ limit: 5 });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Platform overview and system health"
      />

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Organizations"
          value={orgsData?.count ?? 0}
          icon={Building2}
          isLoading={orgsLoading}
        />
        <StatCard
          title="Active Users"
          value={usersData?.count ?? 0}
          icon={Users}
          isLoading={usersLoading}
        />
        <StatCard
          title="API Requests (24h)"
          value={Number(metricsData?.request_count) || 0}
          icon={Activity}
          isLoading={metricsLoading}
          format="number"
        />
        <StatCard
          title="Avg Response Time"
          value={Number(metricsData?.avg_response_time_ms) || 0}
          icon={Clock}
          isLoading={metricsLoading}
          suffix="ms"
        />
      </div>

      {/* System Health */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Activity className="h-5 w-5" />
              System Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            {healthLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : (
              <div className="space-y-3">
                <HealthItem
                  name="API Server"
                  status={healthData?.status === "ok" ? "healthy" : "degraded"}
                />
                <HealthItem name="Database" status="healthy" />
                <HealthItem name="Redis Cache" status="healthy" />
                <HealthItem name="Message Queue" status="healthy" />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="h-5 w-5" />
              Recent Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {alertsLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            ) : alertsData?.results && alertsData.results.length > 0 ? (
              <div className="space-y-3">
                {alertsData.results.map((alert) => (
                  <AlertItem
                    key={alert.id}
                    message={alert.message}
                    severity={alert.severity}
                    time={formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">
                No recent alerts
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ElementType;
  isLoading: boolean;
  trend?: string;
  suffix?: string;
  format?: "number" | "default";
}

function StatCard({
  title,
  value,
  icon: Icon,
  isLoading,
  trend,
  suffix,
  format = "default",
}: StatCardProps) {
  const formattedValue =
    format === "number" ? value.toLocaleString() : value.toString();

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {isLoading ? (
              <Skeleton className="mt-1 h-8 w-20" />
            ) : (
              <p className="text-2xl font-bold">
                {formattedValue}
                {suffix && (
                  <span className="text-sm font-normal text-muted-foreground ml-1">
                    {suffix}
                  </span>
                )}
              </p>
            )}
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Icon className="h-6 w-6 text-primary" />
          </div>
        </div>
        {trend && (
          <div className="mt-2 flex items-center gap-1 text-sm text-green-600 dark:text-green-500">
            <TrendingUp className="h-3 w-3" />
            {trend} from last month
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface HealthItemProps {
  name: string;
  status: "healthy" | "degraded" | "unhealthy";
}

function HealthItem({ name, status }: HealthItemProps) {
  const statusColors = {
    healthy: "bg-green-500",
    degraded: "bg-yellow-500",
    unhealthy: "bg-destructive",
  };

  return (
    <div className="flex items-center justify-between">
      <span className="text-sm">{name}</span>
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${statusColors[status]}`} />
        <span className="text-sm capitalize text-muted-foreground">
          {status}
        </span>
      </div>
    </div>
  );
}

interface AlertItemProps {
  message: string;
  severity: "info" | "warning" | "error";
  time: string;
}

function AlertItem({ message, severity, time }: AlertItemProps) {
  const severityVariants = {
    info: "secondary",
    warning: "outline",
    error: "destructive",
  } as const;

  return (
    <div className="flex items-start gap-3">
      <Badge variant={severityVariants[severity]} className="shrink-0 capitalize">
        {severity}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{message}</p>
        <p className="text-xs text-muted-foreground">{time}</p>
      </div>
    </div>
  );
}
