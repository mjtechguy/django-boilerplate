import { z } from "zod";

export const billingModeSchema = z.enum(["inherit", "independent"]);
export type BillingMode = z.infer<typeof billingModeSchema>;

export const divisionSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  org_name: z.string(),
  name: z.string().min(1),
  billing_mode: billingModeSchema,
  license_tier: z.string().optional(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
  stripe_customer_id: z.string().nullable().optional(),
  stripe_subscription_id: z.string().nullable().optional(),
  billing_email: z.string().email().nullable().optional(),
  teams_count: z.number().optional(),
  members_count: z.number().optional(),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

export type Division = z.infer<typeof divisionSchema>;

export const divisionListItemSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  org_name: z.string(),
  name: z.string().min(1),
  billing_mode: billingModeSchema,
  license_tier: z.string().optional(),
  teams_count: z.number(),
  members_count: z.number(),
  created_at: z.string(),
});

export type DivisionListItem = z.infer<typeof divisionListItemSchema>;

export const divisionsResponseSchema = z.object({
  results: z.array(divisionListItemSchema),
  count: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type DivisionsResponse = z.infer<typeof divisionsResponseSchema>;

export const createDivisionInputSchema = z.object({
  name: z.string().min(1, "Division name is required"),
  org: z.string().uuid("Organization is required").optional(),
  billing_mode: billingModeSchema.optional(),
  license_tier: z.string().optional(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
  billing_email: z.string().email().optional(),
});

export type CreateDivisionInput = z.infer<typeof createDivisionInputSchema>;

export const updateDivisionInputSchema = z.object({
  name: z.string().min(1, "Division name is required").optional(),
  billing_mode: billingModeSchema.optional(),
  license_tier: z.string().optional(),
  feature_flags: z.record(z.string(), z.unknown()).optional(),
  billing_email: z.string().email().optional(),
});

export type UpdateDivisionInput = z.infer<typeof updateDivisionInputSchema>;
