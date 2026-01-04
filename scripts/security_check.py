#!/usr/bin/env python3
"""
Security settings checker for production deployments.

This script validates that critical security settings are properly configured
before deployment to production.

Usage:
    python scripts/security_check.py [--env production|staging]

Exit codes:
    0: All checks passed
    1: One or more checks failed
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))


def check_setting(name: str, expected, actual, description: str) -> tuple[bool, str]:
    """Check a single setting and return (passed, message)."""
    if callable(expected):
        passed = expected(actual)
    else:
        passed = actual == expected

    status = "✓ PASS" if passed else "✗ FAIL"
    msg = f"{status}: {name} - {description}"
    if not passed:
        msg += f"\n       Expected: {expected}, Got: {actual}"
    return passed, msg


def run_security_checks(env: str = "production") -> int:
    """Run all security checks and return exit code."""
    print(f"\n{'=' * 60}")
    print(f"  Security Settings Check ({env})")
    print("=" * 60 + "\n")

    # Set Django settings module
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env}")

    try:
        import django

        django.setup()
        from django.conf import settings
    except Exception as e:
        print(f"✗ FAIL: Could not load Django settings: {e}")
        return 1

    checks = []

    # HTTPS/SSL Settings
    print("--- HTTPS/SSL Settings ---")
    checks.append(
        check_setting(
            "SECURE_SSL_REDIRECT",
            True,
            getattr(settings, "SECURE_SSL_REDIRECT", False),
            "Should redirect HTTP to HTTPS",
        )
    )
    checks.append(
        check_setting(
            "SECURE_HSTS_SECONDS",
            lambda x: x >= 31536000,  # At least 1 year
            getattr(settings, "SECURE_HSTS_SECONDS", 0),
            "HSTS should be at least 1 year (31536000 seconds)",
        )
    )
    checks.append(
        check_setting(
            "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            True,
            getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", False),
            "HSTS should include subdomains",
        )
    )
    for passed, msg in checks[-3:]:
        print(msg)

    # Cookie Settings
    print("\n--- Cookie Security ---")
    checks.append(
        check_setting(
            "SESSION_COOKIE_SECURE",
            True,
            getattr(settings, "SESSION_COOKIE_SECURE", False),
            "Session cookies should be secure (HTTPS only)",
        )
    )
    checks.append(
        check_setting(
            "SESSION_COOKIE_HTTPONLY",
            True,
            getattr(settings, "SESSION_COOKIE_HTTPONLY", True),
            "Session cookies should be HttpOnly",
        )
    )
    checks.append(
        check_setting(
            "CSRF_COOKIE_SECURE",
            True,
            getattr(settings, "CSRF_COOKIE_SECURE", False),
            "CSRF cookies should be secure (HTTPS only)",
        )
    )
    for passed, msg in checks[-3:]:
        print(msg)

    # Debug Mode
    print("\n--- Debug Mode ---")
    checks.append(
        check_setting(
            "DEBUG",
            False,
            settings.DEBUG,
            "DEBUG must be False in production",
        )
    )
    for passed, msg in checks[-1:]:
        print(msg)

    # Security Headers
    print("\n--- Security Headers ---")
    checks.append(
        check_setting(
            "SECURE_BROWSER_XSS_FILTER",
            True,
            getattr(settings, "SECURE_BROWSER_XSS_FILTER", False),
            "XSS filter should be enabled",
        )
    )
    checks.append(
        check_setting(
            "SECURE_CONTENT_TYPE_NOSNIFF",
            True,
            getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False),
            "Content-Type sniffing should be disabled",
        )
    )
    checks.append(
        check_setting(
            "X_FRAME_OPTIONS",
            "DENY",
            getattr(settings, "X_FRAME_OPTIONS", ""),
            "X-Frame-Options should be DENY",
        )
    )
    for passed, msg in checks[-3:]:
        print(msg)

    # CSP
    print("\n--- Content Security Policy ---")
    checks.append(
        check_setting(
            "CSP_DEFAULT_SRC",
            lambda x: x is not None and len(x) > 0,
            getattr(settings, "CSP_DEFAULT_SRC", None),
            "CSP default-src should be configured",
        )
    )
    checks.append(
        check_setting(
            "CSP_FRAME_ANCESTORS",
            ("'none'",),
            getattr(settings, "CSP_FRAME_ANCESTORS", None),
            "CSP frame-ancestors should be 'none'",
        )
    )
    for passed, msg in checks[-2:]:
        print(msg)

    # Middleware
    print("\n--- Security Middleware ---")
    middleware = getattr(settings, "MIDDLEWARE", [])
    checks.append(
        check_setting(
            "SecurityMiddleware",
            True,
            "django.middleware.security.SecurityMiddleware" in middleware,
            "Django SecurityMiddleware should be enabled",
        )
    )
    checks.append(
        check_setting(
            "CSPMiddleware",
            True,
            "csp.middleware.CSPMiddleware" in middleware,
            "CSP middleware should be enabled",
        )
    )
    checks.append(
        check_setting(
            "AxesMiddleware",
            True,
            "axes.middleware.AxesMiddleware" in middleware,
            "Axes (brute-force protection) middleware should be enabled",
        )
    )
    for passed, msg in checks[-3:]:
        print(msg)

    # Secret Key
    print("\n--- Secrets ---")
    checks.append(
        check_setting(
            "SECRET_KEY",
            lambda x: x != "changeme" and len(x) >= 32,
            settings.SECRET_KEY,
            "SECRET_KEY must not be default and should be at least 32 chars",
        )
    )
    for passed, msg in checks[-1:]:
        print(msg)

    # ALLOWED_HOSTS
    print("\n--- Host Configuration ---")
    checks.append(
        check_setting(
            "ALLOWED_HOSTS",
            lambda x: len(x) > 0 and "*" not in x,
            settings.ALLOWED_HOSTS,
            "ALLOWED_HOSTS should be explicitly set (no wildcards)",
        )
    )
    for passed, msg in checks[-1:]:
        print(msg)

    # Webhook SSRF Protection
    print("\n--- Webhook SSRF Protection ---")
    checks.append(
        check_setting(
            "WEBHOOK_SSRF_PROTECTION_ENABLED",
            True,
            getattr(settings, "WEBHOOK_SSRF_PROTECTION_ENABLED", False),
            "SSRF protection must be enabled for webhooks",
        )
    )
    checks.append(
        check_setting(
            "WEBHOOK_BLOCK_PRIVATE_IPS",
            True,
            getattr(settings, "WEBHOOK_BLOCK_PRIVATE_IPS", False),
            "Private IP blocking must be enabled for webhooks",
        )
    )
    checks.append(
        check_setting(
            "WEBHOOK_ALLOWED_SCHEMES",
            lambda x: x == ["https"] if env == "production" else True,
            getattr(settings, "WEBHOOK_ALLOWED_SCHEMES", []),
            "Only HTTPS should be allowed in production" if env == "production" else "HTTPS should be preferred",
        )
    )
    for passed, msg in checks[-3:]:
        print(msg)

    # Summary
    print("\n" + "=" * 60)
    passed_count = sum(1 for passed, _ in checks if passed)
    total_count = len(checks)
    print(f"Results: {passed_count}/{total_count} checks passed")

    if passed_count == total_count:
        print("\n✓ All security checks passed!")
        return 0
    else:
        print(f"\n✗ {total_count - passed_count} check(s) failed")
        print("\nPlease fix the failing checks before deploying to production.")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check security settings")
    parser.add_argument(
        "--env",
        default="production",
        choices=["production", "staging", "local"],
        help="Environment to check (default: production)",
    )
    args = parser.parse_args()

    sys.exit(run_security_checks(args.env))
