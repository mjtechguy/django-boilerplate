import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "../client";
import { queryKeys } from "../query-keys";
import type {
  MfaStatus,
  MfaSetupResponse,
  MfaConfirmResponse,
  MfaDisableRequest,
  BackupCodesResponse,
  MfaLoginVerifyRequest,
  MfaLoginVerifyResponse,
} from "./types";

/**
 * Get MFA status for the current user.
 */
export function useMfaStatus() {
  return useQuery({
    queryKey: queryKeys.mfa.status(),
    queryFn: () => apiGet<MfaStatus>("auth/mfa/status"),
  });
}

/**
 * Setup MFA (get QR code and backup codes).
 */
export function useMfaSetup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => apiPost<MfaSetupResponse>("auth/mfa/setup", {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mfa.status() });
    },
  });
}

/**
 * Confirm MFA setup with TOTP code.
 */
export function useMfaConfirm() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (code: string) =>
      apiPost<MfaConfirmResponse>("auth/mfa/confirm", { code }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mfa.status() });
    },
  });
}

/**
 * Disable MFA for the current user.
 */
export function useMfaDisable() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MfaDisableRequest) =>
      apiPost<{ message: string }>("auth/mfa/disable", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mfa.status() });
    },
  });
}

/**
 * Regenerate backup codes (requires current TOTP code).
 */
export function useMfaRegenerateBackupCodes() {
  return useMutation({
    mutationFn: (code: string) =>
      apiPost<BackupCodesResponse>("auth/mfa/backup-codes", { code }),
  });
}

/**
 * Verify MFA during login (after password auth).
 */
export function useMfaVerify() {
  return useMutation({
    mutationFn: (data: MfaLoginVerifyRequest) =>
      apiPost<MfaLoginVerifyResponse>("auth/mfa/verify", data),
  });
}
