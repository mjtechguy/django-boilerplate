import os

from keycloak import KeycloakOpenID

SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "app")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "api")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

USERS = ["platform_admin", "org_admin", "org_member", "team_admin", "end_user"]
PASSWORD = "password"


def main():
    kwargs = {"server_url": SERVER_URL, "realm_name": REALM, "client_id": CLIENT_ID}
    if CLIENT_SECRET:
        kwargs["client_secret_key"] = CLIENT_SECRET
    oidc = KeycloakOpenID(**kwargs)
    for user in USERS:
        token = oidc.token(username=user, password=PASSWORD)
        print(f"{user}: {token['access_token']}\n")


if __name__ == "__main__":
    main()
