import uuid
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import JSONField
from django.utils import timezone

from api.encryption import EncryptedCharField, EncryptedJSONField, EncryptedTextField

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrgScopedQuerySet(models.QuerySet):
    def for_org(self, org_id):
        return self.filter(org_id=org_id)

    def for_org_and_team(self, org_id, team_id=None):
        qs = self.filter(org_id=org_id)
        if team_id:
            qs = qs.filter(models.Q(team_id=team_id) | models.Q(team_id__isnull=True))
        return qs


class Org(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    license_tier = models.CharField(max_length=64, default="free")
    feature_flags = JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["license_tier"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Org<{self.name}>"


class Team(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Org, related_name="teams", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    class Meta:
        unique_together = [("org", "name")]
        indexes = [models.Index(fields=["org"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"Team<{self.name}>"


class Membership(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, related_name="memberships", on_delete=models.CASCADE)
    org = models.ForeignKey(Org, related_name="memberships", on_delete=models.CASCADE)
    team = models.ForeignKey(
        Team, related_name="memberships", on_delete=models.CASCADE, null=True, blank=True
    )
    org_roles = JSONField(default=list, blank=True)
    team_roles = JSONField(default=list, blank=True)

    class Meta:
        unique_together = [("user", "org", "team")]
        indexes = [
            models.Index(fields=["user", "org"]),
            models.Index(fields=["org"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Membership<{self.user_id} @ {self.org_id}>"


class Settings(TimeStampedModel):
    class Scope(models.TextChoices):
        GLOBAL = "global", "Global"
        ORG = "org", "Org"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=16, choices=Scope.choices, default=Scope.GLOBAL)
    org = models.ForeignKey(Org, null=True, blank=True, on_delete=models.CASCADE)
    key = models.CharField(max_length=128)
    value = JSONField()

    class Meta:
        unique_together = [("scope", "org", "key")]
        indexes = [
            models.Index(fields=["scope", "key"]),
            models.Index(fields=["org", "key"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Settings<{self.scope}:{self.key}>"

    @classmethod
    def get_value(cls, key: str, org: Optional[Org] = None, default: Any = None) -> Any:
        """
        Precedence: org override -> global override -> env default.
        """
        if org:
            org_setting = (
                cls.objects.filter(scope=cls.Scope.ORG, org=org, key=key)
                .order_by("-created_at")
                .first()
            )
            if org_setting:
                return org_setting.value
        global_setting = (
            cls.objects.filter(scope=cls.Scope.GLOBAL, org__isnull=True, key=key)
            .order_by("-created_at")
            .first()
        )
        if global_setting:
            return global_setting.value
        return default


class ResourceBase(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(Org, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, null=True, blank=True, on_delete=models.SET_NULL)
    sensitivity = models.CharField(max_length=32, default="normal")
    pii_flags = JSONField(default=list, blank=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["org"]),
            models.Index(fields=["team"]),
        ]


class SampleResource(ResourceBase):
    """Concrete example resource to exercise org/team scoping patterns."""

    name = models.CharField(max_length=255)

    objects = OrgScopedQuerySet.as_manager()

    class Meta:
        indexes = [models.Index(fields=["name"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"SampleResource<{self.name}>"


class WebhookEndpoint(TimeStampedModel):
    """Webhook endpoint configuration for an organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org_id = models.CharField(max_length=255, db_index=True)
    name = models.CharField(max_length=255)
    url = models.URLField()
    secret = models.CharField(max_length=64)
    events = models.JSONField(default=list)  # ["user.created", "org.updated"]
    is_active = models.BooleanField(default=True)
    headers = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["org_id", "is_active"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"WebhookEndpoint<{self.name}>"


class WebhookDelivery(TimeStampedModel):
    """Track webhook delivery attempts."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries"
    )
    event_type = models.CharField(max_length=128)
    payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["endpoint", "status"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"WebhookDelivery<{self.event_type} -> {self.endpoint.name}>"


class EmailLog(TimeStampedModel):
    """Track email delivery for auditing."""

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        BOUNCED = "bounced", "Bounced"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    to_email = models.EmailField()
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SENT)
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["to_email"]),
            models.Index(fields=["status"]),
        ]


class AuditLog(models.Model):
    """Immutable audit log for compliance and debugging."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        READ = "read", "Read"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.CharField(max_length=255, db_index=True)
    actor_email = models.CharField(max_length=255, blank=True, null=True)
    org_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    action = models.CharField(max_length=64, choices=Action.choices, db_index=True)
    resource_type = models.CharField(max_length=128, db_index=True)
    resource_id = models.CharField(max_length=255, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)

    # Tamper-evidence fields
    signature = models.CharField(
        max_length=128, blank=True, help_text="HMAC-SHA256 signature of this entry"
    )
    previous_hash = models.CharField(
        max_length=128, blank=True, help_text="Hash of previous audit entry for chain integrity"
    )
    sequence_number = models.BigIntegerField(
        default=0, db_index=True, help_text="Sequential entry number for ordering"
    )
    nonce = models.CharField(
        max_length=64, blank=True, help_text="Random nonce for signature uniqueness"
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["org_id", "timestamp"]),
            models.Index(fields=["actor_id", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["sequence_number"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"AuditLog<{self.action} {self.resource_type}:{self.resource_id}>"

    def save(self, *args, **kwargs):
        """Override save to automatically sign new entries."""
        # Use _state.adding instead of 'not self.pk' because UUID primary keys
        # are set before save via default=uuid.uuid4
        if self._state.adding:
            from django.utils import timezone

            from api.audit_integrity import sign_and_save

            # Set timestamp before signing so the hash includes the final value
            # (auto_now_add would set it after signing, causing hash mismatch)
            if not self.timestamp:
                self.timestamp = timezone.now()

            sign_and_save(self)
        super().save(*args, **kwargs)


class ImpersonationLog(TimeStampedModel):
    """Log of user impersonation actions for security and audit purposes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_id = models.CharField(max_length=255, db_index=True)  # platform_admin doing impersonation
    admin_email = models.CharField(max_length=255, null=True, blank=True)
    target_user_id = models.CharField(max_length=255, db_index=True)  # user being impersonated
    target_user_email = models.CharField(max_length=255, null=True, blank=True)
    org_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    action = models.CharField(max_length=64)  # start, end, or action performed
    endpoint = models.CharField(max_length=255)  # API endpoint accessed
    method = models.CharField(max_length=10)  # HTTP method
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["admin_id", "created_at"]),
            models.Index(fields=["target_user_id", "created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"ImpersonationLog<{self.admin_id} -> {self.target_user_id}>"


class SensitiveUserData(TimeStampedModel):
    """
    Example model demonstrating field-level encryption for PII/PHI.
    For HIPAA compliance, all PHI fields must be encrypted at rest.

    Note: Encrypted fields cannot be efficiently indexed or queried.
    For searchable fields, consider storing hashed versions separately.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255, db_index=True)

    # Encrypted PII fields
    ssn = EncryptedCharField(
        max_length=11, blank=True, help_text="Social Security Number (encrypted)"
    )
    date_of_birth = EncryptedCharField(
        max_length=10, blank=True, help_text="DOB in YYYY-MM-DD format (encrypted)"
    )
    medical_record_number = EncryptedCharField(max_length=50, blank=True)

    # Encrypted PHI fields
    diagnosis_codes = EncryptedJSONField(
        default=list, blank=True, help_text="ICD-10 codes (encrypted)"
    )
    medications = EncryptedJSONField(default=list, blank=True)
    notes = EncryptedTextField(blank=True, help_text="Clinical notes (encrypted)")

    # Non-encrypted metadata (for querying)
    data_classification = models.CharField(
        max_length=20,
        default="PHI",
        choices=[
            ("PUBLIC", "Public"),
            ("INTERNAL", "Internal"),
            ("CONFIDENTIAL", "Confidential"),
            ("PHI", "Protected Health Information"),
            ("PII", "Personally Identifiable Information"),
        ],
    )

    class Meta:
        verbose_name = "Sensitive User Data"
        verbose_name_plural = "Sensitive User Data"
        indexes = [models.Index(fields=["user_id", "data_classification"])]

    def __str__(self) -> str:  # pragma: no cover
        return f"SensitiveUserData<{self.user_id}>"
