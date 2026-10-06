// HTTP client for the DHAN API: bearer auth, one shared token refresh on 401, timeouts, and
// errors turned into sentences the screens can show as they are.
import { API_URL, REQUEST_TIMEOUT_MS } from './config';
import { tokens } from './tokens';

export type ApiErrorCode = 'offline' | 'failed' | 'invalid' | 'not_found' | 'unauthorized' | 'limited';

/** Same shape as the mock layer's MockError: screens show `message` and may check `code`. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: ApiErrorCode = 'failed',
    readonly status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const OFFLINE = 'You’re offline. Check your connection and try again.';
const SESSION_ENDED = 'Your session has ended. Please log in again.';

let onSessionExpired: (() => void) | null = null;

/** The app registers what to do when the session can't be renewed (sign out, clear caches). */
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

async function expireSession(): Promise<void> {
  await tokens.clear();
  onSessionExpired?.();
}

async function send(method: string, path: string, body: unknown, token: string | null) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(`${API_URL}${path}`, {
      method,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch {
    // DNS failure, no route, server down, or our timeout: all look the same to the user
    throw new ApiError(OFFLINE, 'offline');
  } finally {
    clearTimeout(timer);
  }
}

function firstValidationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail) || detail.length === 0) return null;
  const first = detail[0] as { msg?: string; loc?: unknown[] };
  if (!first?.msg) return null;
  const msg = first.msg.replace(/^Value error, /, '');
  const field = Array.isArray(first.loc) ? String(first.loc[first.loc.length - 1] ?? '') : '';
  return field && !msg.toLowerCase().includes(field.toLowerCase()) ? `${msg} (${field})` : msg;
}

async function toError(res: Response): Promise<ApiError> {
  let detail: unknown = null;
  try {
    detail = ((await res.json()) as { detail?: unknown }).detail;
  } catch {
    // no JSON body
  }
  const text = typeof detail === 'string' ? detail : firstValidationMessage(detail);
  if (res.status === 429) {
    return new ApiError(text ?? 'Too many attempts. Please wait and try again.', 'limited', 429);
  }
  if (res.status >= 500) {
    return new ApiError('Something went wrong on our side. Please try again.', 'failed', res.status);
  }
  if (res.status === 404) return new ApiError(text ?? 'That no longer exists.', 'not_found', 404);
  if (res.status === 401) return new ApiError(text ?? SESSION_ENDED, 'unauthorized', 401);
  return new ApiError(text ?? 'Check the details and try again.', 'invalid', res.status);
}

let refreshing: Promise<boolean> | null = null;

/**
 * Trades the refresh token for new tokens. Concurrent 401s share one refresh. Resolves false only
 * when the server rejects the token; a server error or rate limit throws instead, so an outage
 * fails the request but keeps the user signed in.
 */
function refreshSession(): Promise<boolean> {
  refreshing ??= (async () => {
    const refreshToken = await tokens.refresh();
    if (!refreshToken) return false;
    const res = await send('POST', '/auth/refresh', { refresh_token: refreshToken }, null);
    if (res.status >= 500 || res.status === 429) throw await toError(res);
    if (!res.ok) return false;
    const body = (await res.json()) as { access_token: string; refresh_token: string };
    await tokens.save(body.access_token, body.refresh_token);
    return true;
  })().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

export interface RequestOptions {
  /** false for login/register: no token is sent and a 401 is just a wrong password. */
  auth?: boolean;
}

export async function request<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
  { auth = true }: RequestOptions = {},
): Promise<T> {
  let res = await send(method, path, body, auth ? await tokens.access() : null);

  if (auth && res.status === 401) {
    // Access token expired (or missing): renew once, then retry the original request
    if (!(await refreshSession())) {
      await expireSession();
      throw new ApiError(SESSION_ENDED, 'unauthorized', 401);
    }
    res = await send(method, path, body, await tokens.access());
    if (res.status === 401) {
      await expireSession();
      throw new ApiError(SESSION_ENDED, 'unauthorized', 401);
    }
  }

  if (!res.ok) {
    const error = await toError(res);
    // A disabled account can't do anything: end the session rather than fail every screen
    if (auth && res.status === 403 && /disabled|inactive/i.test(error.message)) await expireSession();
    throw error;
  }
  // Read as text first: an empty body is "no content", and a garbled one names the endpoint
  const text = res.status === 204 ? '' : await res.text();
  if (!text) return undefined as T;
  try {
    return JSON.parse(text) as T;
  } catch {
    console.warn(
      `DHAN API: unreadable response from ${method} ${path} (${res.status}, ${text.length} chars)`,
    );
    throw new ApiError('The server sent an unexpected reply. Please try again.', 'failed', res.status);
  }
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>('POST', path, body ?? {}, opts),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: <T = void>(path: string) => request<T>('DELETE', path),
};
