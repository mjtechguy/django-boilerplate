import { z } from "zod";

// MFA status schema
export const mfaStatusSchema = z.object({
  enabled: z.boolean(),
  backup_codes_remaining: z.number().optional(),
  last_used_at: z.string().nullable().optional(),
});

export type MfaStatus = z.infer<typeof mfaStatusSchema>;

// MFA setup response schema
export const mfaSetupResponseSchema = z.object({
  secret: z.string(),
  qr_code: z.string(),
  provisioning_uri: z.string().optional(),
  backup_codes: z.array(z.string()),
  message: z.string(),
});

export type MfaSetupResponse = z.infer<typeof mfaSetupResponseSchema>;

// MFA verify request schema
export const mfaVerifyRequestSchema = z.object({
  code: z
    .string()
    .min(6, "Code must be 6 digits")
    .max(8, "Code must be 6-8 characters"),
});

export type MfaVerifyRequest = z.infer<typeof mfaVerifyRequestSchema>;

// MFA confirm response schema
export const mfaConfirmResponseSchema = z.object({
  message: z.string(),
  backup_codes_remaining: z.number().optional(),
});

export type MfaConfirmResponse = z.infer<typeof mfaConfirmResponseSchema>;

// MFA disable request schema
export const mfaDisableRequestSchema = z.object({
  code: z.string().min(1, "Code is required"),
});

export type MfaDisableRequest = z.infer<typeof mfaDisableRequestSchema>;

// Backup codes response schema
export const backupCodesResponseSchema = z.object({
  backup_codes: z.array(z.string()),
  message: z.string(),
});

export type BackupCodesResponse = z.infer<typeof backupCodesResponseSchema>;

// MFA login verify request schema
export const mfaLoginVerifyRequestSchema = z.object({
  mfa_token: z.string(),
  code: z
    .string()
    .min(6, "Code must be 6 digits")
    .max(8, "Code must be 6-8 characters"),
});

export type MfaLoginVerifyRequest = z.infer<typeof mfaLoginVerifyRequestSchema>;

// MFA login verify response
export const mfaLoginVerifyResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
});

export type MfaLoginVerifyResponse = z.infer<typeof mfaLoginVerifyResponseSchema>;
