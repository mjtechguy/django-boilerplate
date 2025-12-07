# Plan 09: Admin vs Org Admin vs End-User Separation

## Tasks
- Define API namespaces/hostnames for global admin, org admin, end-user; enforce via audience checks and routing. ✅ (namespaced routes added; basic role guards)
- Implement role-gated endpoints:
  - Global admin: support-readonly views, policy/version info, global settings read/update. ✅ (admin org list as stub; forbidden for org_admin)
  - Org admin: org settings, teams, memberships, org-scoped settings (license/flags, audit retention/PII policy), billing status. ✅ (license endpoints)
  - End-user: product endpoints (stub). ✅ (ping/protected)
- Ensure Cerbos policies align; default deny cross-tenant; platform roles only where guarded. ✅ (tests enforce platform/admin separation)
- Add MFA flag enforcement where required (sensitive actions). ☐ (to extend later)

## Tests / Validation
- Integration: requests with mismatched audience are rejected; org admin cannot access global endpoints; cross-tenant access denied. ✅ (admin list forbids org_admin; org license enforces org match)
- Unit: route guards and permission checks per namespace. ✅ (tests)
- Audit logs capture admin actions. ☐ (logging to add) 
