# Plan 08: Licensing and Stripe (Optional)

## Tasks
- Implement Settings accessors: license_tier, feature_flags with precedence (env default → global → org override). ✅ (`api/licensing.py`)
- Add org-scoped API endpoints (role-gated) to read/update license/flags; audit changes; trigger cache/Cerbos invalidation. ✅ (`OrgLicenseView`; simple role check; invalidates decision cache)
- Implement Stripe webhook stub (env-gated) to map product/price → tier/flags; store last sync status and timestamp. ✅ (stub endpoint + settings record)
- Expose licensing status via admin/org APIs for frontend. ✅

## Tests / Validation
- Unit/Integration: license get/update, role enforcement, webhook stub recorded. ✅ (pytest suite)
- Cache invalidation: Cerbos decision cache cleared on update. ✅ (called in update)
- Stripe signature validation: ☐ (stub only) 
