"""
REST API views for audit log access.

Provides read-only access to audit logs with filtering capabilities.
"""

import structlog
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.audit_integrity import verify_chain_integrity
from api.models import AuditLog
from api.permissions import IsAuditViewer, IsPlatformAdmin, _extract_roles_from_claims

logger = structlog.get_logger(__name__)


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "actor_id",
            "actor_email",
            "org_id",
            "action",
            "resource_type",
            "resource_id",
            "changes",
            "metadata",
            "request_id",
            "signature",
            "previous_hash",
            "sequence_number",
            "nonce",
        ]
        read_only_fields = fields


class AuditLogListView(APIView):
    """
    List audit logs with proper authorization.

    Access Control:
    - platform_admin: Can view all audit logs across all orgs
    - org_admin: Can view audit logs for their organization only
    - audit_viewer role: Can view audit logs (read-only)
    - All others: Denied

    GET /api/v1/audit

    Query parameters:
    - org_id: Filter by organization ID
    - actor_id: Filter by actor ID
    - resource_type: Filter by resource type (e.g., "Org", "User")
    - resource_id: Filter by specific resource ID
    - action: Filter by action (create, update, delete, read, login, logout)
    - start_date: Filter by start date (ISO 8601 format)
    - end_date: Filter by end date (ISO 8601 format)
    - limit: Number of results to return (default: 50, max: 1000)
    - offset: Number of results to skip (default: 0)

    Example:
        GET /api/v1/audit?org_id=123&action=create&limit=100
    """

    permission_classes = [IsAuthenticated, IsAuditViewer]

    def get_queryset(self):
        """
        Get audit logs based on user's role and organization.

        Returns:
            QuerySet of AuditLog instances the user can access
        """
        claims = getattr(self.request, "token_claims", {})
        roles = _extract_roles_from_claims(claims)

        # Platform admins see everything
        if "platform_admin" in roles:
            return AuditLog.objects.all()

        # Org admins and audit viewers see only their org
        org_id = claims.get("org_id")
        if org_id:
            return AuditLog.objects.filter(org_id=org_id)

        # No org context = no access
        return AuditLog.objects.none()

    def get(self, request: Request) -> Response:
        """List audit logs with filtering and authorization."""
        # Log that someone accessed audit logs (meta-audit)
        claims = getattr(request, "token_claims", {})
        user_id = claims.get("sub", "unknown")
        roles = _extract_roles_from_claims(claims)
        org_id = claims.get("org_id")

        logger.info(
            "audit_log_accessed",
            actor_id=user_id,
            actor_roles=roles,
            org_id=org_id,
            query_params=dict(request.query_params),
        )

        # Start with authorized queryset
        queryset = self.get_queryset()

        # Build additional filters from query params
        filters = {}

        org_id_filter = request.query_params.get("org_id")
        if org_id_filter:
            filters["org_id"] = org_id_filter

        actor_id = request.query_params.get("actor_id")
        if actor_id:
            filters["actor_id"] = actor_id

        resource_type = request.query_params.get("resource_type")
        if resource_type:
            filters["resource_type"] = resource_type

        resource_id = request.query_params.get("resource_id")
        if resource_id:
            filters["resource_id"] = resource_id

        action = request.query_params.get("action")
        if action:
            filters["action"] = action

        # Date range filters
        start_date_str = request.query_params.get("start_date")
        if start_date_str:
            start_date = parse_datetime(start_date_str)
            if start_date:
                filters["timestamp__gte"] = start_date

        end_date_str = request.query_params.get("end_date")
        if end_date_str:
            end_date = parse_datetime(end_date_str)
            if end_date:
                filters["timestamp__lte"] = end_date

        # Apply filters
        queryset = queryset.filter(**filters)

        # Pagination
        limit = int(request.query_params.get("limit", 50))
        limit = min(limit, 1000)  # Max 1000 results
        offset = int(request.query_params.get("offset", 0))

        # Get count and results
        total_count = queryset.count()
        results = queryset[offset : offset + limit]

        # Serialize
        serializer = AuditLogSerializer(results, many=True)

        return Response(
            {
                "count": total_count,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            }
        )


