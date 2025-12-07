# pytest_plugins.py - Runs before conftest.py
# This file is loaded by pytest before conftest.py due to being a plugin
import os

# Set environment variables for tests BEFORE Django loads
os.environ["AUDIT_SIGNING_KEY"] = "test-signing-key-for-audit-logs"
os.environ["FIELD_ENCRYPTION_KEYS"] = "test-encryption-key-32-bytes-lon"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
