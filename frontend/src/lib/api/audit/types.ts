import { z } from "zod";

export const auditActionSchema = z.enum([
  "CREATE",
  "UPDATE",
  "DELETE",
  "READ",
  "LOGIN",
  "LOGOUT",
]);

export type AuditAction = z.infer<typeof auditActionSchema>;

export const auditLogSchema = z.object({
  id: z.string().uuid(),
  actor_id: z.string(),
  actor_email: z.string().optional(),
  action: auditActionSchema,
  resource_type: z.string(),
  resource_id: z.string().optional(),
  details: z.record(z.string(), z.unknown()).optional(),
  ip_address: z.string().optional(),
  user_agent: z.string().optional(),
  org_id: z.string().uuid().optional(),
  timestamp: z.string(),
  hash: z.string().optional(),
});

export type AuditLog = z.infer<typeof auditLogSchema>;

export const auditLogsResponseSchema = z.object({
  results: z.array(auditLogSchema),
  count: z.number().optional(),
  next: z.string().nullable().optional(),
  previous: z.string().nullable().optional(),
});

export type AuditLogsResponse = z.infer<typeof auditLogsResponseSchema>;

export interface AuditFilters {
  action?: AuditAction;
  actor_id?: string;
  resource_type?: string;
  org_id?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  page_size?: number;
}

export interface AuditVerifyResponse {
  valid: boolean;
  message: string;
}

export interface AuditChainVerifyResponse {
  valid: boolean;
  verified_count: number;
  failed_at?: string;
  message: string;
}
