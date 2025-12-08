export const queryKeys = {
  // Organizations
  orgs: {
    all: ["orgs"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["orgs", "list", filters] as const,
    detail: (id: string) => ["orgs", id] as const,
    license: (id: string) => ["orgs", id, "license"] as const,
  },

  // Teams
  teams: {
    all: ["teams"] as const,
    list: (orgId?: string, filters?: Record<string, unknown>) =>
      ["teams", "list", orgId, filters] as const,
    detail: (id: string) => ["teams", id] as const,
    members: (id: string) => ["teams", id, "members"] as const,
  },

  // Users
  users: {
    all: ["users"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["users", "list", filters] as const,
    detail: (id: string) => ["users", id] as const,
  },

  // Audit
  audit: {
    all: ["audit"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["audit", "list", filters] as const,
    verify: (id: string) => ["audit", "verify", id] as const,
    chainVerify: () => ["audit", "chain-verify"] as const,
  },

  // Webhooks
  webhooks: {
    all: ["webhooks"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["webhooks", "list", filters] as const,
    detail: (id: string) => ["webhooks", id] as const,
    deliveries: (id: string, filters?: Record<string, unknown>) =>
      ["webhooks", id, "deliveries", filters] as const,
  },

  // Monitoring
  monitoring: {
    overview: ["monitoring", "overview"] as const,
    server: ["monitoring", "server"] as const,
    health: ["monitoring", "health"] as const,
    celeryHealth: ["monitoring", "celery", "health"] as const,
    celeryStats: ["monitoring", "celery", "stats"] as const,
    queues: ["monitoring", "queues"] as const,
    tasks: ["monitoring", "tasks"] as const,
    metrics: ["monitoring", "metrics"] as const,
  },

  // Settings
  settings: {
    all: ["settings"] as const,
    global: () => ["settings", "global"] as const,
    org: (orgId: string) => ["settings", "org", orgId] as const,
  },
} as const;
