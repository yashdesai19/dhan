// The reference "today" for all mock data and relative labels (spec §6).
export const TODAY = '2026-09-30';
export const TODAY_TIME = '14:52';

let override: string | null = null;

/** Today's ISO date. Tests can pin a different day with setToday(). */
export function today(): string {
  return override ?? TODAY;
}

export function setToday(date: string | null): void {
  override = date;
}
