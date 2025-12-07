# Plan 12: Observability

## Tasks
- Configure structlog for JSON logs with request_id/trace_id, actor, org_id, decision info.
- Add Sentry for web + Celery (env-gated).
- Metrics: expose Prometheus-style metrics for Django (latency, errors), Cerbos client latency, RabbitMQ queue/DLQ depth (exporter), Redis stats, Celery task outcomes.
- Health/readiness probes for all services.
- Logging redaction for PII per policy; ensure audit logs include policy_version/decision_id.

## Tests / Validation
- Unit: logging formatter includes required fields; redaction applied to PII-marked fields.
- Integration: metrics endpoint returns data; Sentry receives a test event (when enabled).
- Health endpoints report ready/healthy under normal conditions. 
