/**
 * Local authentication API client.
 *
 * Handles all API calls for local username/password authentication.
 */

import type { LoginResponse, RegisterData } from "@/types/auth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface ApiError {
  error: string;
  detail?: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || data.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function loginLocal(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });

  return handleResponse<LoginResponse>(response);
}

export async function register(data: RegisterData): Promise<{ message: string; email: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return handleResponse(response);
}

export async function refreshAccessToken(
  refreshToken: string
): Promise<{ access_token: string; token_type: string; expires_in: number }> {
  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  return handleResponse(response);
}

export async function logout(
  refreshToken?: string,
  accessToken?: string
): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/logout`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok && response.status !== 401) {
    // Ignore 401 errors on logout - token might be expired
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "Logout failed");
  }
}

export async function verifyEmail(token: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/verify-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token }),
  });

  return handleResponse(response);
}

export async function resendVerification(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/resend-verification`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  return handleResponse(response);
}

export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/password-reset`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  return handleResponse(response);
}

export async function confirmPasswordReset(
  token: string,
  password: string,
  passwordConfirm: string
): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/password-reset/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      token,
      password,
      password_confirm: passwordConfirm,
    }),
  });

  return handleResponse(response);
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
  newPasswordConfirm: string,
  accessToken: string
): Promise<{ message: string }> {
  const response = await fetch(`${API_URL}/api/v1/auth/change-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
      new_password_confirm: newPasswordConfirm,
    }),
  });

  return handleResponse(response);
}

export async function getCurrentUser(accessToken: string): Promise<{
  id: string;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
  email_verified: boolean;
  auth_provider: string;
  roles: string[];
}> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return handleResponse(response);
}
