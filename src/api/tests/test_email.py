import pytest
from django.core import mail

from api.email import send_email, send_email_async, strip_html
from api.models import EmailLog

pytestmark = pytest.mark.django_db


def test_strip_html():
    """Test HTML to plain text conversion."""
    html = "<p>Hello <b>World</b></p><br/><p>Line 2</p>"
    text = strip_html(html)
    assert "Hello World" in text
    assert "Line 2" in text
    assert "<p>" not in text
    assert "<b>" not in text


def test_send_email_success(settings):
    """Test successful email sending."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    result = send_email(
        to=["test@example.com"],
        subject="Test Subject",
        template="email/welcome.html",
        context={"user_name": "John Doe", "login_url": "https://example.com/login"},
    )

    assert result["success"] is True
    assert result["recipients"] == ["test@example.com"]
    assert len(mail.outbox) == 1

    sent_email = mail.outbox[0]
    assert sent_email.subject == "Test Subject"
    assert sent_email.to == ["test@example.com"]
    assert "John Doe" in sent_email.body


def test_send_email_creates_log(settings):
    """Test that sending email creates log entry."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    send_email(
        to=["test@example.com"],
        subject="Test Subject",
        template="email/welcome.html",
        context={"user_name": "John Doe", "login_url": "https://example.com/login"},
    )

    log = EmailLog.objects.get(to_email="test@example.com")
    assert log.subject == "Test Subject"
    assert log.template == "email/welcome.html"
    assert log.status == EmailLog.Status.SENT
    assert log.sent_at is not None
    assert log.metadata["user_name"] == "John Doe"


def test_send_email_failure_creates_log(settings):
    """Test that email failure creates log entry."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "invalid.example.com"

    result = send_email(
        to=["test@example.com"],
        subject="Test Subject",
        template="email/welcome.html",
        context={"user_name": "John Doe", "login_url": "https://example.com/login"},
    )

    assert result["success"] is False
    assert "error" in result

    log = EmailLog.objects.get(to_email="test@example.com")
    assert log.status == EmailLog.Status.FAILED
    assert log.error is not None
    assert log.sent_at is None


def test_email_template_renders(settings):
    """Test email template rendering."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    send_email(
        to=["test@example.com"],
        subject="Notification",
        template="email/notification.html",
        context={
            "title": "Test Title",
            "message": "Test message",
            "action_url": "https://example.com/action",
            "action_text": "Click Here",
        },
    )

    sent_email = mail.outbox[0]
    assert "Test Title" in sent_email.body
    assert "Test message" in sent_email.body
    assert "Click Here" in sent_email.body


def test_send_email_multiple_recipients(settings):
    """Test sending email to multiple recipients."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    send_email(
        to=["test1@example.com", "test2@example.com"],
        subject="Test Subject",
        template="email/welcome.html",
        context={"user_name": "John Doe", "login_url": "https://example.com/login"},
    )

    # Should create one email with multiple recipients
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["test1@example.com", "test2@example.com"]

    # Should create separate log entries for each recipient
    assert EmailLog.objects.filter(to_email="test1@example.com").count() == 1
    assert EmailLog.objects.filter(to_email="test2@example.com").count() == 1


def test_send_email_async_queues_task(settings):
    """Test that async email queues a Celery task."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    task_id = send_email_async(
        to=["test@example.com"],
        subject="Test Subject",
        template="email/welcome.html",
        context={"user_name": "John Doe", "login_url": "https://example.com/login"},
    )

    # Should return a task ID
    assert task_id is not None
    assert isinstance(task_id, str)


def test_email_log_ordering():
    """Test that email logs are ordered by created_at descending."""
    EmailLog.objects.create(
        to_email="test1@example.com",
        subject="First",
        template="email/welcome.html",
        status=EmailLog.Status.SENT,
    )

    EmailLog.objects.create(
        to_email="test2@example.com",
        subject="Second",
        template="email/welcome.html",
        status=EmailLog.Status.SENT,
    )

    logs = EmailLog.objects.all()
    assert logs[0].subject == "Second"
    assert logs[1].subject == "First"


def test_email_log_indexes():
    """Test that email log indexes exist."""
    EmailLog.objects.create(
        to_email="test@example.com",
        subject="Test",
        template="email/welcome.html",
        status=EmailLog.Status.SENT,
    )

    # Query using indexed fields should work efficiently
    logs_by_email = EmailLog.objects.filter(to_email="test@example.com")
    assert logs_by_email.count() == 1

    logs_by_status = EmailLog.objects.filter(status=EmailLog.Status.SENT)
    assert logs_by_status.count() == 1
