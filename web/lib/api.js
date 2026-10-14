/**
 * Central API client for the Vuna Fresh Django REST Framework backend.
 *
 * JWT storage strategy:
 *  - Access token: React context (memory only). Not accessible to XSS.
 *  - Refresh token: localStorage. Survives page refresh.
 *
 * Upgrade path: when the backend is updated to set tokens in httpOnly cookies
 * via a CookieTokenObtainPairView, remove the localStorage usage here and
 * rely on the browser sending the cookie automatically. That makes tokens
 * completely inaccessible to JavaScript.
 *
 * Usage:
 *   import { apiClient } from '@/lib/api';
 *   const data = await apiClient.get('/products/');
 *   const data = await apiClient.post('/auth/register/', { email, password, ... });
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// In-memory store for the access token (module-level so it survives re-renders
// but is cleared on page refresh — that's intentional).
let _accessToken = null;

export function setAccessToken(token) {
  _accessToken = token;
}

export function getAccessToken() {
  return _accessToken;
}

export function clearTokens() {
  _accessToken = null;
  if (typeof window !== 'undefined') {
    localStorage.removeItem('vf_refresh');
  }
}

export function storeRefreshToken(token) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('vf_refresh', token);
  }
}

export function getRefreshToken() {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('vf_refresh');
  }
  return null;
}

// Shared in-flight refresh, so concurrent 401s (e.g. a page firing several
// requests via Promise.all right as the access token expires) all await the
// SAME refresh call instead of each calling /auth/token/refresh/ on their
// own. With ROTATE_REFRESH_TOKENS on the backend, the first refresh call
// invalidates the old refresh token — a second, independent call reading
// that now-stale token from localStorage would fail and wrongly log the
// user out even though the first refresh actually succeeded.
let _refreshPromise = null;

/**
 * Attempt a silent token refresh. Returns the new access token or null.
 */
async function refreshAccessToken() {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return null;

    try {
      const res = await fetch(`${BASE_URL}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      });

      if (!res.ok) {
        clearTokens();
        return null;
      }

      const data = await res.json();
      setAccessToken(data.access);
      // SimpleJWT with ROTATE_REFRESH_TOKENS=True returns a new refresh token
      if (data.refresh) {
        storeRefreshToken(data.refresh);
      }
      return data.access;
    } catch {
      clearTokens();
      return null;
    }
  })();

  try {
    return await _refreshPromise;
  } finally {
    _refreshPromise = null;
  }
}

// A 401 from these endpoints is an expected, legitimate response (wrong
// credentials at login, etc.) — not a "session expired mid-use" situation,
// so it must NOT trigger the refresh-token dance or get overwritten with the
// generic "Session expired" message below. Let the real backend message
// (e.g. "No active account found with the given credentials") through.
const AUTH_ENDPOINTS_WITHOUT_REFRESH = ['/auth/token/', '/auth/register/'];

/**
 * Core fetch wrapper. Attaches the Bearer token, handles 401 → refresh → retry once.
 */
async function request(path, options = {}, _isRetry = false) {
  const url = `${BASE_URL}${path}`;
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401 && !_isRetry && !AUTH_ENDPOINTS_WITHOUT_REFRESH.includes(path)) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return request(path, options, true);
    }
    // Refresh failed — clear tokens and throw so callers can redirect to login
    clearTokens();
    throw new ApiError(401, 'Session expired. Please log in again.');
  }

  if (!res.ok) {
    let errorMessage = `Request failed (${res.status})`;
    let errorDetail = null;
    try {
      const body = await res.json();
      errorMessage = body?.error?.message || body?.detail || errorMessage;
      errorDetail = body?.error?.detail ?? null;
    } catch {}
    throw new ApiError(res.status, errorMessage, errorDetail);
  }

  // 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

export class ApiError extends Error {
  // detail: per-field validation messages from DRF, e.g. { amount_received: ["..."] }
  constructor(status, message, detail = null) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export const apiClient = {
  get: (path, options) => request(path, { method: 'GET', ...options }),
  post: (path, body, options) =>
    request(path, { method: 'POST', body: JSON.stringify(body), ...options }),
  patch: (path, body, options) =>
    request(path, { method: 'PATCH', body: JSON.stringify(body), ...options }),
  delete: (path, options) => request(path, { method: 'DELETE', ...options }),
};

/**
 * Upload a file via multipart/form-data. Returns the parsed JSON response.
 * Does NOT set Content-Type — the browser sets it automatically with the
 * multipart boundary when the body is a FormData instance.
 */
export async function uploadFile(path, file) {
  const formData = new FormData();
  formData.append('file', file);

  const url = `${BASE_URL}${path}`;
  const headers = {};
  const token = getAccessToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { method: 'POST', headers, body: formData });

  if (!res.ok) {
    let errorMessage = `Upload failed (${res.status})`;
    try {
      const body = await res.json();
      errorMessage = body?.error?.message || body?.detail || errorMessage;
    } catch {}
    throw new ApiError(res.status, errorMessage);
  }

  return res.json();
}
