import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  Team,
  TeamsResponse,
  TeamMembersResponse,
  CreateTeamInput,
  UpdateTeamInput,
} from "./types";

interface TeamsQueryParams {
  search?: string;
  org_id?: string;
  limit?: number;
  offset?: number;
}

// Fetch all teams (admin only)
export function useTeams(params?: TeamsQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.org_id) searchParams.set("org_id", params.org_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString ? `admin/teams?${queryString}` : "admin/teams";

  return useQuery({
    queryKey: queryKeys.teams.list(params?.org_id, params as Record<string, unknown>),
    queryFn: () => apiGet<TeamsResponse>(url),
  });
}

// Fetch single team (admin endpoint)
export function useTeam(teamId: string) {
  return useQuery({
    queryKey: queryKeys.teams.detail(teamId),
    queryFn: () => apiGet<Team>(`admin/teams/${teamId}`),
    enabled: !!teamId,
  });
}

// Fetch team members
export function useTeamMembers(teamId: string) {
  return useQuery({
    queryKey: queryKeys.teams.members(teamId),
    queryFn: () => apiGet<TeamMembersResponse>(`admin/teams/${teamId}/members`),
    enabled: !!teamId,
  });
}

// Create team
export function useCreateTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTeamInput) => apiPost<Team>("admin/teams", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.teams.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}

// Update team
export function useUpdateTeam(teamId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateTeamInput) => apiPut<Team>(`admin/teams/${teamId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.teams.detail(teamId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.teams.all });
    },
  });
}

// Delete team
export function useDeleteTeam() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (teamId: string) =>
      apiDelete<{ message: string; team_id: string }>(`admin/teams/${teamId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.teams.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.orgs.all });
    },
  });
}
