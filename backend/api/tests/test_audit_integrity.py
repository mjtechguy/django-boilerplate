"""
Tests for audit log integrity and tamper-evidence functions.

Tests HMAC signature generation, hash-chaining, and verification logic.
These tests directly test the integrity functions rather than relying on
auto-signing during model save (which requires environment configuration).
"""

import uuid

import pytest
from django.utils import timezone

from api.audit_integrity import (
    compute_entry_hash,
    generate_nonce,
    get_next_sequence_number,
    get_previous_hash,
    sign_audit_entry,
    verify_chain_integrity,
    verify_signature,
)
from api.models import AuditLog


# Test signing key - used by tests that directly call signing functions
TEST_SIGNING_KEY = b"test-signing-key-for-audit-logs"


@pytest.fixture
def clean_audit_logs():
    """Fixture that clears all audit logs before each test."""
    AuditLog.objects.all().delete()
    yield
    AuditLog.objects.all().delete()


@pytest.fixture
def mock_signing_key(monkeypatch):
    """Fixture that patches get_signing_key to return test key."""
    import api.audit_integrity

    monkeypatch.setattr(
        api.audit_integrity, "get_signing_key", lambda: TEST_SIGNING_KEY
    )
    return TEST_SIGNING_KEY


@pytest.mark.django_db
class TestAuditIntegrityBasics:
    """Test basic audit integrity functions."""

    def test_get_signing_key_returns_bytes(self, settings):
        """Test that signing key is retrieved as bytes."""
        from api.audit_integrity import get_signing_key

        settings.AUDIT_SIGNING_KEY = "test-key-123"
        key = get_signing_key()
        assert key == b"test-key-123"

    def test_get_signing_key_missing_returns_empty(self, settings):
        """Test behavior when signing key is not configured."""
        from api.audit_integrity import get_signing_key

        settings.AUDIT_SIGNING_KEY = ""
        key = get_signing_key()
        assert key == b""

    def test_generate_nonce(self):
        """Test nonce generation."""
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()

        # Nonces should be hex strings
        assert isinstance(nonce1, str)
        assert len(nonce1) == 64  # 32 bytes as hex = 64 chars

        # Each nonce should be unique
        assert nonce1 != nonce2

    def test_compute_entry_hash(self):
        """Test hash computation for audit entries."""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timezone.now(),
            actor_id="user-123",
            org_id="org-456",
            resource_type="User",
            resource_id="user-789",
            action=AuditLog.Action.CREATE,
            changes={"name": "John Doe"},
            nonce="test-nonce-123",
        )

        hash1 = compute_entry_hash(audit_log)
        hash2 = compute_entry_hash(audit_log)

        # Hash should be deterministic
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex = 64 chars

        # Changing content should change hash
        audit_log.changes = {"name": "Jane Doe"}
        hash3 = compute_entry_hash(audit_log)
        assert hash3 != hash1

    def test_sign_audit_entry_with_key(self, mock_signing_key):
        """Test HMAC signature generation."""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timezone.now(),
            actor_id="user-123",
            org_id="org-456",
            resource_type="User",
            resource_id="user-789",
            action=AuditLog.Action.CREATE,
            changes={},
            nonce="test-nonce",
        )

        signature = sign_audit_entry(audit_log)

        # Signature should be hex string
        assert isinstance(signature, str)
        assert len(signature) == 64  # HMAC-SHA256 hex = 64 chars

        # Signature should be deterministic
        assert signature == sign_audit_entry(audit_log)

    def test_verify_signature_valid(self, mock_signing_key):
        """Test signature verification with valid signature."""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timezone.now(),
            actor_id="user-123",
            org_id="org-456",
            resource_type="User",
            resource_id="user-789",
            action=AuditLog.Action.CREATE,
            changes={},
            nonce="test-nonce",
        )

        # Sign the entry
        audit_log.signature = sign_audit_entry(audit_log)

        # Verify should pass
        assert verify_signature(audit_log) is True

    def test_verify_signature_invalid(self, mock_signing_key):
        """Test signature verification with tampered signature."""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timezone.now(),
            actor_id="user-123",
            org_id="org-456",
            resource_type="User",
            resource_id="user-789",
            action=AuditLog.Action.CREATE,
            changes={},
            nonce="test-nonce",
        )

        # Set invalid signature
        audit_log.signature = "invalid-signature-123"

        # Verify should fail
        assert verify_signature(audit_log) is False

    def test_verify_signature_missing(self, mock_signing_key):
        """Test signature verification with missing signature."""
        audit_log = AuditLog(
            id=uuid.uuid4(),
            timestamp=timezone.now(),
            actor_id="user-123",
            org_id="org-456",
            resource_type="User",
            resource_id="user-789",
            action=AuditLog.Action.CREATE,
            changes={},
            nonce="test-nonce",
            signature="",  # Empty signature
        )

        # Verify should fail
        assert verify_signature(audit_log) is False


