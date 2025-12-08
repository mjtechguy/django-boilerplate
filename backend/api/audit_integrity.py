"""
Audit log integrity and tamper-evidence utilities.

Implements:
- HMAC-SHA256 signing of audit entries
- Hash-chaining to link entries (like blockchain)
- Signature verification
- Chain integrity verification

This module ensures that audit logs are tamper-evident and maintain
a verifiable chain of custody for compliance and security auditing.
"""

import hashlib
import hmac
import json
import secrets
from typing import Optional

import structlog
from django.conf import settings
from django.db import transaction
from django.db.models import Max

logger = structlog.get_logger(__name__)


def get_signing_key() -> bytes:
    """
    Get the HMAC signing key from settings or environment.

    Checks settings first, then falls back to environment variable.
    This allows tests to set the key via environment before Django loads.

    Returns:
        bytes: The signing key in bytes format

    Raises:
        ValueError: If AUDIT_SIGNING_KEY is not configured
    """
    import os

    # Check settings first, then environment as fallback
    key = getattr(settings, "AUDIT_SIGNING_KEY", "") or os.environ.get(
        "AUDIT_SIGNING_KEY", ""
    )
    if not key:
        logger.warning(
            "audit_signing_key_missing",
            message="AUDIT_SIGNING_KEY not configured - audit logs will not be signed",
        )
        return b""
    return key.encode("utf-8")


def generate_nonce() -> str:
    """
    Generate a cryptographically secure nonce.

    Returns:
        str: 32-byte random nonce as hex string
    """
    return secrets.token_hex(32)


