"""
Tests for field-level encryption functionality.

Tests cover:
- Encryption/decryption round-trip
- Encrypted fields store ciphertext in DB
- Key rotation
- Missing key handling
- JSON field encryption
- Empty/null value handling
"""

import json
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import connection

from api.encryption import (
    EncryptedCharField,
    EncryptedEmailField,
    EncryptedJSONField,
    EncryptedTextField,
    EncryptionManager,
)
from api.models import SensitiveUserData


@pytest.fixture
def encryption_keys():
    """Generate test encryption keys."""
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    return [key1, key2]


@pytest.fixture
def configure_encryption(encryption_keys):
    """Configure encryption keys for testing."""
    original_keys = getattr(settings, "FIELD_ENCRYPTION_KEYS", [])

    # Set test keys
    settings.FIELD_ENCRYPTION_KEYS = encryption_keys

    # Clear singleton instance to pick up new keys
    EncryptionManager._instance = None

    yield encryption_keys

    # Restore original keys
    settings.FIELD_ENCRYPTION_KEYS = original_keys
    EncryptionManager._instance = None


@pytest.mark.django_db
class TestEncryptionManager:
    """Test EncryptionManager singleton and operations."""

    def test_singleton_pattern(self, configure_encryption):
        """Test that EncryptionManager is a singleton."""
        manager1 = EncryptionManager()
        manager2 = EncryptionManager()
        assert manager1 is manager2

    def test_encrypt_decrypt_roundtrip(self, configure_encryption):
        """Test encryption and decryption produce original value."""
        manager = EncryptionManager()
        plaintext = "sensitive data"

        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)

        assert decrypted == plaintext
        assert ciphertext != plaintext  # Should be encrypted

    def test_encrypt_produces_different_ciphertext(self, configure_encryption):
        """Test that encrypting the same value twice produces different ciphertext."""
        manager = EncryptionManager()
        plaintext = "sensitive data"

        ciphertext1 = manager.encrypt(plaintext)
        ciphertext2 = manager.encrypt(plaintext)

        # Fernet includes a timestamp, so same plaintext produces different ciphertext
        assert ciphertext1 != ciphertext2
        # But both decrypt to the same value
        assert manager.decrypt(ciphertext1) == plaintext
        assert manager.decrypt(ciphertext2) == plaintext

    def test_encrypt_empty_string(self, configure_encryption):
        """Test encrypting empty string returns empty string."""
        manager = EncryptionManager()
        assert manager.encrypt("") == ""

    def test_encrypt_none(self, configure_encryption):
        """Test encrypting None returns None."""
        manager = EncryptionManager()
        assert manager.encrypt(None) is None

    def test_decrypt_empty_string(self, configure_encryption):
        """Test decrypting empty string returns empty string."""
        manager = EncryptionManager()
        assert manager.decrypt("") == ""

    def test_decrypt_none(self, configure_encryption):
        """Test decrypting None returns None."""
        manager = EncryptionManager()
        assert manager.decrypt(None) is None

    def test_missing_keys_raises_error(self):
        """Test that operations fail gracefully when no keys are configured."""
        # Clear keys
        settings.FIELD_ENCRYPTION_KEYS = []
        EncryptionManager._instance = None

        manager = EncryptionManager()

        with pytest.raises(ValueError, match="FIELD_ENCRYPTION_KEYS not configured"):
            manager.encrypt("test")

        with pytest.raises(ValueError, match="FIELD_ENCRYPTION_KEYS not configured"):
            manager.decrypt("test")

    def test_key_rotation_support(self, configure_encryption):
        """Test that data encrypted with old key can be decrypted with new keys."""
        key1, key2 = configure_encryption

        # Encrypt with key1 only
        settings.FIELD_ENCRYPTION_KEYS = [key1]
        EncryptionManager._instance = None
        manager1 = EncryptionManager()

        plaintext = "test data"
        ciphertext = manager1.encrypt(plaintext)

        # Add key2 as primary, keep key1 for decryption
        settings.FIELD_ENCRYPTION_KEYS = [key2, key1]
        EncryptionManager._instance = None
        manager2 = EncryptionManager()

        # Should still be able to decrypt with old key
        decrypted = manager2.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_rotate_encryption(self, configure_encryption):
        """Test re-encrypting data with primary key."""
        key1, key2 = configure_encryption

        # Encrypt with key1
        settings.FIELD_ENCRYPTION_KEYS = [key1]
        EncryptionManager._instance = None
        manager1 = EncryptionManager()

        plaintext = "test data"
        old_ciphertext = manager1.encrypt(plaintext)

        # Rotate to key2 as primary
        settings.FIELD_ENCRYPTION_KEYS = [key2, key1]
        EncryptionManager._instance = None
        manager2 = EncryptionManager()

        # Rotate encryption
        new_ciphertext = manager2.rotate_encryption(old_ciphertext)

        # New ciphertext should be different
        assert new_ciphertext != old_ciphertext

        # Should decrypt to same value
        assert manager2.decrypt(new_ciphertext) == plaintext

        # Old ciphertext should still decrypt (using key1)
        assert manager2.decrypt(old_ciphertext) == plaintext


