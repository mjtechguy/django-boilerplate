import { z } from "zod";

export const healthStatusSchema = z.enum(["healthy", "unhealthy", "degraded"]);
export type HealthStatus = z.infer<typeof healthStatusSchema>;

// Component health check result
export const componentHealthSchema = z.object({
  status: healthStatusSchema,
  latency_ms: z.number().optional(),
  error: z.string().optional(),
  note: z.string().optional(),
  details: z.record(z.string(), z.unknown()).optional(),
});

export type ComponentHealth = z.infer<typeof componentHealthSchema>;

// System Overview Response
export const systemOverviewSchema = z.object({
  timestamp: z.string(),
  overall_status: healthStatusSchema,
  components: z.object({
    database: componentHealthSchema,
    cache: componentHealthSchema,
    celery: componentHealthSchema,
    broker: componentHealthSchema,
    cerbos: componentHealthSchema,
  }),
  summary: z.object({
    healthy: z.number(),
    degraded: z.number(),
    unhealthy: z.number(),
  }),
  response_time_ms: z.number(),
});

export type SystemOverview = z.infer<typeof systemOverviewSchema>;

// Celery Worker Detail
export const workerDetailSchema = z.object({
  name: z.string(),
  status: z.string(),
  concurrency: z.number(),
  active_tasks: z.number(),
  pool_type: z.string(),
  prefetch: z.number(),
});

export type WorkerDetail = z.infer<typeof workerDetailSchema>;

// Celery Health Response
export const celeryHealthSchema = z.object({
  status: healthStatusSchema,
  active_workers: z.number(),
  workers: z.array(workerDetailSchema).optional(),
  error: z.string().optional(),
});

export type CeleryHealth = z.infer<typeof celeryHealthSchema>;

// Celery Worker Stats
export const workerStatsSchema = z.object({
  active: z.number(),
  reserved: z.number(),
  scheduled: z.number(),
  concurrency: z.number().optional(),
  pool_type: z.string().optional(),
  broker_transport: z.string().optional(),
  prefetch_count: z.number().optional(),
  registered_tasks: z.number().optional(),
});

export type WorkerStats = z.infer<typeof workerStatsSchema>;

// Celery Stats Response
export const celeryStatsSchema = z.object({
  workers: z.record(z.string(), workerStatsSchema),
  worker_count: z.number(),
  totals: z.object({
    active: z.number(),
    reserved: z.number(),
    scheduled: z.number(),
  }),
});

export type CeleryStats = z.infer<typeof celeryStatsSchema>;

// Queue Info
export const queueInfoSchema = z.object({
  messages: z.number(),
  consumers: z.number(),
  status: z.string().optional(),
});

export type QueueInfo = z.infer<typeof queueInfoSchema>;

// Queue Stats Response
export const queueStatsSchema = z.object({
  queues: z.record(z.string(), queueInfoSchema),
  active_queue_names: z.array(z.string()).optional(),
  queue_count: z.number(),
});

export type QueueStats = z.infer<typeof queueStatsSchema>;

// Server Metrics Response
export const serverMetricsSchema = z.object({
  server: z.object({
    hostname: z.string(),
    platform: z.string(),
    python_version: z.string(),
    uptime_seconds: z.number(),
  }),
  cpu: z.object({
    percent: z.number(),
    count: z.number(),
    load_avg_1m: z.number(),
    load_avg_5m: z.number(),
    load_avg_15m: z.number(),
  }),
  memory: z.object({
    total_gb: z.number(),
    available_gb: z.number(),
    used_gb: z.number(),
    percent: z.number(),
  }),
  disk: z.object({
    total_gb: z.number(),
    used_gb: z.number(),
    free_gb: z.number(),
    percent: z.number(),
  }),
  process: z.object({
    pid: z.number(),
    memory_mb: z.number(),
    threads: z.number(),
  }),
});

export type ServerMetrics = z.infer<typeof serverMetricsSchema>;

// App Metrics Response
export const appMetricsSchema = z.record(z.string(), z.unknown());

export type AppMetrics = z.infer<typeof appMetricsSchema>;

// Readiness Response (public endpoint)
export const readinessResponseSchema = z.object({
  status: z.string(),
  checks: z.record(z.string(), z.object({
    status: z.string(),
    error: z.string().optional(),
  })).optional(),
});

export type ReadinessResponse = z.infer<typeof readinessResponseSchema>;
