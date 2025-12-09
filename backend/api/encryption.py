"""
Field-level encryption for sensitive data.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
Supports key rotation and multiple keys.

For FIPS 140-2 compliance, use cryptography library with FIPS provider.
"""

import base64
import json
from typing import Any, Optional

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.db import models


class EncryptionManager:
    """Manages encryption keys and provides encrypt/decrypt operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_keys()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance. Useful for tests with overridden settings."""
        if cls._instance is not None:
            cls._instance = None

    def _initialize_keys(self):
        """Load encryption keys from settings."""
        # Support multiple keys for rotation
        # FIELD_ENCRYPTION_KEYS = ["key1", "key2"]  # First is primary, others for decryption
        keys = getattr(settings, "FIELD_ENCRYPTION_KEYS", [])

        if not keys:
            # No keys configured - encryption will fail in production
            self._fernet = None
            self._primary_fernet = None
            return

        # Convert string keys to bytes and create Fernet instances
        fernet_keys = []
        for key in keys:
            if isinstance(key, str):
                key = key.encode()
            fernet_keys.append(Fernet(key))

        # Use MultiFernet for key rotation support
        # First key is primary (used for encryption), others for decryption only
        self._fernet = MultiFernet(fernet_keys)
        self._primary_fernet = fernet_keys[0]  # For re-encryption during rotation

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded ciphertext

        Raises:
            ValueError: If no encryption keys are configured
        """
        if self._fernet is None:
            raise ValueError(
                "FIELD_ENCRYPTION_KEYS not configured. Cannot encrypt data. "
                "Set FIELD_ENCRYPTION_KEYS in settings."
            )

        if plaintext is None or plaintext == "":
            return plaintext

        # Convert to bytes if needed
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        # Encrypt and return as string
        ciphertext = self._fernet.encrypt(plaintext)
        return ciphertext.decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string value.

        Args:
            ciphertext: Base64-encoded ciphertext to decrypt

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If no encryption keys are configured
            cryptography.fernet.InvalidToken: If decryption fails (wrong key, corrupted data)
        """
        if self._fernet is None:
            raise ValueError(
                "FIELD_ENCRYPTION_KEYS not configured. Cannot decrypt data. "
                "Set FIELD_ENCRYPTION_KEYS in settings."
            )

        if ciphertext is None or ciphertext == "":
            return ciphertext

        # Convert to bytes if needed
        if isinstance(ciphertext, str):
            ciphertext = ciphertext.encode("ascii")

        # Decrypt and return as string
        plaintext = self._fernet.decrypt(ciphertext)
        return plaintext.decode("utf-8")

    def rotate_encryption(self, ciphertext: str) -> str:
        """
        Re-encrypt with current primary key.

        This is useful when rotating keys - decrypt with any valid key,
        then re-encrypt with the current primary key.

        Args:
            ciphertext: Base64-encoded ciphertext to re-encrypt

        Returns:
            Re-encrypted ciphertext using primary key
        """
        if self._fernet is None or self._primary_fernet is None:
            raise ValueError("FIELD_ENCRYPTION_KEYS not configured. Cannot rotate encryption.")

        if ciphertext is None or ciphertext == "":
            return ciphertext

        # Decrypt with any valid key (MultiFernet tries all keys)
        plaintext = self.decrypt(ciphertext)

        # Re-encrypt with primary key only
        plaintext_bytes = plaintext.encode("utf-8")
        new_ciphertext = self._primary_fernet.encrypt(plaintext_bytes)
        return new_ciphertext.decode("ascii")


class EncryptedCharField(models.CharField):
    """
    A CharField that encrypts its value before storing in the database.
    Values are stored as base64-encoded ciphertext.

    Note: Encrypted fields cannot be indexed or used in WHERE clauses efficiently.
    """

    description = "An encrypted CharField"

    def __init__(self, *args, **kwargs):
        # Store original max_length for validation
        self._original_max_length = kwargs.get("max_length", 255)

        # Increase max_length to accommodate encryption overhead
        # Fernet adds ~57 bytes of overhead + base64 encoding adds ~33% overhead
        # Safety factor: original_length * 2 + 200
        kwargs["max_length"] = self._original_max_length * 2 + 200

        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        """Encrypt before saving to database."""
        if value is None or value == "":
            return value

        # Validate against original max_length before encryption
        if len(str(value)) > self._original_max_length:
            raise ValueError(
                f"Value exceeds maximum length of {self._original_max_length} characters"
            )

        manager = EncryptionManager()
        return manager.encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        """Decrypt when loading from database."""
        if value is None or value == "":
            return value

        manager = EncryptionManager()
        return manager.decrypt(value)

    def to_python(self, value):
        """Convert to Python value (used by forms)."""
        if isinstance(value, str) or value is None:
            return value
        return str(value)

    def deconstruct(self):
        """For migrations."""
        name, path, args, kwargs = super().deconstruct()
        # Store the original max_length in migrations
        if "max_length" in kwargs:
            kwargs["max_length"] = self._original_max_length
        return name, path, args, kwargs


class EncryptedTextField(models.TextField):
    """An encrypted TextField for larger content."""

    description = "An encrypted TextField"

    def get_prep_value(self, value):
        """Encrypt before saving to database."""
        if value is None or value == "":
            return value

        manager = EncryptionManager()
        return manager.encrypt(str(value))

    def from_db_value(self, value, expression, connection):
        """Decrypt when loading from database."""
        if value is None or value == "":
            return value

        manager = EncryptionManager()
        return manager.decrypt(value)

    def to_python(self, value):
        """Convert to Python value (used by forms)."""
        if isinstance(value, str) or value is None:
            return value
        return str(value)


class EncryptedJSONField(models.JSONField):
    """An encrypted JSONField for structured sensitive data."""

    description = "An encrypted JSONField"

    def get_prep_value(self, value):
        """Serialize to JSON, then encrypt."""
        if value is None:
            return value

        # Serialize to JSON string
        json_str = json.dumps(value, ensure_ascii=False, separators=(",", ":"))

        # Encrypt the JSON string
        manager = EncryptionManager()
        return manager.encrypt(json_str)

    def from_db_value(self, value, expression, connection):
        """Decrypt, then deserialize from JSON."""
        if value is None or value == "":
            return None

        # Decrypt the string
        manager = EncryptionManager()
        decrypted_str = manager.decrypt(value)

        # Deserialize from JSON
        return json.loads(decrypted_str)

    def to_python(self, value):
        """Convert to Python value (used by forms)."""
        if value is None or isinstance(value, (dict, list)):
            return value

        # If it's an encrypted string, decrypt it
        if isinstance(value, str):
            try:
                manager = EncryptionManager()
                decrypted_str = manager.decrypt(value)
                return json.loads(decrypted_str)
            except Exception:
                # If decryption fails, try parsing as JSON directly
                try:
                    return json.loads(value)
                except Exception:
                    return value

        return value


class EncryptedEmailField(EncryptedCharField):
    """
    An encrypted email field.

    Note: Cannot use db_index on encrypted fields. If you need to query by email,
    store a hashed version in a separate indexed field.
    """

    description = "An encrypted email field"

    def __init__(self, *args, **kwargs):
        # Email max length is typically 254
        kwargs.setdefault("max_length", 254)
        super().__init__(*args, **kwargs)
