import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPut, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  User,
  UsersResponse,
  UserMembershipsResponse,
  CreateUserInput,
  InviteUserInput,
  UpdateUserInput,
} from "./types";

interface UsersQueryParams {
  search?: string;
  is_active?: boolean;
  auth_provider?: string;
  org_id?: string;
  limit?: number;
  offset?: number;
}

// Fetch all users (admin only)
export function useUsers(params?: UsersQueryParams) {
  const searchParams = new URLSearchParams();
  if (params?.search) searchParams.set("search", params.search);
  if (params?.is_active !== undefined) searchParams.set("is_active", String(params.is_active));
  if (params?.auth_provider) searchParams.set("auth_provider", params.auth_provider);
  if (params?.org_id) searchParams.set("org_id", params.org_id);
  if (params?.limit) searchParams.set("limit", params.limit.toString());
  if (params?.offset) searchParams.set("offset", params.offset.toString());

  const queryString = searchParams.toString();
  const url = queryString ? `admin/users?${queryString}` : "admin/users";

  return useQuery({
    queryKey: queryKeys.users.list(params as Record<string, unknown>),
    queryFn: () => apiGet<UsersResponse>(url),
  });
}

// Fetch single user (admin endpoint)
export function useUser(userId: number | string) {
  return useQuery({
    queryKey: queryKeys.users.detail(String(userId)),
    queryFn: () => apiGet<User>(`admin/users/${userId}`),
    enabled: !!userId,
  });
}

// Fetch user memberships
export function useUserMemberships(userId: number | string) {
  return useQuery({
    queryKey: [...queryKeys.users.detail(String(userId)), "memberships"],
    queryFn: () => apiGet<UserMembershipsResponse>(`admin/users/${userId}/memberships`),
    enabled: !!userId,
  });
}

// Create local user
export function useCreateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateUserInput) => apiPost<User>("admin/users", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

// Invite OIDC user
export function useInviteUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: InviteUserInput) =>
      apiPost<{ message: string; user: User }>("admin/users/invite", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

// Update user
export function useUpdateUser(userId: number | string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UpdateUserInput) => apiPut<User>(`admin/users/${userId}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(String(userId)) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

// Deactivate user
export function useDeactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: number | string) =>
      apiDelete<{ message: string; user_id: string }>(`admin/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
  });
}

// Resend invite
export function useResendInvite() {
  return useMutation({
    mutationFn: (userId: number | string) =>
      apiPost<{ message: string }>(`admin/users/${userId}/resend-invite`, {}),
  });
}
