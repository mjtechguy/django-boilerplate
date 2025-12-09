import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiDelete } from "../client";
import { queryKeys } from "../query-keys";
import type { SocialProvidersResponse, SocialAccountsResponse } from "./types";

/**
 * Get available social providers.
 */
export function useSocialProviders() {
  return useQuery({
    queryKey: queryKeys.social.providers(),
    queryFn: () => apiGet<SocialProvidersResponse>("auth/social/providers"),
  });
}

/**
 * Get connected social accounts for the current user.
 */
export function useSocialAccounts() {
  return useQuery({
    queryKey: queryKeys.social.accounts(),
    queryFn: () => apiGet<SocialAccountsResponse>("me/social-accounts"),
  });
}

/**
 * Disconnect a social account.
 */
export function useDisconnectSocialAccount() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (accountId: number) =>
      apiDelete<{ message: string }>(`me/social-accounts/${accountId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.social.accounts() });
    },
  });
}

/**
 * Initiate social login by redirecting to the provider's OAuth page.
 */
export function initiateSocialLogin(provider: string, redirectUrl?: string) {
  const params = new URLSearchParams();
  if (redirectUrl) {
    params.set("redirect", redirectUrl);
  }

  const apiUrl = import.meta.env.VITE_API_URL || "";
  const loginUrl = `${apiUrl}/api/v1/auth/social/${provider}/login${
    params.toString() ? `?${params.toString()}` : ""
  }`;

  window.location.href = loginUrl;
}
