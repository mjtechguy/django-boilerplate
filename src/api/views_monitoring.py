"""
Monitoring views for Celery tasks, RabbitMQ queues, and application metrics.
"""

import structlog
from celery import current_app
from django.core.cache import caches
from django.db import connection
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.observability import metrics

logger = structlog.get_logger(__name__)


class CeleryHealthView(APIView):
    """Health check endpoint for Celery workers."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Check if Celery workers are responding."""
        try:
            # Ping workers with a timeout
            inspect = current_app.control.inspect(timeout=5.0)
            ping_result = inspect.ping()

            if ping_result:
                workers = list(ping_result.keys())
                return Response(
                    {
                        "status": "healthy",
                        "workers": workers,
                        "worker_count": len(workers),
                    }
                )
            else:
                return Response(
                    {"status": "unhealthy", "error": "No workers responding"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        except Exception as e:
            logger.error("celery_health_check_failed", error=str(e))
            return Response(
                {"status": "unhealthy", "error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class CeleryStatsView(APIView):
    """Statistics endpoint for Celery workers and tasks."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Get Celery worker statistics."""
        try:
            inspect = current_app.control.inspect(timeout=2.0)

            # Get stats only - most essential info
            stats = inspect.stats() or {}

            # Worker details
            workers = []
            for worker_name, worker_stats in stats.items():
                workers.append(
                    {
                        "name": worker_name,
                        "pool": worker_stats.get("pool", {}).get("max-concurrency"),
                        "broker": worker_stats.get("broker", {}).get("transport"),
                        "prefetch_count": worker_stats.get("prefetch_count"),
                    }
                )

            return Response(
                {
                    "workers": workers,
                    "worker_count": len(workers),
                }
            )
        except Exception as e:
            logger.error("celery_stats_failed", error=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class QueueStatsView(APIView):
    """Statistics endpoint for RabbitMQ queues via Celery."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Get queue depths and statistics."""
        try:
            # Get active queues from Celery
            inspect = current_app.control.inspect(timeout=5.0)
            active_queues = inspect.active_queues() or {}

            # Collect queue info
            queues = {}
            for worker, worker_queues in active_queues.items():
                for q in worker_queues:
                    queue_name = q.get("name")
                    if queue_name and queue_name not in queues:
                        queues[queue_name] = {
                            "name": queue_name,
                            "exchange": q.get("exchange", {}).get("name"),
                            "routing_key": q.get("routing_key"),
                        }

            # Get queue lengths using broker connection
            queue_stats = []
            with current_app.connection_or_acquire() as conn:
                for queue_name in ["default", "dlq"]:
                    try:
                        channel = conn.default_channel
                        # Declare queue passively to get message count
                        queue = channel.queue_declare(queue_name, passive=True)
                        queue_stats.append(
                            {
                                "name": queue_name,
                                "message_count": queue.message_count,
                                "consumer_count": queue.consumer_count,
                            }
                        )
                    except Exception:
                        # Queue might not exist yet
                        queue_stats.append(
                            {
                                "name": queue_name,
                                "message_count": 0,
                                "consumer_count": 0,
                                "note": "Queue may not exist yet",
                            }
                        )

            return Response(
                {
                    "queues": queue_stats,
                    "active_queues": list(queues.values()),
                }
            )
        except Exception as e:
            logger.error("queue_stats_failed", error=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class TaskMetricsView(APIView):
    """Metrics endpoint for task execution statistics."""

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Get task metrics from Celery events.

        Note: This provides a basic snapshot. For production use,
        consider using Prometheus + celery-exporter for time-series metrics.
        """
        try:
            inspect = current_app.control.inspect(timeout=2.0)

            # Get registered tasks only
            registered = inspect.registered() or {}

            # Flatten registered tasks across workers
            all_tasks = set()
            for worker_tasks in registered.values():
                all_tasks.update(worker_tasks)

            return Response(
                {
                    "registered_tasks": sorted(list(all_tasks)),
                    "registered_count": len(all_tasks),
                }
            )
        except Exception as e:
            logger.error("task_metrics_failed", error=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class PrometheusMetricsView(APIView):
    """
    Prometheus-compatible metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Export metrics in Prometheus text format."""
        try:
            # Add some system metrics
            self._collect_system_metrics()

            # Get Prometheus-formatted metrics
            prometheus_output = metrics.to_prometheus_format()

            return HttpResponse(
                prometheus_output,
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )
        except Exception as e:
            logger.error("metrics_export_failed", error=str(e))
            return HttpResponse(
                f"# Error: {e}",
                content_type="text/plain",
                status=500,
            )

    def _collect_system_metrics(self):
        """Collect system metrics before export."""
        # Database connection pool (if using connection pooling)
        try:
            metrics.set_gauge("db_connection_count", len(connection.queries))
        except Exception:
            pass

        # Cache stats
        try:
            cache = caches["default"]
            # Try to get cache stats if available (redis)
            if hasattr(cache, "client"):
                client = cache.client.get_client()
                if hasattr(client, "info"):
                    info = client.info()
                    metrics.set_gauge("redis_used_memory_bytes", info.get("used_memory", 0))
                    metrics.set_gauge("redis_connected_clients", info.get("connected_clients", 0))
                    metrics.set_gauge(
                        "redis_keys_count",
                        info.get("db0", {}).get("keys", 0)
                        if isinstance(info.get("db0"), dict)
                        else 0,
                    )
        except Exception:
            pass


class AppMetricsView(APIView):
    """
    Application metrics endpoint (JSON format).

    Returns all collected metrics in JSON format for debugging.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Get all application metrics."""
        return Response(metrics.get_metrics())


class ReadinessView(APIView):
    """
    Kubernetes readiness probe endpoint.

    Checks if the application is ready to receive traffic.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Check application readiness."""
        checks = {}
        all_ready = True

        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = {"status": "ready"}
        except Exception as e:
            checks["database"] = {"status": "not_ready", "error": str(e)}
            all_ready = False

        # Check cache
        try:
            cache = caches["default"]
            cache.set("readiness_check", "ok", 1)
            if cache.get("readiness_check") != "ok":
                raise Exception("Cache read/write failed")
            checks["cache"] = {"status": "ready"}
        except Exception as e:
            checks["cache"] = {"status": "not_ready", "error": str(e)}
            all_ready = False

        # Check Cerbos (optional)
        try:
            from api.cerbos_client import get_client

            get_client()
            checks["cerbos"] = {"status": "ready"}
        except Exception as e:
            checks["cerbos"] = {"status": "degraded", "error": str(e)}
            # Don't fail readiness for Cerbos - it's checked per-request

        status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "ready" if all_ready else "not_ready",
                "checks": checks,
            },
            status=status_code,
        )


class LivenessView(APIView):
    """
    Kubernetes liveness probe endpoint.

    Checks if the application is alive (not deadlocked).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Check application liveness."""
        return Response({"status": "alive"})
