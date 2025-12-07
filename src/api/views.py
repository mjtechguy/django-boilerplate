from rest_framework.response import Response
from rest_framework.views import APIView


class AuthPingView(APIView):
    """Authenticated ping to validate JWT/Auth pipeline."""

    def get(self, request):
        claims = getattr(request, "token_claims", {})
        return Response(
            {
                "message": "pong",
                "user": str(request.user),
                "claims_sub": claims.get("sub"),
                "claims_roles": {
                    "realm": claims.get("realm_roles"),
                    "client": claims.get("client_roles"),
                },
            }
        )

    def post(self, request):
        # Same response shape as GET for idempotency tests and simple mutating checks
        return self.get(request)
