"""
Expanded tests for JWT authentication - validation cases, token parsing, claims extraction.
"""

import time
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from api.auth import KeycloakJWTAuthentication


class TestJWTTokenExtraction(TestCase):
    """Tests for token extraction from requests."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = KeycloakJWTAuthentication()

    def test_no_authorization_header_returns_none(self):
        """Test that missing Authorization header returns None."""
        request = self.factory.get("/api/v1/test")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_empty_authorization_header_returns_none(self):
        """Test that empty Authorization header returns None."""
        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_non_bearer_scheme_returns_none(self):
        """Test that non-Bearer auth scheme returns None."""
        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Basic abc123")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_bearer_with_no_token_raises_error(self):
        """Test that Bearer without token raises error."""
        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_bearer_with_spaces_in_token_raises_error(self):
        """Test that Bearer with spaces in token raises error."""
        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer token with spaces")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)


class TestJWTValidation(TestCase):
    """Tests for JWT token validation."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = KeycloakJWTAuthentication()

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    def test_expired_token_raises_authentication_failed(
        self, mock_jwk, mock_jwt_class, mock_get_jwks
    ):
        """Test that expired tokens raise AuthenticationFailed."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}
        mock_jwt = MagicMock()
        mock_jwt.decode.side_effect = Exception("Token has expired")
        mock_jwt_class.return_value = mock_jwt

        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer expired.token.here")

        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)

        self.assertIn("Invalid token", str(context.exception.detail))

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    def test_invalid_signature_raises_authentication_failed(
        self, mock_jwk, mock_jwt_class, mock_get_jwks
    ):
        """Test that invalid signatures raise AuthenticationFailed."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}
        mock_jwt = MagicMock()
        mock_jwt.decode.side_effect = Exception("Signature verification failed")
        mock_jwt_class.return_value = mock_jwt

        request = self.factory.get(
            "/api/v1/test", HTTP_AUTHORIZATION="Bearer invalid.signature.token"
        )

        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)

        self.assertIn("Invalid token", str(context.exception.detail))


class TestJWTClaimsExtraction(TestCase):
    """Tests for JWT claims extraction."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = KeycloakJWTAuthentication()

    def _create_mock_claims(self, extra_claims=None):
        """Helper to create mock claims object."""
        base_claims = {
            "sub": "user-123",
            "iss": "http://keycloak:8080/realms/app",
            "aud": "api",
            "exp": int(time.time()) + 3600,
        }
        if extra_claims:
            base_claims.update(extra_claims)

        mock_claims = MagicMock()
        mock_claims.__getitem__ = lambda self, key: base_claims[key]
        mock_claims.get = lambda key, default=None: base_claims.get(key, default)
        mock_claims.__contains__ = lambda self, key: key in base_claims
        mock_claims.validate = MagicMock()

        return mock_claims

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    @patch("api.auth.User.objects.get_or_create")
    def test_extracts_sub_claim(self, mock_get_or_create, mock_jwk, mock_jwt_class, mock_get_jwks):
        """Test that subject claim is extracted."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}

        mock_claims = self._create_mock_claims()
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = mock_claims
        mock_jwt_class.return_value = mock_jwt

        mock_user = MagicMock()
        mock_get_or_create.return_value = (mock_user, True)

        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer valid.token.here")
        user, token = self.auth.authenticate(request)

        # Verify get_or_create was called with correct username
        mock_get_or_create.assert_called_once()
        call_kwargs = mock_get_or_create.call_args
        self.assertEqual(call_kwargs[1]["username"], "user-123")

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    @patch("api.auth.User.objects.get_or_create")
    def test_extracts_realm_roles(
        self, mock_get_or_create, mock_jwk, mock_jwt_class, mock_get_jwks
    ):
        """Test that realm roles are extracted from token."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}

        mock_claims = self._create_mock_claims(
            {"realm_access": {"roles": ["platform_admin", "user"]}}
        )
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = mock_claims
        mock_jwt_class.return_value = mock_jwt

        mock_user = MagicMock()
        mock_get_or_create.return_value = (mock_user, True)

        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer valid.token.here")
        user, token = self.auth.authenticate(request)

        # Token claims should be attached to request
        self.assertIsNotNone(request.token_claims)

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    @patch("api.auth.User.objects.get_or_create")
    def test_extracts_org_id_claim(
        self, mock_get_or_create, mock_jwk, mock_jwt_class, mock_get_jwks
    ):
        """Test that org_id custom claim is extracted."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}

        mock_claims = self._create_mock_claims({"org_id": "org-456"})
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = mock_claims
        mock_jwt_class.return_value = mock_jwt

        mock_user = MagicMock()
        mock_get_or_create.return_value = (mock_user, True)

        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer valid.token.here")
        user, token = self.auth.authenticate(request)

        self.assertEqual(request.token_claims.get("org_id"), "org-456")


class TestJWKSCaching(TestCase):
    """Tests for JWKS caching behavior."""

    @patch("api.auth.requests.get")
    @patch("api.auth._jwks_cache.cache_clear")
    def test_jwks_is_fetched_from_keycloak(self, mock_cache_clear, mock_get):
        """Test that JWKS is fetched from Keycloak."""
        from api.auth import _jwks_cache

        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "key-1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Clear cache first
        _jwks_cache.cache_clear()

        # Fetch JWKS
        fetched_at, jwks = _jwks_cache()

        mock_get.assert_called_once()
        self.assertEqual(jwks, {"keys": [{"kid": "key-1"}]})


class TestAudienceValidation(TestCase):
    """Tests for JWT audience validation."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.auth = KeycloakJWTAuthentication()

    @patch("api.auth.get_jwks")
    @patch("api.auth.JsonWebToken")
    @patch("api.auth.JsonWebKey")
    @override_settings(KEYCLOAK_AUDIENCE="expected-audience")
    def test_wrong_audience_raises_authentication_failed(
        self, mock_jwk, mock_jwt_class, mock_get_jwks
    ):
        """Test that wrong audience raises AuthenticationFailed."""
        mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}

        # Create claims with wrong audience
        mock_claims = MagicMock()
        mock_claims.__getitem__ = lambda self, key: {
            "sub": "user-123",
            "iss": "http://keycloak:8080/realms/app",
            "aud": "wrong-audience",
            "exp": int(time.time()) + 3600,
        }[key]
        mock_claims.get = lambda key, default=None: {
            "sub": "user-123",
            "iss": "http://keycloak:8080/realms/app",
            "aud": "wrong-audience",
            "exp": int(time.time()) + 3600,
        }.get(key, default)
        mock_claims.validate = MagicMock()

        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = mock_claims
        mock_jwt_class.return_value = mock_jwt

        request = self.factory.get("/api/v1/test", HTTP_AUTHORIZATION="Bearer valid.token.here")

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)


class TestAuthenticateHeader(TestCase):
    """Tests for WWW-Authenticate header."""

    def test_returns_bearer_realm(self):
        """Test that authenticate_header returns Bearer realm."""
        auth = KeycloakJWTAuthentication()
        request = MagicMock()

        header = auth.authenticate_header(request)

        self.assertIn("Bearer", header)
        self.assertIn("Keycloak", header)
