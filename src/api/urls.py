from django.urls import path

from api.views import AuthPingView
from api.views_admin import AdminOrgListView
from api.views_audit import (
    AuditChainVerificationView,
    AuditLogExportView,
    AuditLogListView,
    AuditLogVerifyView,
)
from api.views_impersonation import ImpersonationLogListView
from api.views_licensing import OrgLicenseView, StripeWebhookView
from api.views_monitoring import (
    AppMetricsView,
    CeleryHealthView,
    CeleryStatsView,
    LivenessView,
    PrometheusMetricsView,
    QueueStatsView,
    ReadinessView,
    TaskMetricsView,
)
from api.views_protected import SampleProtectedView
from api.views_webhooks import (
    WebhookDeliveryListView,
    WebhookEndpointDetailView,
    WebhookEndpointListCreateView,
    WebhookTestView,
)

urlpatterns = [
    path("ping", AuthPingView.as_view(), name="api-ping"),
    path("protected", SampleProtectedView.as_view(), name="api-protected"),
    path("orgs/<uuid:org_id>/license", OrgLicenseView.as_view(), name="org-license"),
    path("admin/orgs", AdminOrgListView.as_view(), name="admin-org-list"),
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
    # Monitoring endpoints
    path("monitoring/celery/health", CeleryHealthView.as_view(), name="celery-health"),
    path("monitoring/celery/stats", CeleryStatsView.as_view(), name="celery-stats"),
    path("monitoring/queues", QueueStatsView.as_view(), name="queue-stats"),
    path("monitoring/tasks", TaskMetricsView.as_view(), name="task-metrics"),
    path("monitoring/metrics", PrometheusMetricsView.as_view(), name="prometheus-metrics"),
    path("monitoring/metrics/json", AppMetricsView.as_view(), name="app-metrics"),
    # Kubernetes probes
    path("health/ready", ReadinessView.as_view(), name="readiness"),
    path("health/live", LivenessView.as_view(), name="liveness"),
]