def compute_entry_hash(audit_log) -> str:
    """
    Compute SHA256 hash of an audit entry's content.

    Creates a deterministic hash of the audit log entry by combining
    all relevant fields in a specific order.

    Args:
        audit_log: AuditLog instance (can be unsaved)

    Returns:
        str: SHA256 hash as hex string
    """
    # Build deterministic string from audit entry fields
    # Order matters for consistency
    content_parts = [
        str(audit_log.id),
        str(audit_log.timestamp) if audit_log.timestamp else "",
        str(audit_log.actor_id),
        str(audit_log.org_id or ""),
        str(audit_log.resource_type),
        str(audit_log.resource_id),
        str(audit_log.action),
        json.dumps(audit_log.changes or {}, sort_keys=True),
        str(audit_log.nonce),
    ]

    content = "|".join(content_parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sign_audit_entry(audit_log) -> str:
    """
    Generate HMAC-SHA256 signature for an audit entry.

    The signature is computed over the hash of the entry content,
    providing both integrity and authenticity.

    Args:
        audit_log: AuditLog instance with computed hash

    Returns:
        str: HMAC signature as hex string
    """
    key = get_signing_key()
    if not key:
        return ""

    # Compute hash of the entry
    entry_hash = compute_entry_hash(audit_log)

    # Sign the hash with HMAC
    signature = hmac.new(key, entry_hash.encode("utf-8"), hashlib.sha256)
    return signature.hexdigest()


def verify_signature(audit_log) -> bool:
    """
    Verify the HMAC signature of an audit entry.

    Args:
        audit_log: AuditLog instance with signature field populated

    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not audit_log.signature:
        logger.warning(
            "audit_signature_missing",
            audit_log_id=str(audit_log.id),
            message="Audit log entry has no signature",
        )
        return False

    # Recompute signature and compare
    expected_signature = sign_audit_entry(audit_log)

    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(audit_log.signature, expected_signature)

    if not is_valid:
        logger.error(
            "audit_signature_invalid",
            audit_log_id=str(audit_log.id),
            sequence_number=audit_log.sequence_number,
            expected=expected_signature,
            actual=audit_log.signature,
        )

    return is_valid


def get_previous_hash(org_id: Optional[str] = None) -> str:
    """
    Get the hash of the most recent audit entry (for chaining).

    Args:
        org_id: Optional organization ID to scope the chain per-org

    Returns:
        str: Hash of previous entry, or empty string if no previous entry
    """
    # Avoid circular import
    from api.models import AuditLog

    # Get the most recent audit log by sequence number
    query = AuditLog.objects.all()
    if org_id:
        query = query.filter(org_id=org_id)

    previous_entry = query.order_by("-sequence_number").first()

    if previous_entry:
        return compute_entry_hash(previous_entry)

    return ""  # Genesis entry


def get_next_sequence_number(org_id: Optional[str] = None) -> int:
    """
    Get the next sequence number for audit log entries.

    Args:
        org_id: Optional organization ID to scope sequence per-org

    Returns:
        int: Next sequence number
    """
    # Avoid circular import
    from api.models import AuditLog

    query = AuditLog.objects.all()
    if org_id:
        query = query.filter(org_id=org_id)

    max_seq = query.aggregate(Max("sequence_number"))["sequence_number__max"]
    return (max_seq or 0) + 1


@transaction.atomic
def sign_and_save(audit_log) -> None:
    """
    Sign an audit entry and save it with chain linking.

    This is called automatically by AuditLog.save() for new entries.
    It performs the following steps:
    1. Generate a unique nonce
    2. Get the next sequence number
    3. Link to the previous entry via hash
    4. Compute and attach the signature

    Args:
        audit_log: Unsaved AuditLog instance
    """
    # Generate nonce for uniqueness
    audit_log.nonce = generate_nonce()

    # Get next sequence number (org-scoped or global)
    audit_log.sequence_number = get_next_sequence_number(audit_log.org_id)

    # Link to previous entry in the chain
    audit_log.previous_hash = get_previous_hash(audit_log.org_id)

    # Compute signature
    audit_log.signature = sign_audit_entry(audit_log)

    logger.info(
        "audit_entry_signed",
        audit_log_id=str(audit_log.id),
        sequence_number=audit_log.sequence_number,
        org_id=audit_log.org_id,
        has_signature=bool(audit_log.signature),
    )


def verify_chain_integrity(
    start_id: Optional[str] = None,
    end_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> dict:
    """
    Verify the integrity of a chain of audit entries.

    Checks:
    1. Signature validity for each entry
    2. Hash chain continuity (each entry's previous_hash matches the hash of the previous entry)
    3. Sequence number ordering

    Args:
        start_id: Optional UUID to start verification from
        end_id: Optional UUID to end verification at
        org_id: Optional organization ID to scope verification

    Returns:
        dict: {
            "valid": bool,
            "broken_at": UUID or None,
            "entries_checked": int,
            "errors": list of error descriptions
        }
    """
    # Avoid circular import
    from api.models import AuditLog

    # Build query
    query = AuditLog.objects.all().order_by("sequence_number")

    if org_id:
        query = query.filter(org_id=org_id)

    if start_id:
        start_entry = AuditLog.objects.get(id=start_id)
        query = query.filter(sequence_number__gte=start_entry.sequence_number)

    if end_id:
        end_entry = AuditLog.objects.get(id=end_id)
        query = query.filter(sequence_number__lte=end_entry.sequence_number)

    entries = list(query)
    entries_checked = 0
    errors = []
    broken_at = None

    for i, entry in enumerate(entries):
        entries_checked += 1

        # Check signature validity
        if not verify_signature(entry):
            error_msg = f"Invalid signature at entry {entry.id} (seq {entry.sequence_number})"
            errors.append(error_msg)
            if not broken_at:
                broken_at = str(entry.id)

        # Check chain continuity (skip first entry)
        if i > 0:
            previous_entry = entries[i - 1]
            expected_previous_hash = compute_entry_hash(previous_entry)

            if entry.previous_hash != expected_previous_hash:
                error_msg = (
                    f"Broken chain at entry {entry.id} (seq {entry.sequence_number}): "
                    f"previous_hash mismatch"
                )
                errors.append(error_msg)
                if not broken_at:
                    broken_at = str(entry.id)

            # Check sequence number ordering
            if entry.sequence_number != previous_entry.sequence_number + 1:
                error_msg = (
                    f"Sequence number gap at entry {entry.id}: "
                    f"expected {previous_entry.sequence_number + 1}, "
                    f"got {entry.sequence_number}"
                )
                errors.append(error_msg)
                if not broken_at:
                    broken_at = str(entry.id)

    result = {
        "valid": len(errors) == 0,
        "broken_at": broken_at,
        "entries_checked": entries_checked,
        "errors": errors,
    }

    logger.info(
        "audit_chain_verified",
        valid=result["valid"],
        entries_checked=entries_checked,
        errors_found=len(errors),
        org_id=org_id,
    )

    return result
