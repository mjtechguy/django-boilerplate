import { z } from "zod";

export const teamSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  org: z.string().uuid(),
  org_name: z.string(),
  members_count: z.number(),
  created_at: z.string(),
  updated_at: z.string().optional(),
});

export type Team = z.infer<typeof teamSchema>;

export const teamListItemSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  org: z.string().uuid(),
  org_name: z.string(),
  members_count: z.number(),
  created_at: z.string(),
});

export type TeamListItem = z.infer<typeof teamListItemSchema>;

export const teamsResponseSchema = z.object({
  results: z.array(teamListItemSchema),
  count: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type TeamsResponse = z.infer<typeof teamsResponseSchema>;

export const createTeamInputSchema = z.object({
  name: z.string().min(1, "Team name is required"),
  org: z.string().uuid("Organization is required"),
});

export type CreateTeamInput = z.infer<typeof createTeamInputSchema>;

export const updateTeamInputSchema = z.object({
  name: z.string().min(1, "Team name is required"),
});

export type UpdateTeamInput = z.infer<typeof updateTeamInputSchema>;

export const teamMemberSchema = z.object({
  membership_id: z.string().uuid(),
  user_id: z.string().uuid(),
  email: z.string().email(),
  first_name: z.string(),
  last_name: z.string(),
  team_roles: z.array(z.string()),
  joined_at: z.string(),
});

export type TeamMember = z.infer<typeof teamMemberSchema>;

export const teamMembersResponseSchema = z.object({
  team_id: z.string().uuid(),
  team_name: z.string(),
  count: z.number(),
  members: z.array(teamMemberSchema),
});

export type TeamMembersResponse = z.infer<typeof teamMembersResponseSchema>;
