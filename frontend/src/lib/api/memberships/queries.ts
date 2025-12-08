import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  Membership,
  MembershipsResponse,
  CreateMembershipInput,
  UpdateMembershipInput,
} from "./types";

interface MembershipsQueryParams {
  user_id?: number | string;
  org_id?: string;
  team_id?: string;
  limit?: number;
  offset?: number;
}

// Fetch all memberships (admin only)
export function useMemberships(params?: MembershipsQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.user_id) searchParams.set("user_id", String(params.user_id));
  if (params?.org_id) searchParams.set("org_id", params.org_id);
  if (params?.team_id) searchParams.set("team_id", params.team_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString ? `admin/memberships?${queryString}` : "admin/memberships";

  return useQuery({
    queryKey: ["memberships", "list", params] as const,
    queryFn: () => apiGet<MembershipsResponse>(url),
  });
}

// Fetch single membership (admin endpoint)
export function useMembership(membershipId: string) {
  return useQuery({
    queryKey: ["memberships", membershipId] as const,
    queryFn: () => apiGet<Membership>(`admin/memberships/${membershipId}`),
    enabled: !!membershipId,
  });
}

// Create membership
export function useCreateMembership() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateMembershipInput) =>
      apiPost<Membership>("admin/memberships", data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["memberships"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(String(variables.user)) });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.detail(variables.org) });
    },
  });
}

// Update membership
export function useUpdateMembership(membershipId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateMembershipInput) =>
      apiPut<Membership>(`admin/memberships/${membershipId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memberships"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

// Delete membership
export function useDeleteMembership() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (membershipId: string) =>
      apiDelete<{ message: string; membership_id: string }>(`admin/memberships/${membershipId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memberships"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}
