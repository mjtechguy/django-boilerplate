# conftest.py
import os
import sys
from pathlib import Path

import pytest
from django.test.utils import override_settings

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def test_settings_and_patches():
    """
    Autouse fixture for test settings overrides.
    """
    caches = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "idempotency": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    with override_settings(
        CACHES=caches,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
    ):
        yield
