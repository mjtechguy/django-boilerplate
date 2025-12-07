import json
import os

from keycloak import KeycloakOpenID


def main() -> None:
    server_url = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
    realm = os.getenv("KEYCLOAK_REALM", "app")
    client_id = os.getenv("KEYCLOAK_CLIENT_ID", "api")
    keycloak_openid = KeycloakOpenID(
        server_url=server_url,
        realm_name=realm,
        client_id=client_id,
    )
    well_known = keycloak_openid.well_known()
    print(
        json.dumps({"jwks_uri": well_known["jwks_uri"], "issuer": well_known["issuer"]}, indent=2)
    )


if __name__ == "__main__":
    main()
