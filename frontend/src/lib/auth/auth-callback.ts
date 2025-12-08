import { getUserManager } from "./oidc-config";

interface ProfileWithRoles {
  realm_access?: { roles?: string[] };
  roles?: string[];
}

export async function handleAuthCallback(): Promise<string> {
  const userManager = getUserManager();

  try {
    const user = await userManager.signinRedirectCallback();
    const profile = user.profile as ProfileWithRoles;

    // Determine redirect based on user roles
    const roles = [
      ...(profile.realm_access?.roles ?? []),
      ...(profile.roles ?? []),
    ];

    if (roles.includes("platform_admin")) {
      return "/admin";
    }
    if (roles.includes("org_admin")) {
      return "/org";
    }
    return "/app";
  } catch (error) {
    console.error("Auth callback failed:", error);
    throw error;
  }
}

export async function handleSilentCallback(): Promise<void> {
  const userManager = getUserManager();
  await userManager.signinSilentCallback();
}
