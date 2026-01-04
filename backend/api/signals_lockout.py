"""
Signal handlers for account lockout notifications.

This module connects to django-axes signals to automatically send notifications
when user accounts are locked due to failed login attempts.
"""

from typing import Any

import structlog
from axes.signals import user_locked_out
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.dispatch import receiver
from django.utils import timezone

from api.audit import log_audit

logger = structlog.get_logger(__name__)

User = get_user_model()


@receiver(user_locked_out)
def handle_user_locked_out(sender, request, username: str, ip_address: str, **kwargs: Any) -> None:
    """
    Handle django-axes user_locked_out signal.

    This signal is triggered when a user's account is locked due to exceeding
    the AXES_FAILURE_LIMIT. It sends a notification email to the user and
    creates an audit log entry.

    Args:
        sender: The sender of the signal (axes)
        request: The HTTP request object
        username: The username that was locked out
        ip_address: The IP address of the failed login attempts
        **kwargs: Additional keyword arguments from the signal
    """
    from api.tasks_lockout import send_lockout_notification_task, check_mass_lockout_task

    logger.info(
        "user_locked_out_signal_received",
        username=username,
        ip_address=ip_address,
    )

    # Try to get the user object
    try:
        user = User.objects.get(username=username)
        user_email = user.email
        user_id = str(user.id)
        first_name = getattr(user, 'first_name', '') or username
    except User.DoesNotExist:
        logger.warning(
            "user_not_found_for_lockout",
            username=username,
            ip_address=ip_address,
        )
        # Still proceed with limited information
        user = None
        user_email = None
        user_id = username  # Use username as fallback ID
        first_name = username

    # Calculate lockout duration from settings
    lockout_hours = settings.AXES_COOLOFF_TIME
    lockout_duration = f"{lockout_hours} hour{'s' if lockout_hours != 1 else ''}"
    failure_limit = settings.AXES_FAILURE_LIMIT

    # Calculate unlock time
    unlock_time = timezone.now() + timezone.timedelta(hours=lockout_hours)

    # Prepare lockout data for email
    lockout_data = {
        "lockout_duration": lockout_duration,
        "failure_count": failure_limit,
        "ip_address": ip_address,
        "lockout_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "unlock_time": unlock_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "reset_password_url": f"{settings.FRONTEND_URL}/reset-password" if hasattr(settings, 'FRONTEND_URL') else None,
    }

    # Prepare user data for email
    user_data = {
        "first_name": first_name,
        "email": user_email or username,
        "username": username,
    }

    # Create audit log entry for the lockout
    log_audit(
        action="account_locked",
        resource_type="User",
        resource_id=user_id,
        actor_id=user_id,  # The user is the actor (attempted login)
        actor_email=user_email,
        metadata={
            "ip_address": ip_address,
            "failure_count": failure_limit,
            "lockout_duration_hours": lockout_hours,
            "unlock_time": unlock_time.isoformat(),
            "source": "django-axes",
        },
    )

    logger.info(
        "account_lockout_audit_logged",
        user_id=user_id,
        username=username,
        ip_address=ip_address,
    )

    # Send notification email asynchronously (if user has email)
    if user_email and settings.LOCKOUT_NOTIFICATION_ENABLED:
        send_lockout_notification_task.delay(
            user_email=user_email,
            user_data=user_data,
            lockout_data=lockout_data,
        )
        logger.info(
            "lockout_notification_queued",
            user_email=user_email,
            ip_address=ip_address,
        )
    else:
        logger.info(
            "lockout_notification_skipped",
            username=username,
            reason="no_email" if not user_email else "disabled",
        )

    # Increment mass lockout counter in Redis for tracking
    # This uses a sorted set to track lockouts within the time window
    cache = caches["default"]
    time_window_seconds = settings.LOCKOUT_MASS_WINDOW_MINUTES * 60

    # Use a sorted set key for tracking lockouts with timestamps
    lockout_tracking_key = f"lockout_events:{settings.LOCKOUT_MASS_WINDOW_MINUTES}m"

    # Add current lockout to tracking with current timestamp as score
    # Note: In phase 3, this will be replaced with proper lockout_tracking.py utilities
    current_timestamp = timezone.now().timestamp()

    # For now, we'll use a simple counter that expires
    # Phase 3 will implement proper sorted set tracking
    lockout_counter_key = f"lockout_count:{settings.LOCKOUT_MASS_WINDOW_MINUTES}m"

    try:
        # Increment counter
        current_count = cache.get(lockout_counter_key, 0)
        current_count += 1
        cache.set(lockout_counter_key, current_count, time_window_seconds)

        logger.info(
            "mass_lockout_counter_incremented",
            count=current_count,
            threshold=settings.LOCKOUT_MASS_THRESHOLD,
            time_window_minutes=settings.LOCKOUT_MASS_WINDOW_MINUTES,
        )

        # Check if we've crossed the mass lockout threshold
        # This will trigger admin alerts if needed
        check_mass_lockout_task.delay(current_count=current_count)

    except Exception as e:
        logger.error(
            "mass_lockout_tracking_failed",
            error=str(e),
            username=username,
        )
        # Don't fail the whole signal handler if tracking fails
