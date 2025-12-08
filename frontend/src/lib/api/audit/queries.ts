import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../client";
import { queryKeys } from "../query-keys";
import type {
  AuditLogsResponse,
  AuditFilters,
  AuditVerifyResponse,
  AuditChainVerifyResponse,
} from "./types";

export function useAuditLogs(filters?: AuditFilters) {
  return useQuery({
    queryKey: queryKeys.audit.list(filters as Record<string, unknown>),
    queryFn: () => {
      const searchParams: Record<string, string> = {};
      if (filters) {
        Object.entries(filters).forEach(([key, value]) => {
          if (value !== undefined) {
            searchParams[key] = String(value);
          }
        });
      }
      return apiGet<AuditLogsResponse>("audit", { searchParams });
    },
  });
}

export function useVerifyAuditLog(logId: string) {
  return useQuery({
    queryKey: queryKeys.audit.verify(logId),
    queryFn: () =>
      apiGet<AuditVerifyResponse>("audit/verify", {
        searchParams: { id: logId },
      }),
    enabled: !!logId,
  });
}

export function useVerifyAuditChain() {
  return useQuery({
    queryKey: queryKeys.audit.chainVerify(),
    queryFn: () => apiGet<AuditChainVerifyResponse>("audit/chain-verify"),
    enabled: false, // Only run when explicitly triggered
  });
}

export function getAuditExportUrl(filters?: AuditFilters): string {
  const baseUrl = `${import.meta.env.VITE_API_URL || ""}/api/v1/audit/export`;
  if (!filters) return baseUrl;

  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) {
      params.set(key, String(value));
    }
  });

  return `${baseUrl}?${params.toString()}`;
}
