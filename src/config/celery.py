import os

import structlog
from celery import Celery
from celery.signals import task_failure, task_retry, task_success
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

logger = structlog.get_logger(__name__)

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Define queues with DLQ support
default_exchange = Exchange("default", type="direct")
dlq_exchange = Exchange("dlq", type="direct")

app.conf.task_queues = (
    Queue("default", default_exchange, routing_key="default"),
    Queue("dlq", dlq_exchange, routing_key="dlq"),
)

app.autodiscover_tasks()


# Task lifecycle signals for metrics/logging
@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    """Log successful task completion."""
    logger.info(
        "task_success",
        task=sender.name if sender else "unknown",
        task_id=kwargs.get("task_id"),
    )


@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    """Log task failure."""
    logger.error(
        "task_failure",
        task=sender.name if sender else "unknown",
        task_id=task_id,
        exception=str(exception),
    )


@task_retry.connect
def on_task_retry(sender=None, reason=None, **kwargs):
    """Log task retry."""
    logger.warning(
        "task_retry",
        task=sender.name if sender else "unknown",
        task_id=kwargs.get("request", {}).get("id"),
        reason=str(reason),
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
