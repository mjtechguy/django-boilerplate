# PRD: Frontend Application (React + Vite + TypeScript)

## 1) Goal and Success Criteria

Build a modern, type-safe frontend that integrates with the Django/DRF + Keycloak + Cerbos backend platform.

**Success Criteria:**
- Sub-2s initial load time (LCP < 2s) on 4G connections
- Full OIDC auth flow with Keycloak (login, logout, token refresh)
- Role-based UI rendering (hide features user can't access)
- Responsive design (mobile-first, works on 320px+)
- WCAG 2.1 AA accessibility compliance
- 80%+ test coverage on critical auth/data flows

## 2) Scope and Non-Goals

**In Scope:**
- Single application with role-based routing (Global Admin, Org Admin, End User views)
- Keycloak OIDC authentication integration (direct to API)
- API client with token management and refresh
- Role-aware routing and component rendering
- Data fetching, caching, and optimistic updates
- Forms with validation (Zod schemas matching backend)
- Real-time notifications (WebSocket integration)
- Dark/light theme support

**Out of Scope:**
- Backend API development (already exists)
- Mobile native apps
- Offline-first/PWA functionality (phase 2)
- i18n/localization (phase 2)

## 3) Tech Stack

| Layer | Library/Tool |
|-------|-------------|
| Build/Dev Server | Vite 6.x |
| Framework | React 19 + TypeScript 5.x |
| Styling | Tailwind CSS v4 + `@tailwindcss/vite` |
| Components | shadcn/ui (Radix primitives) |
| Routing | TanStack Router |
| Server State | TanStack Query v5 |
| Forms | React Hook Form + Zod |
| Tables | TanStack Table |
| Icons | Lucide React |
| Auth | oidc-client-ts or custom Keycloak integration |
| HTTP Client | ky or native fetch wrapper |
| Date/Time | date-fns |
| Utils | clsx, tailwind-merge, class-variance-authority |

### Package Manager
- **pnpm** (preferred for speed and disk efficiency)

### Dev Dependencies
- ESLint + Prettier (code quality)
- Vitest + React Testing Library (unit/integration tests)
- Playwright (E2E tests)
- TypeScript strict mode

## 4) Application Architecture

Single Vite application with role-based routing. User roles determine which routes and features are accessible.

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                # shadcn/ui components
│   │   ├── layouts/           # Shell layouts per role
│   │   └── shared/            # Shared components
│   ├── routes/
│   │   ├── admin/             # Platform admin routes (platform_admin role)
│   │   ├── org/               # Org admin routes (org_admin role)
│   │   ├── app/               # End-user routes (authenticated users)
│   │   └── public/            # Public routes (login, etc.)
│   ├── lib/
│   │   ├── api/               # API client and queries
│   │   ├── auth/              # Auth context, guards, hooks
│   │   └── utils/             # Utilities
│   ├── hooks/                 # Shared hooks
│   └── types/                 # TypeScript types
├── public/
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### Role-Based Access

| Role | Routes | Purpose |
|------|--------|---------|
| `platform_admin` | `/admin/*` | Platform-wide settings, cross-tenant support |
| `org_admin` | `/org/*` | Org settings, teams, users, billing |
| `org_member` / `team_member` | `/app/*` | Product features, end-user experience |

Access control:
- Single Keycloak client (`api`) with role claims in JWT
- TanStack Router guards check roles before rendering
- Backend API enforces authorization via Cerbos (defense in depth)
- UI hides/shows features based on roles (UX only, not security)

## 5) Authentication Flow

### Direct Auth to API (No BFF)

The frontend authenticates directly with Keycloak and sends JWT tokens to the Django API. There is no backend-for-frontend proxy.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Frontend │────▶│ Keycloak │────▶│ Frontend │────▶│ Django   │
│ (React)  │     │ (OIDC)   │     │ (w/JWT)  │     │ API      │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
     │                                                   │
     │  1. Redirect to Keycloak login                   │
     │  2. User authenticates                           │
     │  3. Redirect back with auth code                 │
     │  4. Exchange code for tokens                     │
     │  5. Store access token in memory                 │
     │  6. API requests with Bearer token ─────────────▶│
     │  7. Django validates JWT via JWKS               │
     │  8. Cerbos enforces authorization               │
```

### Token Storage Strategy
- **Access token**: In-memory only (not localStorage) - prevents XSS theft
- **Refresh token**: In-memory or secure cookie (depending on Keycloak client config)
- **Session state**: React context + TanStack Query cache
- **No BFF**: Frontend talks directly to Django API with JWT

### Auth Context Shape
```typescript
interface AuthContext {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: {
    sub: string;
    email: string;
    name: string;
    realmRoles: string[];
    clientRoles: string[];
    orgId?: string;
    teamIds?: string[];
  } | null;
  login: () => void;
  logout: () => void;
  getAccessToken: () => Promise<string>;
}
```

## 6) API Integration

### HTTP Client Setup
```typescript
// Interceptor pattern for auth
const api = createApiClient({
  baseUrl: import.meta.env.VITE_API_URL,
  getToken: () => authContext.getAccessToken(),
  onUnauthorized: () => authContext.login(),
});
```

### TanStack Query Patterns
```typescript
// Query keys namespace
const queryKeys = {
  orgs: {
    all: ['orgs'] as const,
    detail: (id: string) => ['orgs', id] as const,
    members: (id: string) => ['orgs', id, 'members'] as const,
  },
  // ...
};

// Optimistic updates for mutations
const updateOrgMutation = useMutation({
  mutationFn: updateOrg,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: queryKeys.orgs.detail(id) });
    const previous = queryClient.getQueryData(queryKeys.orgs.detail(id));
    queryClient.setQueryData(queryKeys.orgs.detail(id), newData);
    return { previous };
  },
  onError: (err, vars, context) => {
    queryClient.setQueryData(queryKeys.orgs.detail(id), context?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.orgs.detail(id) });
  },
});
```

## 7) Page Requirements

### Global Admin Portal

| Page | Features |
|------|----------|
| Dashboard | Platform metrics, health status, alerts |
| Organizations | List all orgs, search, filter, create |
| Org Detail | View/edit org, license tier, feature flags |
| Users | Cross-tenant user search (support) |
| Settings | Global defaults (fail mode, audit retention) |
| Policies | Cerbos policy version info, publish status |
| Audit Logs | Platform-wide audit log viewer |

### Org Admin Portal

| Page | Features |
|------|----------|
| Dashboard | Org metrics, activity feed, quick actions |
| Team Management | Create/edit teams, assign members |
| User Management | Invite users, manage roles, deactivate |
| Settings | Org-level settings (audit, features) |
| Billing | License tier, Stripe portal link, usage |
| Audit Logs | Org-scoped audit log viewer |
| Integrations | Webhooks, API keys |

### Customer Portal

| Page | Features |
|------|----------|
| Dashboard | User's activity, notifications |
| Resources | Main product features (TBD based on product) |
| Profile | User settings, MFA, sessions |
| Notifications | Real-time + history |

## 8) State Management

### Layered Approach
1. **Server State**: TanStack Query (API data, caching, sync)
2. **Auth State**: React Context (user, tokens, roles)
3. **UI State**: React useState/useReducer (modals, forms, local UI)
4. **URL State**: TanStack Router (filters, pagination, navigation)

### No Global Store (Redux/Zustand)
- Server state via TanStack Query eliminates most global state needs
- Keep state close to where it's used
- Avoid prop drilling with composition and context where needed

## 9) Routing & Navigation

### TanStack Router Features Used
- File-based routing
- Type-safe route params
- Search params validation (Zod)
- Loader functions for data prefetching
- Pending/error states per route

### Route Protection
```typescript
// Auth guard in route definition
const protectedRoute = createRoute({
  beforeLoad: async ({ context }) => {
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login' });
    }
  },
});

