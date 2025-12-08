"""
Monitoring views for Celery tasks, RabbitMQ queues, and application metrics.

Protected endpoints require platform_admin role.
Health probes (readiness/liveness) remain public for Kubernetes.
"""

import os
import platform
import time
from datetime import datetime, timezone

import psutil
import structlog
from celery import current_app
from django.conf import settings
from django.core.cache import caches
from django.db import connection
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import IsPlatformAdmin
from config.observability import metrics

logger = structlog.get_logger(__name__)


class SystemOverviewView(APIView):
    """
    Comprehensive system overview for admin dashboard.
    Returns aggregated health status across all subsystems.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get complete system health overview."""
        start_time = time.time()

        overview = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "components": {},
            "summary": {
                "healthy": 0,
                "degraded": 0,
                "unhealthy": 0,
            },
        }

        # Check database
        db_status = self._check_database()
        overview["components"]["database"] = db_status
        self._update_summary(overview, db_status["status"])

        # Check cache (Redis)
        cache_status = self._check_cache()
        overview["components"]["cache"] = cache_status
        self._update_summary(overview, cache_status["status"])

        # Check Celery workers
        celery_status = self._check_celery()
        overview["components"]["celery"] = celery_status
        self._update_summary(overview, celery_status["status"])

        # Check message broker (RabbitMQ)
        broker_status = self._check_broker()
        overview["components"]["broker"] = broker_status
        self._update_summary(overview, broker_status["status"])

        # Check Cerbos
        cerbos_status = self._check_cerbos()
        overview["components"]["cerbos"] = cerbos_status
        self._update_summary(overview, cerbos_status["status"])

        # Determine overall status
        if overview["summary"]["unhealthy"] > 0:
            overview["overall_status"] = "unhealthy"
        elif overview["summary"]["degraded"] > 0:
            overview["overall_status"] = "degraded"

        overview["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return Response(overview)

    def _update_summary(self, overview, status):
        if status == "healthy":
            overview["summary"]["healthy"] += 1
        elif status == "degraded":
            overview["summary"]["degraded"] += 1
        else:
            overview["summary"]["unhealthy"] += 1

    def _check_database(self):
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                migration_count = cursor.fetchone()[0]
            latency = round((time.time() - start) * 1000, 2)

            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {
                    "engine": settings.DATABASES["default"]["ENGINE"],
                    "name": settings.DATABASES["default"]["NAME"],
                    "migrations_applied": migration_count,
                },
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def _check_cache(self):
        try:
            cache = caches["default"]
            start = time.time()

            # Write test
            test_key = f"health_check_{time.time()}"
            cache.set(test_key, "ok", 10)

            # Read test
            value = cache.get(test_key)
            cache.delete(test_key)

            latency = round((time.time() - start) * 1000, 2)

            if value != "ok":
                return {
                    "status": "degraded",
                    "error": "Cache read/write mismatch",
                    "latency_ms": latency,
                }

            # Get Redis info if available
            details = {"latency_ms": latency}
            try:
                if hasattr(cache, "client"):
                    client = cache.client.get_client()
                    if hasattr(client, "info"):
                        info = client.info()
                        details.update({
                            "used_memory": info.get("used_memory_human", "unknown"),
                            "connected_clients": info.get("connected_clients", 0),
                            "uptime_days": info.get("uptime_in_days", 0),
                            "redis_version": info.get("redis_version", "unknown"),
                        })
            except Exception:
                pass

            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": details,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def _check_celery(self):
        try:
            start = time.time()
            inspect = current_app.control.inspect(timeout=3.0)
            ping_result = inspect.ping()
            latency = round((time.time() - start) * 1000, 2)

            if not ping_result:
                return {
                    "status": "unhealthy",
                    "error": "No workers responding",
                    "latency_ms": latency,
                }

            workers = list(ping_result.keys())

            # Get active tasks
            active = inspect.active() or {}
            active_count = sum(len(tasks) for tasks in active.values())

            # Get reserved tasks
            reserved = inspect.reserved() or {}
            reserved_count = sum(len(tasks) for tasks in reserved.values())

            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {
                    "worker_count": len(workers),
                    "workers": workers,
                    "active_tasks": active_count,
                    "reserved_tasks": reserved_count,
                },
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def _check_broker(self):
        try:
            start = time.time()
            with current_app.connection_or_acquire() as conn:
                conn.ensure_connection(max_retries=1)
                transport = conn.transport.driver_type
            latency = round((time.time() - start) * 1000, 2)

            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {
                    "transport": transport,
                    "broker_url": self._mask_url(settings.CELERY_BROKER_URL),
                },
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    def _check_cerbos(self):
        try:
            from api.cerbos_client import get_client
            start = time.time()
            client = get_client()
            latency = round((time.time() - start) * 1000, 2)

            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {
                    "url": getattr(settings, "CERBOS_URL", "not configured"),
                },
            }
        except Exception as e:
            return {
                "status": "degraded",
                "error": str(e),
                "note": "Authorization may be impacted",
            }

    def _mask_url(self, url):
        """Mask credentials in URLs."""
        if not url:
            return "not configured"
        if "@" in url:
            # Mask password in amqp://user:pass@host
            parts = url.split("@")
            return f"***@{parts[-1]}"
        return url


