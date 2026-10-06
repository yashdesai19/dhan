// Where the DHAN API lives. Set EXPO_PUBLIC_DHAN_API_URL (see .env.example) to use the real
// backend; leave it unset to run on the built-in mock data (tests, offline demos).
// Only the address is configured here: the app holds no secrets.

const raw = process.env.EXPO_PUBLIC_DHAN_API_URL ?? '';

export const API_URL = raw.trim().replace(/\/+$/, '');
export const isApiMode = API_URL.length > 0;

/** Requests that take longer than this are treated as a network failure. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** DHAN keeps day and month boundaries in India time (backend DEFAULT_TIMEZONE). */
export const IST_OFFSET_MINUTES = 330;
