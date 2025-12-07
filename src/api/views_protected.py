from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import CerbosPermission


class SampleProtectedView(APIView):
    permission_classes = [CerbosPermission]
    resource_kind = "sample_resource"
    resource_attrs = {"org_id": "org-123"}
    actions = ["read"]

    def get(self, request):
        return Response({"message": "protected-ok", "org": self.resource_attrs["org_id"]})
