"""
Redis-based lockout event tracking for mass lockout detection.

This module provides utilities for tracking account lockout events in a time-based
sliding window using Redis sorted sets. It's used to detect mass lockout events
that may indicate credential stuffing attacks.
"""

from typing import Dict, List, Optional

import structlog
from django.conf import settings
from django.core.cache import caches
from django.utils import timezone

logger = structlog.get_logger(__name__)


def increment_lockout_count(
    username: str,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    source: str = "unknown",
) -> int:
    """
    Add a lockout event to the sliding window counter.

    Uses Redis sorted set to track lockout events with timestamps as scores,
    allowing efficient time-based windowing and automatic cleanup.

    Args:
        username: The username that was locked out
        email: The email address (optional)
        ip_address: The IP address of failed attempts (optional)
        source: Source of the lockout (e.g., 'django-axes', 'local-auth')

    Returns:
        Current count of lockouts in the time window
    """
    cache = caches["default"]
    time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES
    time_window_seconds = time_window_minutes * 60

    # Keys for tracking
    events_key = f"lockout_events:{time_window_minutes}m"
    details_key = f"lockout_details:{time_window_minutes}m"

    current_timestamp = timezone.now().timestamp()
    cutoff_timestamp = current_timestamp - time_window_seconds

    try:
        # Get the raw Redis client for sorted set operations
        redis_client = cache.client.get_client()

        # Add current lockout event to sorted set with timestamp as score
        # Member is a unique identifier combining timestamp and username
        member = f"{current_timestamp}:{username}"
        redis_client.zadd(events_key, {member: current_timestamp})

        # Store detailed information about this lockout for admin alerts
        # Use hash to store lockout details
        detail_key = f"{details_key}:{member}"
        lockout_details = {
            "username": username,
            "email": email or "",
            "ip_address": ip_address or "",
            "source": source,
            "lockout_time": timezone.now().isoformat(),
        }

        # Store details as individual fields in a hash
        redis_client.hset(detail_key, mapping=lockout_details)

        # Set expiry on the detail key (slightly longer than window for safety)
        redis_client.expire(detail_key, time_window_seconds + 300)

        # Remove old events outside the time window
        redis_client.zremrangebyscore(events_key, "-inf", cutoff_timestamp)

        # Set expiry on the sorted set key itself
        redis_client.expire(events_key, time_window_seconds + 300)

        # Count current events in window
        count = redis_client.zcard(events_key)

        logger.info(
            "lockout_event_tracked",
            username=username,
            ip_address=ip_address,
            source=source,
            count=count,
            time_window_minutes=time_window_minutes,
        )

        return count

    except Exception as e:
        logger.error(
            "lockout_tracking_increment_failed",
            error=str(e),
            username=username,
        )
        # Return 0 on error to prevent blocking the lockout process
        return 0


def get_lockout_count(time_window_minutes: Optional[int] = None) -> int:
    """
    Get the current count of lockouts in the time window.

    Args:
        time_window_minutes: Optional time window in minutes (defaults to LOCKOUT_MASS_WINDOW_MINUTES)

    Returns:
        Number of lockout events in the time window
    """
    if time_window_minutes is None:
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES

    cache = caches["default"]
    events_key = f"lockout_events:{time_window_minutes}m"
    time_window_seconds = time_window_minutes * 60
    cutoff_timestamp = timezone.now().timestamp() - time_window_seconds

    try:
        redis_client = cache.client.get_client()

        # Remove expired events first
        redis_client.zremrangebyscore(events_key, "-inf", cutoff_timestamp)

        # Count remaining events
        count = redis_client.zcard(events_key)

        logger.info(
            "lockout_count_retrieved",
            count=count,
            time_window_minutes=time_window_minutes,
        )

        return count

    except Exception as e:
        logger.error(
            "lockout_tracking_count_failed",
            error=str(e),
            time_window_minutes=time_window_minutes,
        )
        return 0


