# Plan 13: Testing & CI

## Tasks
- Expand pytest suite: auth class (JWT validation cases), settings precedence, Cerbos permission helper, idempotency middleware, licensing API, admin/org boundaries.
- Add contract tests for Cerbos policies using sample bundle.
- Configure coverage reporting; enforce minimum threshold.
- CI pipeline: ruff, pytest + coverage, dependency scan (pip-audit/safety), container build + scan; optional SBOM generation placeholder.

## Tests / Validation
- `ruff check .` passes.
- `pytest --maxfail=1 --disable-warnings -q` passes with coverage threshold met.
- Policy contract tests run in CI (Cerbos container spun up in pipeline).
- Dependency/container scans complete successfully. 