@pytest.mark.django_db
class TestAuditChaining:
    """Test audit log hash-chaining functionality."""

    def test_get_next_sequence_number_empty(self, clean_audit_logs):
        """Test sequence number generation when no entries exist."""
        seq_num = get_next_sequence_number()
        assert seq_num == 1

    def test_get_next_sequence_number_increments(self, clean_audit_logs, mock_signing_key):
        """Test sequence number generation with existing entries."""
        # Manually create an entry with sequence number using bulk_create
        entry = AuditLog(
            actor_id="user-1",
            org_id="org-1",
            resource_type="User",
            resource_id="user-1",
            action=AuditLog.Action.CREATE,
            timestamp=timezone.now(),
            sequence_number=1,
            nonce=generate_nonce(),
        )
        entry.signature = sign_audit_entry(entry)
        AuditLog.objects.bulk_create([entry])

        # Next sequence should be 2
        seq_num = get_next_sequence_number()
        assert seq_num == 2

    def test_get_previous_hash_empty(self, clean_audit_logs):
        """Test getting previous hash when no entries exist."""
        prev_hash = get_previous_hash()
        assert prev_hash == ""

    def test_get_previous_hash_with_entries(self, clean_audit_logs, mock_signing_key):
        """Test getting previous hash with existing entries."""
        # Manually create an entry using bulk_create
        entry = AuditLog(
            actor_id="user-1",
            org_id="org-1",
            resource_type="User",
            resource_id="user-1",
            action=AuditLog.Action.CREATE,
            timestamp=timezone.now(),
            sequence_number=1,
            nonce=generate_nonce(),
        )
        entry.signature = sign_audit_entry(entry)
        AuditLog.objects.bulk_create([entry])

        # Get previous hash
        prev_hash = get_previous_hash()
        expected_hash = compute_entry_hash(entry)
        assert prev_hash == expected_hash


