import { apiFetch } from "./client";
import type { components } from "./schema";
import { clearTokens, getRefreshToken, setTokens } from "./token-store";

export type AuthResponse = components["schemas"]["AuthResponse"];
export type UserResponse = components["schemas"]["UserResponse"];
export type RegisterRequest = components["schemas"]["RegisterRequest"];
export type LoginRequest = components["schemas"]["LoginRequest"];

async function handleAuthResponse(
  response: AuthResponse,
): Promise<AuthResponse> {
  setTokens(response.tokens.access_token, response.tokens.refresh_token);
  return response;
}

export async function register(body: RegisterRequest): Promise<AuthResponse> {
  const response = await apiFetch<AuthResponse>("/auth/register", {
    method: "POST",
    body,
    skipAuth: true,
  });
  return handleAuthResponse(response);
}

export async function login(body: LoginRequest): Promise<AuthResponse> {
  const response = await apiFetch<AuthResponse>("/auth/login", {
    method: "POST",
    body,
    skipAuth: true,
  });
  return handleAuthResponse(response);
}

export async function getCurrentUser(): Promise<UserResponse> {
  return apiFetch<UserResponse>("/auth/me");
}

/** Attempts to restore a session from the refresh token persisted in localStorage. Used on
 * app load, since the access token itself only lives in memory and doesn't survive a reload. */
export async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const tokens = await apiFetch<{
      access_token: string;
      refresh_token: string;
    }>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipAuth: true,
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export function logout(): void {
  clearTokens();
}
