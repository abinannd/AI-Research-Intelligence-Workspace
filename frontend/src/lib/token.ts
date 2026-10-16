const STORAGE_KEY = "ari_access_token";

let memoryToken: string | null = null;

export function getAccessToken(): string | null {
  if (memoryToken) return memoryToken;
  if (typeof window === "undefined") return null;
  memoryToken = window.localStorage.getItem(STORAGE_KEY);
  return memoryToken;
}

export function setAccessToken(token: string | null): void {
  memoryToken = token;
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}
