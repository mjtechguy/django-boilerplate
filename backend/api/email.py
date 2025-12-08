import html
import re

import structlog
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Model
from django.template.loader import render_to_string
from django.utils import timezone

logger = structlog.get_logger(__name__)


def _make_serializable(obj):
    """Convert objects to JSON-serializable format."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(v) for v in obj]
    if isinstance(obj, Model):
        return f"{obj.__class__.__name__}:{obj.pk}"
    return str(obj)


def strip_html(html_content: str) -> str:
    """Convert HTML to plain text."""
    text = re.sub(r"<br\s*/?>", "\n", html_content)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def send_email(
    to: list[str],
    subject: str,
    template: str,
    context: dict,
    from_email: str = None,
) -> dict:
    """Send email synchronously."""
    from api.models import EmailLog

    html_content = render_to_string(template, context)
    text_content = strip_html(html_content)

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            to=to,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # Log success
        serializable_metadata = _make_serializable(context)
        for email in to:
            EmailLog.objects.create(
                to_email=email,
                subject=subject,
                template=template,
                status=EmailLog.Status.SENT,
                sent_at=timezone.now(),
                metadata=serializable_metadata,
            )

        return {"success": True, "recipients": to}
    except Exception as e:
        logger.error("email_send_failed", error=str(e), to=to)
        for email in to:
            EmailLog.objects.create(
                to_email=email,
                subject=subject,
                template=template,
                status=EmailLog.Status.FAILED,
                error=str(e),
            )
        return {"success": False, "error": str(e)}


def send_email_async(to, subject, template, context, from_email=None) -> str:
    """Queue email via Celery."""
    from api.tasks import send_email_task

    task = send_email_task.delay(to, subject, template, context, from_email)
    return task.id
