// Access token lives in memory only (cleared on page reload); refresh token persists in
// localStorage so a session survives a reload. See docs/03-ROADMAP.md Phase 2 plan notes for
// the httpOnly-cookie tradeoff this accepts for now.
const REFRESH_TOKEN_KEY = "atm_refresh_token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function setTokens(accessTok: string, refreshTok: string): void {
  setAccessToken(accessTok);
  setRefreshToken(refreshTok);
}

export function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}
