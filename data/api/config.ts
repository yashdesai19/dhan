// Where the DHAN API lives, from EXPO_PUBLIC_DHAN_API_URL (see .env.example). Only the test suite
// runs on the built-in mock data; the app itself always uses the real backend, so it never shows
// demo accounts. Only the address is configured here: the app holds no secrets.

// Builds whose profile leaves the variable out (.env never reaches EAS) use the live API
const PRODUCTION_API_URL = 'https://dhan-api-jqfp.onrender.com';
const isTest = process.env.NODE_ENV === 'test';
const raw = process.env.EXPO_PUBLIC_DHAN_API_URL ?? (isTest ? '' : PRODUCTION_API_URL);

export const API_URL = raw.trim().replace(/\/+$/, '');
export const isApiMode = !isTest || API_URL.length > 0;

/** Requests that take longer than this are treated as a network failure. */
export const REQUEST_TIMEOUT_MS = 15_000;

/** DHAN keeps day and month boundaries in India time (backend DEFAULT_TIMEZONE). */
export const IST_OFFSET_MINUTES = 330;
