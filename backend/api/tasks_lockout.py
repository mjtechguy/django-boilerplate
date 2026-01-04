"""
Celery tasks for account lockout notifications and mass lockout detection.
"""

import structlog
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = structlog.get_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def send_lockout_notification_task(
    self,
    user_email: str,
    user_data: dict,
    lockout_data: dict,
) -> dict:
    """
    Send account lockout notification email to affected user.

    This task sends an email to a user whose account has been locked due to
    failed login attempts. It uses the existing send_email infrastructure
    and includes security guidance.

    Args:
        user_email: Email address of the locked-out user
        user_data: Dictionary containing user information (first_name, email, etc.)
        lockout_data: Dictionary containing lockout details:
            - lockout_duration: Human-readable lockout duration (e.g., "1 hour")
            - failure_count: Number of failed attempts
            - ip_address: IP address of failed attempts (optional)
            - lockout_time: Timestamp of lockout
            - unlock_time: When the account will be unlocked
            - reset_password_url: URL for password reset (optional)

    Returns:
        Dictionary with task status and delivery information
    """
    from api.email import send_email

    if not settings.LOCKOUT_NOTIFICATION_ENABLED:
        logger.info(
            "lockout_notification_disabled",
            task_id=self.request.id,
            user_email=user_email,
        )
        return {"status": "disabled", "task_id": self.request.id}

    logger.info(
        "lockout_notification_start",
        task_id=self.request.id,
        user_email=user_email,
        ip_address=lockout_data.get("ip_address"),
    )

    # Prepare email context
    context = {
        "user": user_data,
        **lockout_data,
    }

    # Send the email
    result = send_email(
        to=[user_email],
        subject="Account Temporarily Locked - Security Alert",
        template="email/account_lockout.html",
        context=context,
    )

    if result.get("success"):
        logger.info(
            "lockout_notification_sent",
            task_id=self.request.id,
            user_email=user_email,
            ip_address=lockout_data.get("ip_address"),
        )
    else:
        logger.error(
            "lockout_notification_failed",
            task_id=self.request.id,
            user_email=user_email,
            error=result.get("error"),
        )

    return {
        "status": "success" if result.get("success") else "failed",
        "task_id": self.request.id,
        "user_email": user_email,
        "result": result,
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def send_admin_lockout_alert_task(
    self,
    lockout_count: int,
    time_window_minutes: int,
    affected_accounts: list,
    ip_summary: list = None,
) -> dict:
    """
    Send mass lockout alert to admin email addresses.

    This task notifies administrators when a mass lockout event is detected,
    which may indicate a credential stuffing attack or other security incident.

    Args:
        lockout_count: Number of accounts locked in the time window
        time_window_minutes: The time window in minutes
        affected_accounts: List of dicts with account info:
            - username: Account username
            - email: Account email
            - lockout_time: When the account was locked
        ip_summary: Optional list of dicts with IP address info:
            - address: IP address
            - count: Number of attempts from this IP

    Returns:
        Dictionary with task status and delivery information
    """
    from api.email import send_email

    if not settings.LOCKOUT_NOTIFICATION_ENABLED:
        logger.info(
            "admin_alert_disabled",
            task_id=self.request.id,
            lockout_count=lockout_count,
        )
        return {"status": "disabled", "task_id": self.request.id}

    admin_emails = settings.LOCKOUT_ADMIN_EMAILS
    if not admin_emails:
        logger.warning(
            "admin_alert_no_recipients",
            task_id=self.request.id,
            lockout_count=lockout_count,
        )
        return {
            "status": "skipped",
            "task_id": self.request.id,
            "reason": "No admin emails configured",
        }

    logger.info(
        "admin_alert_start",
        task_id=self.request.id,
        lockout_count=lockout_count,
        time_window_minutes=time_window_minutes,
        admin_count=len(admin_emails),
    )

    # Prepare email context
    context = {
        "lockout_count": lockout_count,
        "time_window": time_window_minutes,
        "detection_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "threshold": settings.LOCKOUT_MASS_THRESHOLD,
        "affected_accounts": affected_accounts,
        "ip_summary": ip_summary,
    }

    # Send the email
    result = send_email(
        to=admin_emails,
        subject=f"🚨 Mass Account Lockout Alert - {lockout_count} Accounts Affected",
        template="email/mass_lockout_alert.html",
        context=context,
    )

    if result.get("success"):
        logger.info(
            "admin_alert_sent",
            task_id=self.request.id,
            lockout_count=lockout_count,
            admin_count=len(admin_emails),
        )
    else:
        logger.error(
            "admin_alert_failed",
            task_id=self.request.id,
            lockout_count=lockout_count,
            error=result.get("error"),
        )

    return {
        "status": "success" if result.get("success") else "failed",
        "task_id": self.request.id,
        "lockout_count": lockout_count,
        "admin_count": len(admin_emails),
        "result": result,
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def check_mass_lockout_task(self, current_count: int = None) -> dict:
    """
    Check for mass lockout patterns and trigger admin alerts if threshold exceeded.

    This task is called after each lockout event to check if we've crossed the
    mass lockout threshold. It uses Redis-based tracking to count lockouts
    within the configured time window.

    Args:
        current_count: Optional pre-computed lockout count (for optimization)

    Returns:
        Dictionary with check results and alert status
    """
    from django.core.cache import caches

    logger.info(
        "mass_lockout_check_start",
        task_id=self.request.id,
        current_count=current_count,
    )

    if not settings.LOCKOUT_NOTIFICATION_ENABLED:
        logger.info(
            "mass_lockout_check_disabled",
            task_id=self.request.id,
        )
        return {"status": "disabled", "task_id": self.request.id}

    threshold = settings.LOCKOUT_MASS_THRESHOLD
    time_window_minutes = settings.LOCKOUT_MASS_WINDOW_MINUTES

    # Get lockout count from tracking (will be implemented in lockout_tracking.py)
    # For now, we use the provided count or return early
    if current_count is None:
        logger.warning(
            "mass_lockout_check_no_count",
            task_id=self.request.id,
        )
        return {
            "status": "skipped",
            "task_id": self.request.id,
            "reason": "No count provided and tracking not yet implemented",
        }

    logger.info(
        "mass_lockout_count",
        task_id=self.request.id,
        count=current_count,
        threshold=threshold,
    )

    # Check if threshold exceeded
    if current_count >= threshold:
        # Check debounce key to prevent alert spam
        cache = caches["default"]
        debounce_key = f"mass_lockout_alert_sent:{time_window_minutes}m"

        if cache.get(debounce_key):
            logger.info(
                "mass_lockout_alert_debounced",
                task_id=self.request.id,
                count=current_count,
            )
            return {
                "status": "debounced",
                "task_id": self.request.id,
                "count": current_count,
                "threshold": threshold,
            }

        # Set debounce key (expires after the time window)
        cache.set(debounce_key, True, time_window_minutes * 60)

        logger.warning(
            "mass_lockout_threshold_exceeded",
            task_id=self.request.id,
            count=current_count,
            threshold=threshold,
            time_window_minutes=time_window_minutes,
        )

        # Trigger admin alert
        # Note: In phase 3, this will collect actual affected accounts
        # For now, we'll pass placeholder data
        send_admin_lockout_alert_task.delay(
            lockout_count=current_count,
            time_window_minutes=time_window_minutes,
            affected_accounts=[],  # Will be populated in phase 3
            ip_summary=None,  # Will be populated in phase 3
        )

        return {
            "status": "alert_triggered",
            "task_id": self.request.id,
            "count": current_count,
            "threshold": threshold,
        }

    return {
        "status": "below_threshold",
        "task_id": self.request.id,
        "count": current_count,
        "threshold": threshold,
    }
