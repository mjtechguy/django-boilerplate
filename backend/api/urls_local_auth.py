"""
URL patterns for local authentication endpoints.

All endpoints are prefixed with /api/v1/auth/
"""

from django.urls import path

from api.views_local_auth import (
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RegisterView,
    TokenRefreshView,
)
from api.views_password_reset import (
    EmailVerificationView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ResendVerificationView,
)

urlpatterns = [
    # Registration and login
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),

    # Token management
    path("refresh", TokenRefreshView.as_view(), name="auth-refresh"),

    # User profile
    path("me", CurrentUserView.as_view(), name="auth-me"),
    path("change-password", ChangePasswordView.as_view(), name="auth-change-password"),

    # Email verification
    path("verify-email", EmailVerificationView.as_view(), name="auth-verify-email"),
    path("resend-verification", ResendVerificationView.as_view(), name="auth-resend-verification"),

    # Password reset
    path("password-reset", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password-reset/confirm",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