@pytest.mark.django_db
class TestChainVerification:
    """Test chain integrity verification."""

    def _create_signed_entry(self, actor_id, org_id, resource_id, sequence_number, previous_hash=""):
        """Helper to create a properly signed audit entry.

        Uses bulk_create to bypass the model's save() override, then signs
        AFTER fetching from DB to ensure the signature matches the stored data
        (since DB may alter timestamp precision).
        """
        entry = AuditLog(
            actor_id=actor_id,
            org_id=org_id,
            resource_type="User",
            resource_id=resource_id,
            action=AuditLog.Action.CREATE,
            timestamp=timezone.now(),
            sequence_number=sequence_number,
            previous_hash=previous_hash,
            nonce=generate_nonce(),
            signature="",  # Will be set after DB insert
        )

        # Use bulk_create to bypass save() override
        AuditLog.objects.bulk_create([entry])

        # Fetch from DB to get the actual stored values (timestamp precision may differ)
        saved = AuditLog.objects.get(id=entry.id)

        # Sign the fetched entry (which has the actual DB-stored values)
        signature = sign_audit_entry(saved)

        # Update the signature directly in the database
        AuditLog.objects.filter(id=saved.id).update(signature=signature)

        # Refresh and return
        saved.refresh_from_db()
        return saved

    def test_verify_chain_integrity_valid_chain(self, clean_audit_logs, mock_signing_key):
        """Test verification of a valid audit chain."""
        # Create a chain of properly signed entries
        entry1 = self._create_signed_entry("user-1", "org-1", "user-1", 1)
        entry2 = self._create_signed_entry(
            "user-2", "org-1", "user-2", 2, compute_entry_hash(entry1)
        )
        entry3 = self._create_signed_entry(
            "user-3", "org-1", "user-3", 3, compute_entry_hash(entry2)
        )

        # Verify chain
        result = verify_chain_integrity(org_id="org-1")

        assert result["valid"] is True, f"Verification failed: {result}"
        assert result["broken_at"] is None
        assert result["entries_checked"] == 3
        assert len(result["errors"]) == 0

    def test_verify_chain_integrity_tampered_signature(self, clean_audit_logs, mock_signing_key):
        """Test detection of tampered signature."""
        # Create entries
        entry1 = self._create_signed_entry("user-1", "org-1", "user-1", 1)
        entry2 = self._create_signed_entry(
            "user-2", "org-1", "user-2", 2, compute_entry_hash(entry1)
        )

        # Tamper with signature (direct DB update to bypass save)
        AuditLog.objects.filter(id=entry2.id).update(signature="tampered-signature")

        # Verify chain
        result = verify_chain_integrity(org_id="org-1")

        assert result["valid"] is False
        assert result["broken_at"] == str(entry2.id)
        assert len(result["errors"]) > 0

    def test_verify_chain_integrity_broken_chain(self, clean_audit_logs, mock_signing_key):
        """Test detection of broken hash chain."""
        # Create entries
        entry1 = self._create_signed_entry("user-1", "org-1", "user-1", 1)
        entry2 = self._create_signed_entry(
            "user-2", "org-1", "user-2", 2, compute_entry_hash(entry1)
        )

        # Break the chain (direct DB update to bypass save)
        AuditLog.objects.filter(id=entry2.id).update(previous_hash="wrong-hash")

        # Verify chain
        result = verify_chain_integrity(org_id="org-1")

        assert result["valid"] is False
        assert result["broken_at"] == str(entry2.id)
        assert any("previous_hash mismatch" in err for err in result["errors"])

    def test_verify_chain_integrity_org_scoped(self, clean_audit_logs, mock_signing_key):
        """Test that verification is properly scoped by organization."""
        # Create entries for org-1
        entry1a = self._create_signed_entry("user-1", "org-1", "user-1", 1)
        entry2a = self._create_signed_entry(
            "user-2", "org-1", "user-2", 2, compute_entry_hash(entry1a)
        )

        # Create entries for org-2 (separate chain)
        entry1b = self._create_signed_entry("user-3", "org-2", "user-3", 1)
        entry2b = self._create_signed_entry(
            "user-4", "org-2", "user-4", 2, compute_entry_hash(entry1b)
        )

        # Verify org-1 chain
        result1 = verify_chain_integrity(org_id="org-1")
        assert result1["valid"] is True
        assert result1["entries_checked"] == 2

        # Verify org-2 chain
        result2 = verify_chain_integrity(org_id="org-2")
        assert result2["valid"] is True
        assert result2["entries_checked"] == 2

    def test_nonce_uniqueness(self, mock_signing_key):
        """Test that nonces are unique across entries."""
        nonces = set()

        # Generate multiple nonces
        for _ in range(10):
            nonce = generate_nonce()
            nonces.add(nonce)

        # All nonces should be unique
        assert len(nonces) == 10

    def test_tamper_detection_modified_changes(self, clean_audit_logs, mock_signing_key):
        """Test that modifying changes field is detected."""
        # Create entry without signature first
        entry = AuditLog(
            actor_id="user-1",
            org_id="org-1",
            resource_type="User",
            resource_id="user-1",
            action=AuditLog.Action.UPDATE,
            timestamp=timezone.now(),
            sequence_number=1,
            changes={"name": "Original Name"},
            nonce=generate_nonce(),
            signature="",  # Will be set after DB insert
        )
        AuditLog.objects.bulk_create([entry])

        # Fetch from DB and sign (to match DB-stored timestamp precision)
        saved_entry = AuditLog.objects.get(id=entry.id)
        signature = sign_audit_entry(saved_entry)
        AuditLog.objects.filter(id=saved_entry.id).update(signature=signature)
        saved_entry.refresh_from_db()

        # Verify original is valid
        assert verify_signature(saved_entry) is True

        # Tamper with changes (direct DB update to bypass save override)
        AuditLog.objects.filter(id=entry.id).update(changes={"name": "Tampered Name"})
        saved_entry.refresh_from_db()

        # Signature should now be invalid
        assert verify_signature(saved_entry) is False