// Role guard
const adminRoute = createRoute({
  beforeLoad: async ({ context }) => {
    if (!context.auth.user?.realmRoles.includes('platform_admin')) {
      throw redirect({ to: '/unauthorized' });
    }
  },
});
```

## 10) Component Patterns

### Role-Aware Rendering
```typescript
// Hide UI based on permissions
<RequireRole roles={['org_admin', 'platform_admin']}>
  <DeleteButton />
</RequireRole>

// Or with hook
const canDelete = useHasRole(['org_admin']);
{canDelete && <DeleteButton />}
```

### Form Pattern (React Hook Form + Zod)
```typescript
const schema = z.object({
  name: z.string().min(1, 'Required'),
  email: z.string().email(),
});

function OrgForm() {
  const form = useForm({ resolver: zodResolver(schema) });
  // ...
}
```

### Data Table Pattern (TanStack Table)
- Server-side pagination
- Column sorting/filtering
- Row selection
- Virtualization for large datasets

## 11) Real-Time Features

### WebSocket Integration
- Connect to `/ws/notifications/` for user notifications
- Connect to `/ws/events/{orgId}/` for org-wide events
- Auto-reconnect with exponential backoff
- Invalidate TanStack Query cache on relevant events

## 12) Security Considerations

- **No secrets in frontend code** (all via env vars, never committed)
- **CSRF protection** via SameSite cookies + CORS
- **XSS prevention** via React's default escaping + CSP headers
- **Token security** via memory storage (no localStorage for tokens)
- **Input validation** via Zod on both client and server
- **Route guards** prevent unauthorized navigation
- **API errors** never expose stack traces to UI

## 13) Theme & Responsive Design

### Dark/Light Theme
- **Built-in support** via shadcn/ui + Tailwind CSS
- **System preference detection** via `prefers-color-scheme` media query
- **User preference toggle** stored in localStorage
- **CSS variables** for theme colors (shadcn/ui default)
- **No flash on load** via inline script in HTML head

```typescript
// Theme provider pattern
<ThemeProvider defaultTheme="system" storageKey="ui-theme">
  <App />