@pytest.mark.django_db
class TestEncryptedFields:
    """Test encrypted field types."""

    def test_encrypted_char_field_roundtrip(self, configure_encryption):
        """Test EncryptedCharField stores encrypted data and retrieves plaintext."""
        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", ssn="123-45-6789"
        )

        # Retrieve from DB
        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.ssn == "123-45-6789"

    def test_encrypted_char_field_stores_ciphertext(self, configure_encryption):
        """Test that encrypted data is actually encrypted in the database."""
        plaintext_ssn = "123-45-6789"

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", ssn=plaintext_ssn
        )

        # Get the raw value using Django's values() to bypass decryption
        from django.db import models

        # Access the raw database value by using a raw query that selects from db
        # Use Django's query to get the raw field value
        raw_qs = SensitiveUserData.objects.filter(id=sensitive_data.id)

        # Use values_list to get raw database value
        with connection.cursor() as cursor:
            # In SQLite, UUID is stored as a blob or text
            cursor.execute("SELECT ssn FROM api_sensitiveuserdata LIMIT 1")
            row = cursor.fetchone()
            db_value = row[0] if row else None

        # Database value should not be plaintext
        assert db_value is not None
        assert db_value != plaintext_ssn
        # Should be base64-encoded ciphertext (alphanumeric + some special chars)
        assert len(db_value) > len(plaintext_ssn)

    def test_encrypted_text_field_roundtrip(self, configure_encryption):
        """Test EncryptedTextField with larger content."""
        long_note = "This is a long clinical note. " * 100

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", notes=long_note
        )

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.notes == long_note

    def test_encrypted_json_field_roundtrip(self, configure_encryption):
        """Test EncryptedJSONField with structured data."""
        medications = [
            {"name": "Aspirin", "dosage": "100mg", "frequency": "daily"},
            {"name": "Ibuprofen", "dosage": "200mg", "frequency": "as needed"},
        ]

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", medications=medications
        )

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.medications == medications

    def test_encrypted_json_field_stores_ciphertext(self, configure_encryption):
        """Test that JSON field stores encrypted data, not plaintext JSON."""
        # Clear any existing test data
        SensitiveUserData.objects.all().delete()

        diagnosis_codes = ["I10", "E11.9", "Z79.4"]

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", diagnosis_codes=diagnosis_codes
        )

        # Query raw data from database - use LIMIT 1 to avoid UUID issues in SQLite
        with connection.cursor() as cursor:
            cursor.execute("SELECT diagnosis_codes FROM api_sensitiveuserdata LIMIT 1")
            row = cursor.fetchone()
            db_value = row[0] if row else None

        # Database value should not be plaintext JSON
        assert db_value is not None
        plaintext_json = json.dumps(diagnosis_codes)
        # The encrypted value should be different from plaintext
        assert db_value != plaintext_json
        # Encrypted ciphertext should be longer than plaintext due to IV/padding
        assert len(db_value) > len(plaintext_json)

    def test_null_and_empty_values(self, configure_encryption):
        """Test handling of null and empty values."""
        # Create with empty/null values
        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123",
            ssn="",
            date_of_birth="",
            medical_record_number="",
            notes="",
        )

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.ssn == ""
        assert retrieved.date_of_birth == ""
        assert retrieved.medical_record_number == ""
        assert retrieved.notes == ""

    def test_encrypted_email_field(self, configure_encryption):
        """Test EncryptedEmailField (subclass of EncryptedCharField)."""
        from api.encryption import EncryptedEmailField
        from django.db import models

        # Create a test model with EncryptedEmailField
        class TestModel(models.Model):
            email = EncryptedEmailField()

            class Meta:
                app_label = "api"
                managed = False

        field = TestModel._meta.get_field("email")
        assert isinstance(field, EncryptedEmailField)

    def test_max_length_validation(self, configure_encryption):
        """Test that max_length is enforced before encryption."""
        # SSN field has max_length=11
        too_long_ssn = "1" * 12

        with pytest.raises(ValueError, match="exceeds maximum length"):
            SensitiveUserData.objects.create(user_id="user123", ssn=too_long_ssn)

    def test_update_encrypted_field(self, configure_encryption):
        """Test updating an encrypted field."""
        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", ssn="123-45-6789"
        )

        # Update SSN
        sensitive_data.ssn = "987-65-4321"
        sensitive_data.save()

        # Retrieve and verify
        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.ssn == "987-65-4321"

    def test_bulk_create_with_encryption(self, configure_encryption):
        """Test bulk_create with encrypted fields."""
        records = [
            SensitiveUserData(user_id=f"user{i}", ssn=f"{i:03d}-45-6789")
            for i in range(5)
        ]

        SensitiveUserData.objects.bulk_create(records)

        # Verify all records were encrypted and can be decrypted
        for i in range(5):
            retrieved = SensitiveUserData.objects.get(user_id=f"user{i}")
            assert retrieved.ssn == f"{i:03d}-45-6789"

    def test_json_field_with_complex_structure(self, configure_encryption):
        """Test EncryptedJSONField with nested structures."""
        complex_data = {
            "patient": {"name": "John Doe", "age": 45},
            "vitals": {"bp": "120/80", "hr": 72, "temp": 98.6},
            "history": ["diabetes", "hypertension"],
        }

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", diagnosis_codes=complex_data
        )

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.diagnosis_codes == complex_data

    def test_json_field_default_value(self, configure_encryption):
        """Test EncryptedJSONField default value (empty list)."""
        sensitive_data = SensitiveUserData.objects.create(user_id="user123")

        # Should have default empty list
        assert sensitive_data.medications == []
        assert sensitive_data.diagnosis_codes == []


