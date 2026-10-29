// Where the DHAN API lives, from EXPO_PUBLIC_DHAN_API_URL (see .env.example). Only the test suite
// runs on the built-in mock data; the app itself always uses the real backend, so it never shows
// demo accounts. Only the address is configured here: the app holds no secrets.

const raw = process.env.EXPO_PUBLIC_DHAN_API_URL ?? '';
const isTest = process.env.NODE_ENV === 'test';

export const API_URL = raw.trim().replace(/\/+$/, '');
export const isApiMode = !isTest || API_URL.length > 0;

if (isApiMode && !API_URL) {
  throw new Error('EXPO_PUBLIC_DHAN_API_URL is not set: add it to .env (see .env.example)');
}

/** Requests that take longer than this are treated as a network failure. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** DHAN keeps day and month boundaries in India time (backend DEFAULT_TIMEZONE). */
export const IST_OFFSET_MINUTES = 330;
