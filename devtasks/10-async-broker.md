# Plan 10: Async + Broker

## Tasks
- Configure Celery to use RabbitMQ broker, Redis backend/locks; set task_acks_late, retry/backoff defaults, dedup keys.
- Define DLQ/TTL policy in RabbitMQ and wire Celery routing to send failed tasks to DLQ after max retries.
- Add sample idempotent task (e.g., audit fan-out) with metrics/logging and retry behavior.
- Add monitoring endpoints/exporters for RabbitMQ (queue depth, DLQ depth) and Celery (success/failure/retry counts).

## Tests / Validation
- Unit: task idempotency helper, dedup key enforcement, retry/backoff config.
- Integration: publish task, observe processing; force failure to confirm retries and DLQ routing; confirm metrics emitted.
