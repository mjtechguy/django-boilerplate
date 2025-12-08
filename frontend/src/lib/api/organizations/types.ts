import { z } from "zod";

export const orgStatusSchema = z.enum(["active", "inactive"]);
export type OrgStatus = z.infer<typeof orgStatusSchema>;

export const orgSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  status: orgStatusSchema,
  license_tier: z.string(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
  teams_count: z.number().optional(),
  members_count: z.number().optional(),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

export type Org = z.infer<typeof orgSchema>;

export const orgListItemSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  status: orgStatusSchema,
  license_tier: z.string(),
  teams_count: z.number(),
  members_count: z.number(),
  created_at: z.string(),
});

export type OrgListItem = z.infer<typeof orgListItemSchema>;

export const orgsResponseSchema = z.object({
  results: z.array(orgListItemSchema),
  count: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type OrgsResponse = z.infer<typeof orgsResponseSchema>;

// Create organization input
export const createOrgInputSchema = z.object({
  name: z.string().min(1, "Organization name is required"),
  status: orgStatusSchema,
  license_tier: z.string(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
});

export type CreateOrgInput = z.infer<typeof createOrgInputSchema>;

// Update organization input
export const updateOrgInputSchema = z.object({
  name: z.string().min(1, "Organization name is required").optional(),
  status: orgStatusSchema.optional(),
  license_tier: z.string().optional(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
});

export type UpdateOrgInput = z.infer<typeof updateOrgInputSchema>;

export const licenseSchema = z.object({
  tier: z.string(),
  feature_flags: z.record(z.string(), z.boolean()),
  expires_at: z.string().nullable().optional(),
});

export type License = z.infer<typeof licenseSchema>;

export interface UpdateLicenseRequest {
  tier?: string;
  feature_flags?: Record<string, boolean>;
}
