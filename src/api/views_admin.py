from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Org


def _is_platform_admin(claims) -> bool:
    roles = (claims.get("realm_roles") or []) + (claims.get("client_roles") or [])
    return "platform_admin" in roles


class AdminOrgListView(APIView):
    """
    Global admin view for listing orgs (support/platform).
    """

    def get(self, request):
        claims = getattr(request, "token_claims", {})
        if not _is_platform_admin(claims):
            return Response({"detail": _("Forbidden")}, status=status.HTTP_403_FORBIDDEN)
        orgs = Org.objects.all().values("id", "name", "status", "license_tier")
        return Response({"results": list(orgs)})