def get_affected_accounts(time_window_minutes: Optional[int] = None) -> List[Dict[str, str]]:
    """
    Get detailed information about accounts locked in the time window.

    This is used to populate admin alert emails with the list of affected accounts.

    Args:
        time_window_minutes: Optional time window in minutes (defaults to LOCKOUT_MASS_WINDOW_MINUTES)

    Returns:
        List of dictionaries containing account information:
            - username: Account username
            - email: Account email
            - lockout_time: When the lockout occurred
            - ip_address: IP address of failed attempts (if available)
            - source: Source of the lockout
    """
    if time_window_minutes is None:
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES

    cache = caches["default"]
    events_key = f"lockout_events:{time_window_minutes}m"
    details_key = f"lockout_details:{time_window_minutes}m"
    time_window_seconds = time_window_minutes * 60
    cutoff_timestamp = timezone.now().timestamp() - time_window_seconds

    affected_accounts = []

    try:
        redis_client = cache.client.get_client()

        # Get all lockout event members in the time window
        # Returns list of (member, score) tuples
        events = redis_client.zrangebyscore(
            events_key,
            cutoff_timestamp,
            "+inf",
            withscores=False,
        )

        # Retrieve details for each event
        for event_member in events:
            # event_member format: "timestamp:username"
            detail_key = f"{details_key}:{event_member.decode('utf-8') if isinstance(event_member, bytes) else event_member}"

            # Get all fields from the hash
            details = redis_client.hgetall(detail_key)

            if details:
                # Decode bytes to strings
                account_info = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in details.items()
                }
                affected_accounts.append(account_info)

        logger.info(
            "affected_accounts_retrieved",
            count=len(affected_accounts),
            time_window_minutes=time_window_minutes,
        )

        return affected_accounts

    except Exception as e:
        logger.error(
            "lockout_tracking_accounts_failed",
            error=str(e),
            time_window_minutes=time_window_minutes,
        )
        return []


def get_ip_summary(time_window_minutes: Optional[int] = None) -> List[Dict[str, any]]:
    """
    Get a summary of IP addresses involved in lockout events.

    Groups lockouts by IP address to help identify attack patterns.

    Args:
        time_window_minutes: Optional time window in minutes (defaults to LOCKOUT_MASS_WINDOW_MINUTES)

    Returns:
        List of dictionaries containing IP summary:
            - address: IP address
            - count: Number of lockouts from this IP
    """
    affected_accounts = get_affected_accounts(time_window_minutes)

    # Count lockouts by IP address
    ip_counts: Dict[str, int] = {}

    for account in affected_accounts:
        ip_address = account.get("ip_address", "").strip()
        if ip_address:
            ip_counts[ip_address] = ip_counts.get(ip_address, 0) + 1

    # Convert to list of dicts and sort by count (descending)
    ip_summary = [
        {"address": ip, "count": count}
        for ip, count in ip_counts.items()
    ]
    ip_summary.sort(key=lambda x: x["count"], reverse=True)

    logger.info(
        "ip_summary_generated",
        unique_ips=len(ip_summary),
        total_lockouts=len(affected_accounts),
    )

    return ip_summary


def clear_lockout_tracking(time_window_minutes: Optional[int] = None) -> bool:
    """
    Clear all lockout tracking data for the specified time window.

    This is primarily used for testing and manual incident response.

    Args:
        time_window_minutes: Optional time window in minutes (defaults to LOCKOUT_MASS_WINDOW_MINUTES)

    Returns:
        True if successful, False otherwise
    """
    if time_window_minutes is None:
        time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES

    cache = caches["default"]
    events_key = f"lockout_events:{time_window_minutes}m"
    details_key = f"lockout_details:{time_window_minutes}m"

    try:
        redis_client = cache.client.get_client()

        # Get all event members to delete their details
        events = redis_client.zrange(events_key, 0, -1)

        # Delete all detail keys
        for event_member in events:
            detail_key = f"{details_key}:{event_member.decode('utf-8') if isinstance(event_member, bytes) else event_member}"
            redis_client.delete(detail_key)

        # Delete the events sorted set
        redis_client.delete(events_key)

        logger.warning(
            "lockout_tracking_cleared",
            time_window_minutes=time_window_minutes,
            events_cleared=len(events),
        )

        return True

    except Exception as e:
        logger.error(
            "lockout_tracking_clear_failed",
            error=str(e),
            time_window_minutes=time_window_minutes,
        )
        return False
