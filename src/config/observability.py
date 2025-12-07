"""
Observability utilities: request context, metrics, and tracing.

This module provides:
- Thread-local request context storage for logging
- Prometheus-style metrics collection
- Audit logging helpers
"""

import contextvars
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger(__name__)

# Context variables for request-scoped data
_request_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "request_context", default={}
)


@dataclass
class RequestContext:
    """Request context data for logging and tracing."""

    request_id: str = ""
    trace_id: str = ""
    actor: str = ""
    org_id: str = ""
    path: str = ""
    method: str = ""
    user_agent: str = ""


def set_request_context(
    request_id: str = "",
    trace_id: str = "",
    actor: str = "",
    org_id: str = "",
    path: str = "",
    method: str = "",
    user_agent: str = "",
    **extra,
) -> None:
    """
    Set request context for the current async context.

    This context will be automatically included in all log messages
    within the same request/task.
    """
    context = {
        "request_id": request_id,
        "trace_id": trace_id or request_id,  # Fall back to request_id if no trace_id
        "actor": actor,
        "org_id": org_id,
        "path": path,
        "method": method,
        **extra,
    }
    # Filter out empty values
    context = {k: v for k, v in context.items() if v}
    _request_context.set(context)


def get_request_context() -> Dict[str, Any]:
    """Get the current request context."""
    return _request_context.get()


def clear_request_context() -> None:
    """Clear the request context."""
    _request_context.set({})


def bind_context(**kwargs) -> None:
    """Add additional context to the current request context."""
    context = _request_context.get().copy()
    context.update(kwargs)
    _request_context.set(context)


# Metrics storage (simple in-memory for development)
# In production, use prometheus_client or similar
@dataclass
class MetricsCollector:
    """Simple metrics collector for observability."""

    counters: Dict[str, int] = field(default_factory=dict)
    histograms: Dict[str, list] = field(default_factory=dict)
    gauges: Dict[str, float] = field(default_factory=dict)

    def inc(self, name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value

    def observe(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Record a histogram observation."""
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        # Keep only last 1000 observations
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create a metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary."""
        return {
            "counters": dict(self.counters),
            "histograms": {
                k: {
                    "count": len(v),
                    "sum": sum(v) if v else 0,
                    "avg": sum(v) / len(v) if v else 0,
                    "min": min(v) if v else 0,
                    "max": max(v) if v else 0,
                }
                for k, v in self.histograms.items()
            },
            "gauges": dict(self.gauges),
        }

    def to_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        # Counters
        for key, value in self.counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")

        # Histograms (simplified - just count, sum, avg)
        for key, values in self.histograms.items():
            base_name = key.split("{")[0]
            labels = key[len(base_name) :] if "{" in key else ""
            if values:
                lines.append(f"# TYPE {base_name} histogram")
                lines.append(f"{base_name}_count{labels} {len(values)}")
                lines.append(f"{base_name}_sum{labels} {sum(values)}")

        # Gauges
        for key, value in self.gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")

        return "\n".join(lines)


# Global metrics collector
metrics = MetricsCollector()


def timed(metric_name: str, labels: Dict[str, str] = None):
    """
    Decorator to measure function execution time.

    Usage:
        @timed("http_request_duration_seconds", {"handler": "my_view"})
        def my_view(request):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                metrics.observe(metric_name, duration, labels)

        return wrapper

    return decorator


def log_audit_decision(
    action: str,
    resource_kind: str,
    resource_id: str,
    result: str,
    policy_version: str = "",
    decision_id: str = "",
    decision_time_ms: float = 0,
    **extra,
) -> None:
    """
    Log an authorization decision for audit purposes.

    Args:
        action: The action being authorized (e.g., "read", "write")
        resource_kind: Type of resource (e.g., "document", "project")
        resource_id: ID of the resource
        result: Decision result ("allow" or "deny")
        policy_version: Version of the policy used
        decision_id: Unique ID for this decision
        decision_time_ms: Time taken for the decision in milliseconds
        **extra: Additional context to include
    """
    context = get_request_context()

    logger.info(
        "authz_decision",
        action=action,
        resource_kind=resource_kind,
        resource_id=resource_id,
        result=result,
        policy_version=policy_version,
        decision_id=decision_id,
        decision_time_ms=decision_time_ms,
        actor=context.get("actor", ""),
        org_id=context.get("org_id", ""),
        request_id=context.get("request_id", ""),
        **extra,
    )

    # Record metrics
    metrics.inc(
        "authz_decisions_total",
        labels={"action": action, "resource_kind": resource_kind, "result": result},
    )
    if decision_time_ms > 0:
        metrics.observe(
            "authz_decision_duration_seconds",
            decision_time_ms / 1000,
            labels={"action": action},
        )
