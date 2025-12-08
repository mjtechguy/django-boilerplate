import { UserManager, WebStorageStateStore, type UserManagerSettings } from "oidc-client-ts";

const keycloakUrl = import.meta.env.VITE_KEYCLOAK_URL || "http://localhost:8080";
const realm = import.meta.env.VITE_KEYCLOAK_REALM || "app";
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || "api";

export const oidcSettings: UserManagerSettings = {
  authority: `${keycloakUrl}/realms/${realm}`,
  client_id: clientId,
  redirect_uri: `${window.location.origin}/callback`,
  post_logout_redirect_uri: `${window.location.origin}/login`,
  response_type: "code",
  scope: "openid profile email",
  automaticSilentRenew: true,
  silentRequestTimeoutInSeconds: 10,
  userStore: new WebStorageStateStore({ store: sessionStorage }),
  monitorSession: true,
  filterProtocolClaims: true,
  loadUserInfo: true,
};

let userManagerInstance: UserManager | null = null;

export function getUserManager(): UserManager {
  if (!userManagerInstance) {
    userManagerInstance = new UserManager(oidcSettings);
  }
  return userManagerInstance;
}

export function resetUserManager(): void {
  userManagerInstance = null;
}