@pytest.mark.django_db
class TestKeyRotationScenarios:
    """Test key rotation scenarios."""

    def test_read_with_rotated_keys(self, configure_encryption):
        """Test reading data after keys have been rotated."""
        key1, key2 = configure_encryption

        # Create data with key1 only
        settings.FIELD_ENCRYPTION_KEYS = [key1]
        EncryptionManager._instance = None

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", ssn="123-45-6789"
        )
        record_id = sensitive_data.id

        # Rotate keys: key2 is now primary, key1 is for decryption only
        settings.FIELD_ENCRYPTION_KEYS = [key2, key1]
        EncryptionManager._instance = None

        # Should still be able to read old data
        retrieved = SensitiveUserData.objects.get(id=record_id)
        assert retrieved.ssn == "123-45-6789"

    def test_write_after_key_rotation(self, configure_encryption):
        """Test that new data is encrypted with new primary key after rotation."""
        key1, key2 = configure_encryption

        # Rotate keys
        settings.FIELD_ENCRYPTION_KEYS = [key2, key1]
        EncryptionManager._instance = None

        # Create new data - should use key2
        new_data = SensitiveUserData.objects.create(user_id="user456", ssn="987-65-4321")

        # Should be readable
        retrieved = SensitiveUserData.objects.get(id=new_data.id)
        assert retrieved.ssn == "987-65-4321"

        # Verify it was encrypted with key2 (new primary)
        # by trying to decrypt with only key2
        settings.FIELD_ENCRYPTION_KEYS = [key2]
        EncryptionManager._instance = None

        retrieved2 = SensitiveUserData.objects.get(id=new_data.id)
        assert retrieved2.ssn == "987-65-4321"


@pytest.mark.django_db
class TestEncryptionEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_characters(self, configure_encryption):
        """Test encryption of unicode characters."""
        unicode_text = "Données sensibles: café, naïve, 日本語, 😀"

        sensitive_data = SensitiveUserData.objects.create(user_id="user123", notes=unicode_text)

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.notes == unicode_text

    def test_special_characters(self, configure_encryption):
        """Test encryption of special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}|;:',.<>?/~`\"\\"

        sensitive_data = SensitiveUserData.objects.create(
            user_id="user123", medical_record_number=special_chars[:50]  # Limited by max_length
        )

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.medical_record_number == special_chars[:50]

    def test_very_long_text(self, configure_encryption):
        """Test encryption of very long text in TextField."""
        long_text = "A" * 10000

        sensitive_data = SensitiveUserData.objects.create(user_id="user123", notes=long_text)

        retrieved = SensitiveUserData.objects.get(id=sensitive_data.id)
        assert retrieved.notes == long_text
        assert len(retrieved.notes) == 10000

    def test_filter_on_non_encrypted_field(self, configure_encryption):
        """Test that filtering works on non-encrypted fields."""
        SensitiveUserData.objects.create(user_id="user123", ssn="123-45-6789")
        SensitiveUserData.objects.create(user_id="user456", ssn="987-65-4321")

        # Filter by non-encrypted field (user_id)
        results = SensitiveUserData.objects.filter(user_id="user123")
        assert results.count() == 1
        assert results.first().user_id == "user123"

    def test_filter_on_encrypted_field_limitation(self, configure_encryption):
        """Test that filtering on encrypted fields doesn't work as expected."""
        SensitiveUserData.objects.create(user_id="user123", ssn="123-45-6789")

        # Filtering on encrypted fields won't work because the value in DB is encrypted
        results = SensitiveUserData.objects.filter(ssn="123-45-6789")
        # This will return no results because it's comparing plaintext to ciphertext
        assert results.count() == 0
