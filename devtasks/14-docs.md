# Plan 14: Documentation

## Tasks
- Update README with local dev flow: uv/pip install, compose up, migrate, seed Keycloak/Cerbos, sample API calls.
- Document env vars, secrets handling (dev .env vs prod secret manager), storage config (S3/MinIO), admin vs org vs user audiences/hostnames.
- Add runbooks for common tasks: rotate keys, clear caches, invalidate Cerbos decisions, recreate containers.
- Summarize PRD highlights and link to policy bundle and Keycloak realm files.

## Tests / Validation
- Docs lint (optional markdownlint); all commands verified locally.
- Quickstart followed on a clean environment to ensure completeness. 
