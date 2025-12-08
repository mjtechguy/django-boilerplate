from django.urls import include, path

from api.views import AuthPingView
from api.views_admin_orgs import AdminOrgDetailView, AdminOrgListCreateView
from api.views_admin_teams import (
    AdminTeamDetailView,
    AdminTeamListCreateView,
    AdminTeamMembersView,
)
from api.views_admin_users import (
    AdminUserDetailView,
    AdminUserInviteView,
    AdminUserListCreateView,
    AdminUserMembershipsView,
    AdminUserResendInviteView,
)
from api.views_admin_memberships import (
    AdminMembershipDetailView,
    AdminMembershipListCreateView,
)
from api.views_alerts import AlertListView
from api.views_audit import (
    AuditChainVerificationView,
    AuditLogExportView,
    AuditLogListView,
    AuditLogVerifyView,
)
from api.views_impersonation import ImpersonationLogListView
from api.views_billing import (
    AvailablePlansView,
    BillingPortalView,
    BillingStatusView,
    CheckoutSessionView,
    CreateStripeCustomerView,
)
from api.views_licensing import OrgLicenseView, StripeWebhookView
from api.views_monitoring import (
    AppMetricsView,
    CeleryHealthView,
    CeleryStatsView,
    LivenessView,
    PrometheusMetricsView,
    QueueStatsView,
    ReadinessView,
    ServerMetricsView,
    SystemOverviewView,
    TaskMetricsView,
)
from api.views_protected import SampleProtectedView
from api.views_site_settings import SiteSettingsAdminView, SiteSettingsView
from api.views_webhooks import (
    WebhookDeliveryListView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
    WebhookTestView,
)

urlpatterns = [
    # Local authentication
    path("auth/", include("api.urls_local_auth")),

    path("ping", AuthPingView.as_view(), name="api-ping"),
    path("protected", SampleProtectedView.as_view(), name="api-protected"),
    path("orgs/<uuid:org_id>/license", OrgLicenseView.as_view(), name="org-license"),
    # Billing endpoints
    path("orgs/<uuid:org_id>/billing", BillingStatusView.as_view(), name="org-billing-status"),
    path("orgs/<uuid:org_id>/billing/checkout", CheckoutSessionView.as_view(), name="org-billing-checkout"),
    path("orgs/<uuid:org_id>/billing/portal", BillingPortalView.as_view(), name="org-billing-portal"),
    path("orgs/<uuid:org_id>/billing/customer", CreateStripeCustomerView.as_view(), name="org-billing-customer"),
    path("billing/plans", AvailablePlansView.as_view(), name="billing-plans"),
    path("admin/orgs", AdminOrgListCreateView.as_view(), name="admin-org-list"),
    path("admin/orgs/<uuid:org_id>", AdminOrgDetailView.as_view(), name="admin-org-detail"),
    # Team admin endpoints
    path("admin/teams", AdminTeamListCreateView.as_view(), name="admin-team-list"),
    path("admin/teams/<uuid:team_id>", AdminTeamDetailView.as_view(), name="admin-team-detail"),
    path("admin/teams/<uuid:team_id>/members", AdminTeamMembersView.as_view(), name="admin-team-members"),
    # User admin endpoints
    path("admin/users", AdminUserListCreateView.as_view(), name="admin-user-list"),
    path("admin/users/invite", AdminUserInviteView.as_view(), name="admin-user-invite"),
    path("admin/users/<int:user_id>", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:user_id>/memberships", AdminUserMembershipsView.as_view(), name="admin-user-memberships"),
    path("admin/users/<int:user_id>/resend-invite", AdminUserResendInviteView.as_view(), name="admin-user-resend-invite"),
    # Membership admin endpoints
    path("admin/memberships", AdminMembershipListCreateView.as_view(), name="admin-membership-list"),
    path("admin/memberships/<uuid:membership_id>", AdminMembershipDetailView.as_view(), name="admin-membership-detail"),
    path("admin/settings/site", SiteSettingsAdminView.as_view(), name="admin-site-settings"),
    # Admin alerts (aggregated from multiple sources)
    path("admin/alerts", AlertListView.as_view(), name="admin-alerts"),
    # Public site settings (for branding)
    path("settings/site", SiteSettingsView.as_view(), name="site-settings"),
    path("stripe/webhook", StripeWebhookView.as_view(), name="stripe-webhook"),
    # Audit endpoints
    path("audit", AuditLogListView.as_view(), name="audit-list"),
    path("audit/export", AuditLogExportView.as_view(), name="audit-export"),
    path("audit/verify", AuditLogVerifyView.as_view(), name="audit-verify"),
    path(
        "audit/chain-verify",
        AuditChainVerificationView.as_view(),
        name="audit-chain-verify",
    ),
    # Impersonation endpoints
    path(
        "admin/impersonation/logs",
        ImpersonationLogListView.as_view(),
        name="impersonation-logs",
    ),
    # Webhook endpoints
    path("webhooks", WebhookEndpointListCreateView.as_view(), name="webhook-list"),
    path("webhooks/<uuid:pk>", WebhookEndpointDetailView.as_view(), name="webhook-detail"),
    path(
        "webhooks/<uuid:pk>/deliveries",
        WebhookDeliveryListView.as_view(),
        name="webhook-deliveries",
    ),
    path("webhooks/<uuid:pk>/test", WebhookTestView.as_view(), name="webhook-test"),
    # Monitoring endpoints (platform_admin only)
    path("monitoring/overview", SystemOverviewView.as_view(), name="system-overview"),
    path("monitoring/server", ServerMetricsView.as_view(), name="server-metrics"),
    path("monitoring/celery/health", CeleryHealthView.as_view(), name="celery-health"),
    path("monitoring/celery/stats", CeleryStatsView.as_view(), name="celery-stats"),
    path("monitoring/queues", QueueStatsView.as_view(), name="queue-stats"),
    path("monitoring/tasks", TaskMetricsView.as_view(), name="task-metrics"),
    path("monitoring/metrics", PrometheusMetricsView.as_view(), name="prometheus-metrics"),
    path("monitoring/metrics/json", AppMetricsView.as_view(), name="app-metrics"),
    # Kubernetes probes (public for K8s)
    path("health/ready", ReadinessView.as_view(), name="readiness"),
    path("health/live", LivenessView.as_view(), name="liveness"),
]
