import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  Server,
  Database,
  RefreshCw,
  HardDrive,
  Cpu,
  MemoryStick,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  useSystemOverview,
  useServerMetrics,
  useCeleryStats,
  useQueueStats,
} from "@/lib/api/monitoring";
import type { HealthStatus, ComponentHealth } from "@/lib/api/monitoring";

export const Route = createFileRoute("/admin/_layout/monitoring/")({
  component: MonitoringPage,
});

function StatusIcon({ status }: { status: HealthStatus }) {
  switch (status) {
    case "healthy":
      return <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-500" />;
    case "degraded":
      return <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-500" />;
    case "unhealthy":
      return <AlertCircle className="h-5 w-5 text-destructive" />;
  }
}

function StatusBadge({ status }: { status: HealthStatus }) {
  const variants: Record<HealthStatus, "default" | "secondary" | "destructive"> = {
    healthy: "default",
    degraded: "secondary",
    unhealthy: "destructive",
  };

  return (
    <Badge variant={variants[status]} className="capitalize">
      {status}
    </Badge>
  );
}

function ComponentCard({
  name,
  component,
  icon: Icon,
}: {
  name: string;
  component: ComponentHealth;
  icon: React.ElementType;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <div className="flex items-center gap-2">
            <Icon className="h-4 w-4" />
            {name}
          </div>
          <StatusIcon status={component.status} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <StatusBadge status={component.status} />
          {component.latency_ms !== undefined && (
            <span className="text-sm text-muted-foreground">
              {component.latency_ms}ms
            </span>
          )}
        </div>
        {component.error && (
          <p className="text-sm text-destructive">{component.error}</p>
        )}
        {component.details && (
          <div className="space-y-1 text-sm">
            {Object.entries(component.details).map(([key, value]) => (
              <div key={key} className="flex justify-between">
                <span className="text-muted-foreground capitalize">
                  {key.replace(/_/g, " ")}
                </span>
                <span className="font-mono">{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function MonitoringPage() {
  const {
    data: overview,
    isLoading: overviewLoading,
    refetch: refetchOverview,
    error: overviewError,
  } = useSystemOverview();

  const {
    data: server,
    isLoading: serverLoading,
    refetch: refetchServer,
  } = useServerMetrics();

  const {
    data: celeryStats,
    isLoading: celeryLoading,
    refetch: refetchCelery,
  } = useCeleryStats();

  const {
    data: queueStats,
    isLoading: queuesLoading,
    refetch: refetchQueues,
  } = useQueueStats();

  const handleRefresh = () => {
    refetchOverview();
    refetchServer();
    refetchCelery();
    refetchQueues();
  };

  const isLoading = overviewLoading || serverLoading;

  // Handle auth error
  if (overviewError) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="System Monitoring"
          description="Monitor system health, workers, and resources"
        />
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
            <p className="text-muted-foreground text-center max-w-md">
              You need platform administrator privileges to view system monitoring data.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Monitoring"
        description="Monitor system health, workers, and resources"
        actions={
          <Button variant="outline" onClick={handleRefresh} disabled={isLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        }
      />

      {/* Overall Status Banner */}
      {overviewLoading ? (
        <Skeleton className="h-20 w-full" />
      ) : overview ? (
        <Card
          className={`border-2 ${
            overview.overall_status === "healthy"
              ? "border-green-500/50 bg-green-500/5"
              : overview.overall_status === "degraded"
                ? "border-yellow-500/50 bg-yellow-500/5"
                : "border-destructive/50 bg-destructive/5"
          }`}
        >
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-4">
              <StatusIcon status={overview.overall_status} />
              <div>
                <h3 className="text-lg font-semibold capitalize">
                  System {overview.overall_status}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {overview.summary.healthy} healthy, {overview.summary.degraded} degraded,{" "}
                  {overview.summary.unhealthy} unhealthy
                </p>
              </div>
            </div>
            <div className="text-right text-sm text-muted-foreground">
              <div>Response: {overview.response_time_ms}ms</div>
              <div>
                Last check:{" "}
                {new Date(overview.timestamp).toLocaleTimeString()}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Component Health Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {overviewLoading ? (
          <>
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
          </>
        ) : overview ? (
          <>
            <ComponentCard
              name="Database"
              component={overview.components.database}
              icon={Database}
            />
            <ComponentCard
              name="Cache (Redis)"
              component={overview.components.cache}
              icon={Database}
            />
            <ComponentCard
              name="Celery Workers"
              component={overview.components.celery}
              icon={Server}
            />
            <ComponentCard
              name="Message Broker"
              component={overview.components.broker}
              icon={Activity}
            />
            <ComponentCard
              name="Cerbos (Auth)"
              component={overview.components.cerbos}
              icon={Activity}
            />
          </>
        ) : null}
      </div>

      {/* Server Resources */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {serverLoading ? (
          <>
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
            <Skeleton className="h-32" />
          </>
        ) : server ? (
          <>
            {/* Server Info */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Server className="h-4 w-4" />
                  Server
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Hostname</span>
                  <span className="font-mono truncate max-w-[120px]">
                    {server.server.hostname}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Platform</span>
                  <span>{server.server.platform}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Python</span>
                  <span>{server.server.python_version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Uptime</span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatUptime(server.server.uptime_seconds)}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* CPU */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Cpu className="h-4 w-4" />
                  CPU
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">{server.cpu.percent}%</span>
                  <span className="text-sm text-muted-foreground">
                    {server.cpu.count} cores
                  </span>
                </div>
                <Progress value={server.cpu.percent} className="h-2" />
                <div className="text-xs text-muted-foreground">
                  Load: {server.cpu.load_avg_1m} / {server.cpu.load_avg_5m} /{" "}
                  {server.cpu.load_avg_15m}
                </div>
              </CardContent>
            </Card>

            {/* Memory */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <MemoryStick className="h-4 w-4" />
                  Memory
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">{server.memory.percent}%</span>
                  <span className="text-sm text-muted-foreground">
                    {server.memory.used_gb}GB / {server.memory.total_gb}GB
                  </span>
                </div>
                <Progress
                  value={server.memory.percent}
                  className={`h-2 ${server.memory.percent > 90 ? "[&>div]:bg-destructive" : ""}`}
                />
                <div className="text-xs text-muted-foreground">
                  Available: {server.memory.available_gb}GB
                </div>
              </CardContent>
            </Card>

            {/* Disk */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-base">
                  <HardDrive className="h-4 w-4" />
                  Disk
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold">{server.disk.percent}%</span>
                  <span className="text-sm text-muted-foreground">
                    {server.disk.used_gb}GB / {server.disk.total_gb}GB
                  </span>
                </div>
                <Progress
                  value={server.disk.percent}
                  className={`h-2 ${server.disk.percent > 90 ? "[&>div]:bg-destructive" : ""}`}
                />
                <div className="text-xs text-muted-foreground">
                  Free: {server.disk.free_gb}GB
                </div>
              </CardContent>
            </Card>
          </>
        ) : null}
      </div>

      {/* Worker & Queue Details */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Worker Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Celery Workers
            </CardTitle>
          </CardHeader>
          <CardContent>
            {celeryLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : celeryStats?.workers && Object.keys(celeryStats.workers).length > 0 ? (
              <div className="space-y-4">
                {/* Totals */}
                <div className="grid grid-cols-3 gap-4 pb-4 border-b">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600 dark:text-green-500">
                      {celeryStats.totals.active}
                    </p>
                    <p className="text-xs text-muted-foreground">Active</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-500">
                      {celeryStats.totals.reserved}
                    </p>
                    <p className="text-xs text-muted-foreground">Reserved</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-primary">
                      {celeryStats.totals.scheduled}
                    </p>
                    <p className="text-xs text-muted-foreground">Scheduled</p>
                  </div>
                </div>

                {/* Worker List */}
                <div className="space-y-3">
                  {Object.entries(celeryStats.workers).map(([name, stats]) => (
                    <div key={name} className="p-3 rounded-lg border bg-muted/30">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-sm truncate max-w-[200px]" title={name}>
                          {name.split("@")[1] || name}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {stats.concurrency} slots
                        </Badge>
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-xs">
                        <span>Active: {stats.active}</span>
                        <span>Reserved: {stats.reserved}</span>
                        <span>Tasks: {stats.registered_tasks}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No workers available
              </p>
            )}
          </CardContent>
        </Card>

        {/* Queue Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Message Queues
            </CardTitle>
          </CardHeader>
          <CardContent>
            {queuesLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : queueStats?.queues && Object.keys(queueStats.queues).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(queueStats.queues).map(([name, stats]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between p-3 rounded-lg border bg-muted/30"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          stats.consumers > 0 ? "bg-green-500" : "bg-yellow-500"
                        }`}
                      />
                      <span className="font-medium">{name}</span>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">
                        {stats.messages} msgs
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {stats.consumers} consumers
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-center py-8">
                No queues found
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Process Info */}
      {server && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Process Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">PID</span>
                <span className="font-mono">{server.process.pid}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Memory Usage</span>
                <span className="font-mono">{server.process.memory_mb} MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Threads</span>
                <span className="font-mono">{server.process.threads}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
