import { z } from "zod";

export const userMembershipSchema = z.object({
  id: z.string().uuid(),
  org: z.string().uuid(),
  org_name: z.string(),
  team: z.string().uuid().nullable(),
  team_name: z.string().nullable(),
  org_roles: z.array(z.string()),
  team_roles: z.array(z.string()),
  created_at: z.string(),
});

export type UserMembership = z.infer<typeof userMembershipSchema>;

export const userSchema = z.object({
  id: z.number(),
  email: z.string().email(),
  first_name: z.string(),
  last_name: z.string(),
  is_active: z.boolean(),
  auth_provider: z.string(),
  email_verified: z.boolean(),
  roles: z.array(z.string()),
  memberships_count: z.number(),
  memberships: z.array(userMembershipSchema).optional(),
  date_joined: z.string(),
  last_login: z.string().nullable().optional(),
});

export type User = z.infer<typeof userSchema>;

export const userListItemSchema = z.object({
  id: z.number(),
  email: z.string().email(),
  first_name: z.string(),
  last_name: z.string(),
  is_active: z.boolean(),
  auth_provider: z.string(),
  email_verified: z.boolean(),
  roles: z.array(z.string()),
  memberships_count: z.number(),
  date_joined: z.string(),
});

export type UserListItem = z.infer<typeof userListItemSchema>;

export const usersResponseSchema = z.object({
  results: z.array(userListItemSchema),
  count: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type UsersResponse = z.infer<typeof usersResponseSchema>;

// Create local user input
export const createUserInputSchema = z.object({
  email: z.string().email("Valid email is required"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one digit"),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  roles: z.array(z.string()).optional(),
});

export type CreateUserInput = z.infer<typeof createUserInputSchema>;

// Invite OIDC user input
export const inviteUserInputSchema = z.object({
  email: z.string().email("Valid email is required"),
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  roles: z.array(z.string()).optional(),
  org_id: z.string().uuid().optional().nullable(),
  org_roles: z.array(z.string()).optional(),
});

export type InviteUserInput = z.infer<typeof inviteUserInputSchema>;

// Update user input
export const updateUserInputSchema = z.object({
  first_name: z.string().optional(),
  last_name: z.string().optional(),
  is_active: z.boolean().optional(),
  roles: z.array(z.string()).optional(),
});

export type UpdateUserInput = z.infer<typeof updateUserInputSchema>;

// User memberships response
export const userMembershipsResponseSchema = z.object({
  user_id: z.string(),
  user_email: z.string(),
  count: z.number(),
  memberships: z.array(userMembershipSchema),
});

export type UserMembershipsResponse = z.infer<typeof userMembershipsResponseSchema>;
