import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  Org,
  OrgsResponse,
  License,
  UpdateLicenseRequest,
  CreateOrgInput,
  UpdateOrgInput,
} from "./types";

interface OrgsQueryParams {
  search?: string;
  status?: string;
  license_tier?: string;
  limit?: number;
  offset?: number;
}

// Fetch all organizations (admin only)
export function useOrganizations(params?: OrgsQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.status) searchParams.set("status", params.status);
  if (params?.license_tier) searchParams.set("license_tier", params.license_tier);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString ? `admin/orgs?${queryString}` : "admin/orgs";

  return useQuery({
    queryKey: queryKeys.orgs.list(params as Record<string, unknown>),
    queryFn: () => apiGet<OrgsResponse>(url),
  });
}

// Fetch single organization (admin endpoint)
export function useOrganization(orgId: string) {
  return useQuery({
    queryKey: queryKeys.orgs.detail(orgId),
    queryFn: () => apiGet<Org>(`admin/orgs/${orgId}`),
    enabled: !!orgId,
  });
}

// Create organization
export function useCreateOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateOrgInput) => apiPost<Org>("admin/orgs", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}

// Update organization
export function useUpdateOrganization(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateOrgInput) => apiPut<Org>(`admin/orgs/${orgId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.detail(orgId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}

// Delete (deactivate) organization
export function useDeleteOrganization() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orgId: string) =>
      apiDelete<{ message: string; org_id: string }>(`admin/orgs/${orgId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}

// Fetch organization license
export function useOrgLicense(orgId: string) {
  return useQuery({
    queryKey: queryKeys.orgs.license(orgId),
    queryFn: () => apiGet<License>(`orgs/${orgId}/license`),
    enabled: !!orgId,
  });
}

// Update organization license
export function useUpdateOrgLicense(orgId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateLicenseRequest) =>
      apiPut<License>(`orgs/${orgId}/license`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.license(orgId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.detail(orgId) });
    },
  });
}
