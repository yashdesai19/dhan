// The reference "today" for all mock data and relative labels (spec §6). With the real API the
// app uses the actual date (India time, matching the server's day and month boundaries).
import { isApiMode } from '@/data/api/config';
import { istToday } from '@/data/api/mappers';

export const TODAY = '2026-09-30';
export const TODAY_TIME = '14:52';

let override: string | null = null;

/** Today's ISO date. Tests can pin a different day with setToday(). */
export function today(): string {
  return override ?? (isApiMode ? istToday() : TODAY);
}

export function setToday(date: string | null): void {
  override = date;
}
