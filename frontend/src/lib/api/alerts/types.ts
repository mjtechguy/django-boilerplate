import { z } from "zod";

export const alertSchema = z.object({
  id: z.string(),
  severity: z.enum(["info", "warning", "error"]),
  message: z.string(),
  source: z.enum(["system", "audit", "webhook"]),
  timestamp: z.string(),
  metadata: z.record(z.unknown()).optional(),
});

export const alertsResponseSchema = z.object({
  count: z.number(),
  results: z.array(alertSchema),
});

export type Alert = z.infer<typeof alertSchema>;
export type AlertsResponse = z.infer<typeof alertsResponseSchema>;