class CeleryHealthView(APIView):
    """Health check endpoint for Celery workers."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Check if Celery workers are responding with detailed info."""
        try:
            inspect = current_app.control.inspect(timeout=5.0)
            ping_result = inspect.ping()

            if not ping_result:
                return Response(
                    {
                        "status": "unhealthy",
                        "error": "No workers responding",
                        "active_workers": 0,
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            workers = list(ping_result.keys())

            # Get additional worker info
            stats = inspect.stats() or {}
            active = inspect.active() or {}

            worker_details = []
            for worker_name in workers:
                worker_stats = stats.get(worker_name, {})
                worker_active = active.get(worker_name, [])

                pool_info = worker_stats.get("pool", {})
                worker_details.append({
                    "name": worker_name,
                    "status": "online",
                    "concurrency": pool_info.get("max-concurrency", 0),
                    "active_tasks": len(worker_active),
                    "pool_type": pool_info.get("implementation", "unknown"),
                    "prefetch": worker_stats.get("prefetch_count", 0),
                })

            return Response({
                "status": "healthy",
                "active_workers": len(workers),
                "workers": worker_details,
            })
        except Exception as e:
            logger.error("celery_health_check_failed", error=str(e))
            return Response(
                {"status": "unhealthy", "error": str(e), "active_workers": 0},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class CeleryStatsView(APIView):
    """Detailed statistics for Celery workers and tasks."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get comprehensive Celery worker statistics."""
        try:
            inspect = current_app.control.inspect(timeout=3.0)

            stats = inspect.stats() or {}
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}
            scheduled = inspect.scheduled() or {}
            registered = inspect.registered() or {}

            workers = {}
            for worker_name, worker_stats in stats.items():
                pool_info = worker_stats.get("pool", {})
                broker_info = worker_stats.get("broker", {})

                workers[worker_name] = {
                    "active": len(active.get(worker_name, [])),
                    "reserved": len(reserved.get(worker_name, [])),
                    "scheduled": len(scheduled.get(worker_name, [])),
                    "concurrency": pool_info.get("max-concurrency", 0),
                    "pool_type": pool_info.get("implementation", "unknown"),
                    "broker_transport": broker_info.get("transport", "unknown"),
                    "prefetch_count": worker_stats.get("prefetch_count", 0),
                    "registered_tasks": len(registered.get(worker_name, [])),
                }

            # Aggregate totals
            total_active = sum(w["active"] for w in workers.values())
            total_reserved = sum(w["reserved"] for w in workers.values())
            total_scheduled = sum(w["scheduled"] for w in workers.values())

            return Response({
                "workers": workers,
                "worker_count": len(workers),
                "totals": {
                    "active": total_active,
                    "reserved": total_reserved,
                    "scheduled": total_scheduled,
                },
            })
        except Exception as e:
            logger.error("celery_stats_failed", error=str(e))
            return Response(
                {"error": str(e), "workers": {}, "worker_count": 0},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class QueueStatsView(APIView):
    """Statistics for RabbitMQ queues."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get queue depths and statistics."""
        try:
            queues = {}

            # Get queue lengths using broker connection
            with current_app.connection_or_acquire() as conn:
                # Check common queues
                queue_names = ["celery", "default", "dlq", "high_priority", "low_priority"]

                for queue_name in queue_names:
                    try:
                        channel = conn.default_channel
                        queue = channel.queue_declare(queue_name, passive=True)
                        queues[queue_name] = {
                            "messages": queue.message_count,
                            "consumers": queue.consumer_count,
                            "status": "active",
                        }
                    except Exception:
                        # Queue doesn't exist yet - that's ok
                        pass

            # Get active queues from workers
            inspect = current_app.control.inspect(timeout=2.0)
            active_queues = inspect.active_queues() or {}

            active_queue_names = set()
            for worker_queues in active_queues.values():
                for q in worker_queues:
                    active_queue_names.add(q.get("name", ""))

            return Response({
                "queues": queues,
                "active_queue_names": list(active_queue_names),
                "queue_count": len(queues),
            })
        except Exception as e:
            logger.error("queue_stats_failed", error=str(e))
            return Response(
                {"error": str(e), "queues": {}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class TaskMetricsView(APIView):
    """Metrics for registered Celery tasks."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get task registration and execution info."""
        try:
            inspect = current_app.control.inspect(timeout=2.0)

            registered = inspect.registered() or {}
            active = inspect.active() or {}
            reserved = inspect.reserved() or {}

            # Flatten registered tasks
            all_tasks = set()
            for worker_tasks in registered.values():
                all_tasks.update(worker_tasks)

            # Get currently running tasks
            running_tasks = []
            for worker_name, tasks in active.items():
                for task in tasks:
                    running_tasks.append({
                        "id": task.get("id"),
                        "name": task.get("name"),
                        "worker": worker_name,
                        "started": task.get("time_start"),
                    })

            return Response({
                "registered_tasks": sorted(list(all_tasks)),
                "registered_count": len(all_tasks),
                "running_tasks": running_tasks,
                "running_count": len(running_tasks),
            })
        except Exception as e:
            logger.error("task_metrics_failed", error=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class ServerMetricsView(APIView):
    """Server resource metrics (CPU, memory, disk)."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get server resource utilization."""
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)

            # Memory info
            memory = psutil.virtual_memory()

            # Disk info
            disk = psutil.disk_usage("/")

            # Process info
            process = psutil.Process()
            process_memory = process.memory_info()

            return Response({
                "server": {
                    "hostname": platform.node(),
                    "platform": platform.system(),
                    "python_version": platform.python_version(),
                    "uptime_seconds": int(time.time() - psutil.boot_time()),
                },
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_avg_1m": round(load_avg[0], 2),
                    "load_avg_5m": round(load_avg[1], 2),
                    "load_avg_15m": round(load_avg[2], 2),
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent": round(disk.percent, 1),
                },
                "process": {
                    "pid": process.pid,
                    "memory_mb": round(process_memory.rss / (1024**2), 2),
                    "threads": process.num_threads(),
                },
            })
        except Exception as e:
            logger.error("server_metrics_failed", error=str(e))
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PrometheusMetricsView(APIView):
    """Prometheus-compatible metrics endpoint."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Export metrics in Prometheus text format."""
        try:
            self._collect_system_metrics()
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
        try:
            metrics.set_gauge("db_connection_count", len(connection.queries))
        except Exception:
            pass

        try:
            cache = caches["default"]
            if hasattr(cache, "client"):
                client = cache.client.get_client()
                if hasattr(client, "info"):
                    info = client.info()
                    metrics.set_gauge("redis_used_memory_bytes", info.get("used_memory", 0))
                    metrics.set_gauge("redis_connected_clients", info.get("connected_clients", 0))
        except Exception:
            pass


class AppMetricsView(APIView):
    """Application metrics in JSON format."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        """Get all application metrics."""
        return Response(metrics.get_metrics())


# ============================================================================
# Health Probes - Keep public for Kubernetes
# ============================================================================

class ReadinessView(APIView):
    """
    Kubernetes readiness probe endpoint.

    PUBLIC - No auth required for K8s probes.
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

    PUBLIC - No auth required for K8s probes.
    Checks if the application is alive (not deadlocked).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """Check application liveness."""
        return Response({"status": "alive"})
