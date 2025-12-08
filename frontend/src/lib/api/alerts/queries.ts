import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../client";
import { queryKeys } from "../query-keys";
import type { AlertsResponse } from "./types";

export interface AlertsParams {
  limit?: number;
  hours?: number;
}

export function useAlerts(params?: AlertsParams) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.hours) searchParams.set("hours", String(params.hours));

  const queryString = searchParams.toString();
  const endpoint = queryString ? `admin/alerts?${queryString}` : "admin/alerts";

  return useQuery({
    queryKey: queryKeys.alerts.list(params),
    queryFn: () => apiGet<AlertsResponse>(endpoint),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 1,
  });
}
