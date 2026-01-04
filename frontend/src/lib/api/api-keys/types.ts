import { z } from "zod";

// User API Key schema (for list view)
export const userApiKeySchema = z.object({
  id: z.string(),
  prefix: z.string(),
  name: z.string(),
  created: z.string(),
  revoked: z.boolean(),
});

export type UserAPIKey = z.infer<typeof userApiKeySchema>;

// Create API Key input schema
export const createApiKeyInputSchema = z.object({
  name: z.string().optional(),
});

export type CreateAPIKeyInput = z.infer<typeof createApiKeyInputSchema>;

// Create API Key response schema (includes full key - only shown once)
export const createApiKeyResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  key: z.string(), // Full key - only returned once!
  prefix: z.string(),
  created: z.string(),
});

export type CreateAPIKeyResponse = z.infer<typeof createApiKeyResponseSchema>;

// List API Keys response schema
export const listApiKeysResponseSchema = z.object({
  api_keys: z.array(userApiKeySchema),
});

export type ListAPIKeysResponse = z.infer<typeof listApiKeysResponseSchema>;

// Revoke API Key response schema
export const revokeApiKeyResponseSchema = z.object({
  message: z.string(),
});

export type RevokeAPIKeyResponse = z.infer<typeof revokeApiKeyResponseSchema>;
