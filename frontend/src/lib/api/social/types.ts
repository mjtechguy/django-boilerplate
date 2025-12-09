import { z } from "zod";

// Social provider schema
export const socialProviderSchema = z.object({
  id: z.string(),
  name: z.string(),
});

export type SocialProvider = z.infer<typeof socialProviderSchema>;

// Social providers response schema
export const socialProvidersResponseSchema = z.object({
  providers: z.array(socialProviderSchema),
});

export type SocialProvidersResponse = z.infer<typeof socialProvidersResponseSchema>;

// Social login URL response schema
export const socialLoginUrlResponseSchema = z.object({
  auth_url: z.string(),
});

export type SocialLoginUrlResponse = z.infer<typeof socialLoginUrlResponseSchema>;

// Social account schema
export const socialAccountSchema = z.object({
  id: z.number(),
  provider: z.string(),
  created_at: z.string(),
});

export type SocialAccount = z.infer<typeof socialAccountSchema>;

// Social accounts response schema
export const socialAccountsResponseSchema = z.object({
  accounts: z.array(socialAccountSchema),
});

export type SocialAccountsResponse = z.infer<typeof socialAccountsResponseSchema>;
