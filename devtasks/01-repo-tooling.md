# Plan 01: Repo + Tooling Baseline

## Versions / Dependencies
- Python: 3.13 (runtime/tooling).
- Django==6.0, djangorestframework==3.16.1.
- psycopg[binary,pool]==3.3.2.
- python-keycloak==5.8.1.
- cerbos==0.7.0.
- django-redis==6.0.0, redis==7.0.1.
- celery==5.6.0.
- django-axes==8.0.0, django-cors-headers==4.9.0, django-csp==4.0.
- sentry-sdk==2.47.0.
- structlog, ruff, pytest, coverage, pre-commit, pip-audit/safety.
- django-storages, boto3 (optional storage).

## Tasks
- Initialize git repo structure; add `.gitignore`, `.env.example` (no secrets). ✅
- Set up `uv` (preferred) with `pyproject.toml`, `requirements*.txt`; pin all deps above. ✅
- Configure pre-commit hooks: ruff (lint/format), trailing whitespace, end-of-file. ✅
- Add CI skeleton: ruff, pytest placeholder, dependency scan (pip-audit placeholder). ✅
- Document how to install tooling (uv/pip), run lint/tests.

## Tests / Validation
- `ruff check .`
- `pytest` (empty suite passes).
- `pip-audit` or `safety check`.
- Pre-commit runs clean locally.
- `uv venv` + `uv pip install -r requirements.txt -r requirements-dev.txt` succeed. ✅
