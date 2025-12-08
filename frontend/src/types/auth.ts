export type AuthProvider = "local" | "oidc";

export interface AuthUser {
  sub: string;
  email: string;
  name: string;
  preferred_username?: string;
  realmRoles: string[];
  clientRoles: string[];
  orgId?: string;
  teamIds?: string[];
  authProvider?: AuthProvider;
  emailVerified?: boolean;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: AuthUser | null;
  authProvider: AuthProvider | null;
  // OIDC login
  login: () => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
  // Local auth
  loginLocal: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
}

export interface RegisterData {
  email: string;
  password: string;
  password_confirm: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LocalTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

export type UserRole =
  | "platform_admin"
  | "support_readonly"
  | "org_admin"
  | "org_member"
  | "team_admin"
  | "team_member"
  | "billing_admin";
