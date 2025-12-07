# Plan 03: Django/DRF Project Setup

## Versions / Dependencies
- Django==6.0, DRF==3.16.1, psycopg[binary,pool]==3.3.2.
- django-cors-headers==4.9.0, django-csp==4.0.
- structlog, sentry-sdk, django-storages, boto3.

## Tasks
- Create Django project/app; configure Postgres (pooled), timezone=UTC, locale en-us. ✅
- DRF config: default renderer/parser, pagination, versioned API prefix `/api/v1`. ✅
- Static/media config; optional S3/MinIO backend via django-storages/boto3, env-gated. ✅
- Add middleware: request/trace ID, structlog JSON logging, CORS, CSP, security headers. ✅ (basic CSP placeholder; security headers to tighten later)
- Add Sentry init (env-gated). ✅
- Add base settings separation: base/local/dev/prod with env overrides. ✅ (base/local in place; prod pending)

## Tests / Validation
- `python manage.py check`.
- `python manage.py migrate` (initial empty).
- `pytest` for settings smoke (load settings, ensure DRF defaults).
- Hit health endpoint (e.g., `/healthz`) via web container. 
