# Plan 07: Cerbos Integration

## Versions / Dependencies
- cerbos==0.7.0 (Python SDK), Cerbos container (latest stable).

## Tasks
- Add Cerbos client config (gRPC) with env for host/port; readiness check on startup. ✅ (config + client helper)
- Implement permission helper to build principal/resource (roles, org_id, team_ids, license_tier, mfa_level, risk flags). ✅
- Add Redis-backed decision cache (short TTL); invalidation hooks on settings/license change. ✅ (cache in cerbos_client; coarse invalidation)
- Create sample policy bundle (YAML) for patient_record/project/document; mount into Cerbos container. ✅ (sample_resource policy + conf)
- Wire DRF permission class to call Cerbos and enforce ALLOW/DENY; include audit context (request_id). ✅ (permission class + protected view)

## Tests / Validation
- Unit: principal/resource builder; cache keying; permission class behavior (allow/deny). ✅ (pytest suite with mocks and cache check)
- Integration: Cerbos container up; sample requests evaluate as expected against policy bundle. ✅ (manual via Compose; add CI job later)
- Contract tests for policy bundle in CI. ☐ (future work to add cerbos test runner)
