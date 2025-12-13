import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  Division,
  DivisionsResponse,
  CreateDivisionInput,
  UpdateDivisionInput,
} from "./types";
import type { TeamListItem } from "../teams/types";

interface DivisionsQueryParams {
  search?: string;
  billing_mode?: string;
  license_tier?: string;
  limit?: number;
  offset?: number;
}

// Fetch all divisions (admin only)
export function useDivisions(params?: DivisionsQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.billing_mode) searchParams.set("billing_mode", params.billing_mode);
  if (params?.license_tier) searchParams.set("license_tier", params.license_tier);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString
    ? `admin/divisions/?${queryString}`
    : "admin/divisions/";

  return useQuery({
    queryKey: queryKeys.divisions.list(undefined, params as Record<string, unknown>),
    queryFn: () => apiGet<DivisionsResponse>(url),
  });
}

// Fetch divisions for a specific org
export function useOrgDivisions(orgId: string, params?: DivisionsQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.billing_mode) searchParams.set("billing_mode", params.billing_mode);
  if (params?.license_tier) searchParams.set("license_tier", params.license_tier);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString
    ? `orgs/${orgId}/divisions?${queryString}`
    : `orgs/${orgId}/divisions`;

  return useQuery({
    queryKey: queryKeys.divisions.list(orgId, params as Record<string, unknown>),
    queryFn: () => apiGet<DivisionsResponse>(url),
    enabled: !!orgId,
  });
}

// Fetch single division
export function useDivision(divisionId: string) {
  return useQuery({
    queryKey: queryKeys.divisions.detail(divisionId),
    queryFn: () => apiGet<Division>(`divisions/${divisionId}`),
    enabled: !!divisionId,
  });
}

// Create division for an org
export function useCreateDivision(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDivisionInput) =>
      apiPost<Division>(`orgs/${orgId}/divisions`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
      queryClient.invalidateQueries({
        queryKey: queryKeys.divisions.byOrg(orgId),
      });
    },
  });
}

// Update division
export function useUpdateDivision(divisionId: string, orgId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateDivisionInput) =>
      apiPut<Division>(`divisions/${divisionId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.divisions.detail(divisionId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
      if (orgId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.divisions.byOrg(orgId),
        });
      }
    },
  });
}

// Delete division
export function useDeleteDivision(orgId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (divisionId: string) =>
      apiDelete<{ message: string; division_id: string }>(
        `divisions/${divisionId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
      if (orgId) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.divisions.byOrg(orgId),
        });
      }
    },
  });
}

// Admin: Create division (platform admin only)
export function useAdminCreateDivision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDivisionInput) =>
      apiPost<Division>("admin/divisions/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
    },
  });
}

// Admin: Update division (platform admin only)
export function useAdminUpdateDivision(divisionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateDivisionInput) =>
      apiPut<Division>(`admin/divisions/${divisionId}/`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.divisions.detail(divisionId),
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
    },
  });
}

// Admin: Delete division (platform admin only)
export function useAdminDeleteDivision() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (divisionId: string) =>
      apiDelete<void>(`admin/divisions/${divisionId}/`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.divisions.all });
    },
  });
}

// Fetch teams within a division
export function useDivisionTeams(divisionId: string) {
  return useQuery({
    queryKey: queryKeys.divisions.teams(divisionId),
    queryFn: () =>
      apiGet<{ results: TeamListItem[]; count: number }>(
        `divisions/${divisionId}/teams`
      ),
    enabled: !!divisionId,
  });
}
