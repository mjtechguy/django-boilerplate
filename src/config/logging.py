"""
Structured logging configuration with PII redaction and context binding.

This module provides:
- Structlog processors for request context (request_id, trace_id, actor, org_id)
- PII redaction for sensitive fields
- Audit logging with policy version and decision info
"""

import re
from typing import Any

import structlog
from django.conf import settings

# Fields that should be redacted in logs
PII_FIELDS = {
    "email",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "credit_card",
    "ssn",
    "social_security",
    "phone",
    "phone_number",
    "address",
    "ip_address",
    "ip",
}

# Regex patterns for PII detection
PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
    (re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"), "[SSN_REDACTED]"),
    (re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"), "[CARD_REDACTED]"),
]


def redact_value(value: Any, field_name: str = "") -> Any:
    """
    Redact PII from a value based on field name or content patterns.

    Args:
        value: The value to potentially redact
        field_name: The name of the field (used for field-based redaction)

    Returns:
        The redacted value or original if no redaction needed
    """
    # Check if field name indicates PII
    field_lower = field_name.lower()
    for pii_field in PII_FIELDS:
        if pii_field in field_lower:
            if isinstance(value, str):
                return "[REDACTED]"
            elif isinstance(value, dict):
                return {k: "[REDACTED]" for k in value}
            return "[REDACTED]"

    # Check string values for PII patterns
    if isinstance(value, str):
        result = value
        for pattern, replacement in PII_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    return value


def redact_dict(data: dict, depth: int = 0, max_depth: int = 5) -> dict:
    """
    Recursively redact PII from a dictionary.

    Args:
        data: Dictionary to redact
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Dictionary with PII redacted
    """
    if depth > max_depth:
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = redact_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                redact_dict(v, depth + 1, max_depth)
                if isinstance(v, dict)
                else redact_value(v, key)
                for v in value
            ]
        else:
            result[key] = redact_value(value, key)
    return result


def pii_redactor(logger, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that redacts PII from log events.

    Respects AUDIT_PII_POLICY setting:
    - 'mask': Replace PII with [REDACTED] (default)
    - 'hash': Replace PII with hashed value (not implemented, falls back to mask)
    - 'drop': Remove PII fields entirely
    """
    pii_policy = getattr(settings, "AUDIT_PII_POLICY", "mask")

    if pii_policy == "drop":
        # Remove PII fields entirely
        for field in list(event_dict.keys()):
            field_lower = field.lower()
            for pii_field in PII_FIELDS:
                if pii_field in field_lower:
                    del event_dict[field]
                    break
    else:
        # Mask PII (default behavior)
        for key in list(event_dict.keys()):
            if key in ("event", "message", "timestamp", "level"):
                continue
            event_dict[key] = redact_value(event_dict[key], key)

    return event_dict


def add_request_context(logger, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that adds request context from thread-local storage.

    Adds: request_id, trace_id, actor, org_id, path, method
    """
    from config.observability import get_request_context

    context = get_request_context()
    if context:
        event_dict.update(context)
    return event_dict


def add_service_info(logger, method_name: str, event_dict: dict) -> dict:
    """
    Structlog processor that adds service identification info.
    """
    event_dict["service"] = "django-api"
    event_dict["environment"] = getattr(settings, "ENVIRONMENT", "development")
    return event_dict


def configure_structlog():
    """
    Configure structlog with all processors for production logging.

    Call this from settings.py after Django settings are loaded.
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        add_service_info,
        add_request_context,
        pii_redactor,
        structlog.processors.EventRenamer("message"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(settings, "LOG_LEVEL", "INFO").upper()
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """
    Get a structlog logger with the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("message", extra_field="value")
    """
    return structlog.get_logger(name)