</ThemeProvider>

// Toggle component
<ModeToggle /> // Light / Dark / System options
```

### Color Scheme
- Use shadcn/ui default neutral palette (clean enterprise aesthetic)
- Consistent contrast ratios for accessibility (WCAG 2.1 AA)
- Semantic colors: success (green), warning (amber), error (red), info (blue)

### Responsive Design (Mobile-First)
- **Breakpoints** (Tailwind defaults):
  - `sm`: 640px (small tablets)
  - `md`: 768px (tablets)
  - `lg`: 1024px (laptops)
  - `xl`: 1280px (desktops)
  - `2xl`: 1536px (large screens)
- **Minimum width**: 320px (iPhone SE)
- **Touch-friendly**: 44px minimum tap targets
- **Navigation**: Collapsible sidebar on mobile, hamburger menu

### Layout Patterns
```
Desktop (lg+):
┌─────────┬────────────────────────────┐
│ Sidebar │  Header                    │
│ (240px) ├────────────────────────────┤
│         │  Main Content              │
│         │                            │
└─────────┴────────────────────────────┘

Mobile (<lg):
┌────────────────────────────┐
│ Header + Hamburger         │
├────────────────────────────┤
│  Main Content              │
│                            │
│                            │
└────────────────────────────┘
│ Slide-out drawer when open │
```

### Component Responsiveness
- **Tables**: Horizontal scroll on mobile, or card view for small datasets
- **Forms**: Stack fields vertically on mobile
- **Modals**: Full-screen sheets on mobile, centered dialogs on desktop
- **Navigation**: Breadcrumbs collapse to back button on mobile

## 14) Development Workflow

### Local Development
```bash
# Start frontend dev server
pnpm dev

# Proxy API requests to backend
# (configured in vite.config.ts)
```

### Vite Config (API Proxy)
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
});
```

### Testing Strategy
| Type | Tool | Coverage Target |
|------|------|-----------------|
| Unit | Vitest | Hooks, utils, components |
| Integration | Vitest + RTL | Forms, flows |
| E2E | Playwright | Critical paths (login, CRUD) |

### CI Pipeline
1. Lint (ESLint + Prettier check)
2. Type check (tsc --noEmit)
3. Unit/Integration tests (Vitest)
4. Build (Vite production build)
5. E2E tests (Playwright against preview)

## 15) Deployment

### Build Output
- Static files (HTML, JS, CSS, assets)
- Deploy to CDN (Cloudflare Pages, Vercel, S3+CloudFront)
- Environment-specific config via build-time env vars

### Environment Variables
```bash
VITE_API_URL=https://api.example.com
VITE_KEYCLOAK_URL=https://auth.example.com
VITE_KEYCLOAK_REALM=app
VITE_KEYCLOAK_CLIENT_ID=api  # Single client for all roles
```

## 16) Implementation Priority

### Phase 1: Foundation + Admin Routes
Build core infrastructure and platform admin features:
- Auth integration (Keycloak OIDC, token management)
- Role-based routing with TanStack Router
- Shared components (shadcn/ui setup, layouts)
- Theme system (dark/light mode)
- Admin routes: Dashboard, Organizations, Settings

### Phase 2: Org Admin Routes
Add organization management features:
- Org admin routes: Teams, Users, Billing, Audit Logs
- Role guards for org_admin access
- Org-scoped API queries

### Phase 3: End User Routes
Add end-user experience:
- App routes: Dashboard, Profile, Notifications
- WebSocket integration for real-time updates
- Product-specific features (TBD)

## Decisions Made

- **Architecture**: Single Vite app with role-based routing (not 3 separate apps)
- **Auth Flow**: Direct to API (no backend-for-frontend proxy)
- **Theme**: Dark/light mode with system preference detection
- **Responsive**: Mobile-first design, 320px minimum width
- **Build Priority**: Foundation → Admin → Org → User features
