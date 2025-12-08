import { z } from "zod";

export const membershipSchema = z.object({
  id: z.string().uuid(),
  user: z.number(),
  user_email: z.string().email(),
  user_name: z.string(),
  org: z.string().uuid(),
  org_name: z.string(),
  team: z.string().uuid().nullable(),
  team_name: z.string().nullable(),
  org_roles: z.array(z.string()),
  team_roles: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

export type Membership = z.infer<typeof membershipSchema>;

export const membershipListItemSchema = z.object({
  id: z.string().uuid(),
  user: z.number(),
  user_email: z.string().email(),
  user_name: z.string(),
  org: z.string().uuid(),
  org_name: z.string(),
  team: z.string().uuid().nullable(),
  team_name: z.string().nullable(),
  org_roles: z.array(z.string()),
  team_roles: z.array(z.string()),
  created_at: z.string(),
});

export type MembershipListItem = z.infer<typeof membershipListItemSchema>;

export const membershipsResponseSchema = z.object({
  results: z.array(membershipListItemSchema),
  count: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type MembershipsResponse = z.infer<typeof membershipsResponseSchema>;

// Create membership input
export const createMembershipInputSchema = z.object({
  user: z.number({ message: "User is required" }),
  org: z.string().uuid({ message: "Organization is required" }),
  team: z.string().uuid().nullable().optional(),
  org_roles: z.array(z.string()),
  team_roles: z.array(z.string()),
});

export type CreateMembershipInput = z.infer<typeof createMembershipInputSchema>;

// Update membership input
export const updateMembershipInputSchema = z.object({
  org_roles: z.array(z.string()).optional(),
  team_roles: z.array(z.string()).optional(),
  team: z.string().uuid().nullable().optional(),
});

export type UpdateMembershipInput = z.infer<typeof updateMembershipInputSchema>;
