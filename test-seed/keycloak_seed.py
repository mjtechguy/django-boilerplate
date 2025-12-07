import os

from keycloak import KeycloakAdmin

SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080")
REALM = os.getenv("KEYCLOAK_REALM", "app")
USERNAME = os.getenv("KEYCLOAK_ADMIN", "admin")
PASSWORD = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")

USERS = [
    ("platform_admin", ["platform_admin"], []),
    ("org_admin", ["org_admin"], []),
    ("org_member", ["org_member"], []),
    ("team_admin", ["team_admin"], []),
    ("end_user", [], []),
]


def ensure_user(kc: KeycloakAdmin, username: str, realm_roles, client_roles):
    try:
        user_id = kc.get_user_id(username)
    except Exception:
        user_id = None
    if not user_id:
        kc.create_user(
            {
                "username": username,
                "enabled": True,
                "emailVerified": True,
                "email": f"{username}@example.com",
                "firstName": username,
                "lastName": "User",
                "requiredActions": [],
            }
        )
        user_id = kc.get_user_id(username)
        kc.set_user_password(user_id=user_id, password="password", temporary=False)
        kc.update_user(user_id=user_id, payload={"requiredActions": [], "emailVerified": True})
    for role in realm_roles:
        try:
            role_rep = kc.get_realm_role(role)
        except Exception:
            kc.create_realm_role({"name": role})
            role_rep = kc.get_realm_role(role)
        kc.assign_realm_roles(user_id=user_id, roles=[role_rep])
    # Client role assignment skipped for simplicity; using realm roles above.
    print(f"Ensured user {username}")


def main():
    kc = KeycloakAdmin(
        server_url=SERVER_URL,
        username=USERNAME,
        password=PASSWORD,
        realm_name="master",
        verify=True,
    )
    kc.realm_name = REALM
    for username, realm_roles, client_roles in USERS:
        ensure_user(kc, username, realm_roles, client_roles)


if __name__ == "__main__":
    main()
