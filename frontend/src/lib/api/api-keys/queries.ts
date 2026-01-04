import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type {
  ListAPIKeysResponse,
  CreateAPIKeyInput,
  CreateAPIKeyResponse,
  RevokeAPIKeyResponse,
} from "./types";

/**
 * Get list of API keys for the current user.
 */
export function useApiKeys() {
  return useQuery({
    queryKey: queryKeys.apiKeys.list(),
    queryFn: () => apiGet<ListAPIKeysResponse>("me/api-keys"),
  });
}

/**
 * Create a new API key.
 */
export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateAPIKeyInput) =>
      apiPost<CreateAPIKeyResponse>("me/api-keys", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.list() });
    },
  });
}

/**
 * Revoke an existing API key.
 */
export function useRevokeApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      apiDelete<RevokeAPIKeyResponse>(`me/api-keys/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys.list() });
    },
  });
}