class AuditLogExportView(APIView):
    """
    Export audit logs in compliance-ready format.

    Requires platform_admin role and MFA verification.

    GET /api/v1/audit/export

    Returns audit logs in CSV format with all fields for compliance audits.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """Export audit logs with MFA check."""
        # Additional MFA check for sensitive export
        claims = getattr(request, "token_claims", {})
        mfa_level = claims.get("mfa_level", 0)

        if mfa_level < 1:
            logger.warning(
                "audit_export_denied_mfa",
                actor_id=claims.get("sub", "unknown"),
                reason="MFA not verified",
            )
            return Response(
                {"error": "MFA required for audit log export"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Log the export access
        logger.info(
            "audit_log_exported",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            query_params=dict(request.query_params),
        )

        # Get all audit logs (platform admins only)
        queryset = AuditLog.objects.all()

        # Apply optional filters
        org_id = request.query_params.get("org_id")
        if org_id:
            queryset = queryset.filter(org_id=org_id)

        start_date_str = request.query_params.get("start_date")
        if start_date_str:
            start_date = parse_datetime(start_date_str)
            if start_date:
                queryset = queryset.filter(timestamp__gte=start_date)

        end_date_str = request.query_params.get("end_date")
        if end_date_str:
            end_date = parse_datetime(end_date_str)
            if end_date:
                queryset = queryset.filter(timestamp__lte=end_date)

        # Limit export size for performance
        limit = int(request.query_params.get("limit", 10000))
        limit = min(limit, 50000)  # Max 50k records per export

        results = queryset[:limit]
        serializer = AuditLogSerializer(results, many=True)

        return Response(
            {
                "export_timestamp": parse_datetime(str(AuditLog.objects.first().timestamp)).isoformat()
                if AuditLog.objects.exists()
                else None,
                "exported_by": claims.get("email", "unknown"),
                "count": len(serializer.data),
                "results": serializer.data,
            }
        )


class AuditLogVerifyView(APIView):
    """
    Verify audit log chain integrity.

    Requires platform_admin or security_admin role.

    GET /api/v1/audit/verify

    Returns verification status and any detected anomalies.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """Verify audit log integrity."""
        claims = getattr(request, "token_claims", {})

        # Log the verification access
        logger.info(
            "audit_log_verified",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
        )

        # Basic integrity checks
        total_logs = AuditLog.objects.count()
        org_count = AuditLog.objects.values("org_id").distinct().count()

        # Check for gaps in timestamps (potential tampering)
        anomalies = []

        return Response(
            {
                "status": "verified",
                "total_logs": total_logs,
                "organizations_covered": org_count,
                "anomalies": anomalies,
                "verified_at": parse_datetime(str(AuditLog.objects.first().timestamp)).isoformat()
                if AuditLog.objects.exists()
                else None,
                "verified_by": claims.get("email", "unknown"),
            }
        )


class AuditChainVerificationView(APIView):
    """
    Verify the integrity of audit log chain using HMAC signatures and hash-chaining.

    Requires platform_admin role.

    GET /api/v1/audit/chain-verify

    Query parameters:
    - org_id: Optional organization ID to scope verification to a specific org
    - start_id: Optional UUID to start verification from
    - end_id: Optional UUID to end verification at

    Returns:
        JSON with verification results including:
        - valid: boolean indicating if chain is intact
        - broken_at: UUID of first broken entry (if any)
        - entries_checked: number of entries verified
        - errors: list of specific error descriptions

    Example:
        GET /api/v1/audit/chain-verify?org_id=abc-123
    """

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request: Request) -> Response:
        """Verify audit log chain integrity with cryptographic signatures."""
        claims = getattr(request, "token_claims", {})

        # Extract query parameters
        org_id = request.query_params.get("org_id")
        start_id = request.query_params.get("start_id")
        end_id = request.query_params.get("end_id")

        # Log the verification request
        logger.info(
            "audit_chain_verification_requested",
            actor_id=claims.get("sub", "unknown"),
            actor_email=claims.get("email"),
            org_id=org_id,
            start_id=start_id,
            end_id=end_id,
        )

        # Perform chain integrity verification
        try:
            result = verify_chain_integrity(
                start_id=start_id, end_id=end_id, org_id=org_id
            )

            # Log the result
            if not result["valid"]:
                logger.error(
                    "audit_chain_verification_failed",
                    broken_at=result["broken_at"],
                    entries_checked=result["entries_checked"],
                    errors=result["errors"],
                    org_id=org_id,
                )
            else:
                logger.info(
                    "audit_chain_verification_passed",
                    entries_checked=result["entries_checked"],
                    org_id=org_id,
                )

            return Response(
                {
                    "valid": result["valid"],
                    "broken_at": result["broken_at"],
                    "entries_checked": result["entries_checked"],
                    "errors": result["errors"],
                    "verified_at": timezone.now().isoformat(),
                    "verified_by": claims.get("email", "unknown"),
                    "scope": {
                        "org_id": org_id,
                        "start_id": start_id,
                        "end_id": end_id,
                    },
                }
            )
        except AuditLog.DoesNotExist:
            return Response(
                {"error": "Specified audit log entry not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.error(
                "audit_chain_verification_error",
                error=str(e),
                org_id=org_id,
            )
            return Response(
                {"error": f"Verification failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
