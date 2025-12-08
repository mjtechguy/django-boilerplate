import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../client";
import { queryKeys } from "../query-keys";
import type {
  AppMetrics,
  CeleryHealth,
  CeleryStats,
  QueueStats,
  ReadinessResponse,
  ServerMetrics,
  SystemOverview,
} from "./types";

export function useSystemOverview() {
  return useQuery({
    queryKey: queryKeys.monitoring.overview,
    queryFn: () => apiGet<SystemOverview>("monitoring/overview"),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  });
}

// Public endpoint for dashboard - no auth required
export function useReadiness() {
  return useQuery({
    queryKey: queryKeys.monitoring.health,
    queryFn: () => apiGet<ReadinessResponse>("health/ready"),
    refetchInterval: 60000,
    retry: 1,
  });
}

export function useAppMetrics() {
  return useQuery({
    queryKey: queryKeys.monitoring.metrics,
    queryFn: () => apiGet<AppMetrics>("monitoring/metrics/json"),
    refetchInterval: 60000,
    retry: 1,
  });
}

export function useServerMetrics() {
  return useQuery({
    queryKey: queryKeys.monitoring.server,
    queryFn: () => apiGet<ServerMetrics>("monitoring/server"),
    refetchInterval: 15000, // Refresh every 15 seconds
    retry: 1,
  });
}

export function useCeleryHealth() {
  return useQuery({
    queryKey: queryKeys.monitoring.celeryHealth,
    queryFn: () => apiGet<CeleryHealth>("monitoring/celery/health"),
    refetchInterval: 30000,
    retry: 1,
  });
}

export function useCeleryStats() {
  return useQuery({
    queryKey: queryKeys.monitoring.celeryStats,
    queryFn: () => apiGet<CeleryStats>("monitoring/celery/stats"),
    refetchInterval: 30000,
    retry: 1,
  });
}

export function useQueueStats() {
  return useQuery({
    queryKey: queryKeys.monitoring.queues,
    queryFn: () => apiGet<QueueStats>("monitoring/queues"),
    refetchInterval: 30000,
    retry: 1,
  });
}
