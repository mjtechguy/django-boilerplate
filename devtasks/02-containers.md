# Plan 02: Core Services & Containers

## Versions / Dependencies
- Base image: slim Python (matching runtime, e.g., python:3.12-slim) or distroless if feasible.
- Docker Compose services: web, postgres, redis, rabbitmq, keycloak, cerbos, celery, celery-beat, optional stripe-mock, optional s3/minio.
- Healthchecks: HTTP for web/Cerbos, TCP/AMQP for RabbitMQ, Redis ping, Postgres pg_isready, Keycloak endpoint.

## Tasks
- Author Dockerfile for Django app (multi-stage: builder + runtime, non-root user). ✅ (single-stage; can harden later)
- Entry points: web (runserver for dev), celery worker, celery beat. ✅
- Compose file: wire networks/volumes, env vars, ports; mount Keycloak realm import, Cerbos policies bundle. ✅
- Configure RabbitMQ (DLQ/TTL policy defaults), Redis, Postgres volumes. ✅ (baseline; DLQ policies to be refined)
- Add healthchecks for all services. ✅
- Optional MinIO/stripe-mock services for local dev. ✅

## Tests / Validation
- `docker compose build` succeeds.
- `docker compose up` brings all services healthy.
- Verify Cerbos health endpoint reachable; RabbitMQ management (if enabled) responds; Redis ping OK.
- Web container serves Django health endpoint; Celery worker connects to RabbitMQ; beat schedules heartbeat task.
- Keycloak realm import loads (realm-app.json); minio/stripe-mock optional. 
