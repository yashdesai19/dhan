// Date helpers on ISO 'YYYY-MM-DD' strings. All maths is done in UTC so
// labels never shift a day across time zones.
import type { ISODate, MonthKey } from '@/types/domain';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;
const MONTHS_LONG = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
] as const;
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'] as const;
const DAY_MS = 86_400_000;

export function toUTC(date: ISODate): number {
  const [y, m, d] = date.split('-').map(Number);
  return Date.UTC(y ?? 1970, (m ?? 1) - 1, d ?? 1);
}

export function fromUTC(ms: number): ISODate {
  return new Date(ms).toISOString().slice(0, 10);
}

export function addDays(date: ISODate, days: number): ISODate {
  return fromUTC(toUTC(date) + days * DAY_MS);
}

export function daysBetween(from: ISODate, to: ISODate): number {
  return Math.round((toUTC(to) - toUTC(from)) / DAY_MS);
}

export function monthOf(date: ISODate): MonthKey {
  return date.slice(0, 7);
}

export function parts(date: ISODate): { y: number; m: number; d: number; weekday: number } {
  const dt = new Date(toUTC(date));
  return { y: dt.getUTCFullYear(), m: dt.getUTCMonth() + 1, d: dt.getUTCDate(), weekday: dt.getUTCDay() };
}

export function daysInMonth(month: MonthKey): number {
  const [y, m] = month.split('-').map(Number);
  return new Date(Date.UTC(y ?? 1970, m ?? 1, 0)).getUTCDate();
}

export function monthName(month: MonthKey, long = false): string {
  const m = Number(month.slice(5, 7));
  return (long ? MONTHS_LONG : MONTHS).at(m - 1) ?? '';
}

export function monthYear(month: MonthKey): string {
  return `${monthName(month, true)} ${month.slice(0, 4)}`;
}

export function shiftMonth(month: MonthKey, delta: number): MonthKey {
  const [y, m] = month.split('-').map(Number);
  const idx = (y ?? 1970) * 12 + ((m ?? 1) - 1) + delta;
  const ny = Math.floor(idx / 12);
  const nm = (idx % 12) + 1;
  return `${ny}-${String(nm).padStart(2, '0')}`;
}

/** Whole calendar months after `from`'s month up to and including `to`'s month. */
export function monthsUntil(from: ISODate, to: ISODate): number {
  const a = parts(from);
  const b = parts(to);
  return Math.max(0, (b.y - a.y) * 12 + (b.m - a.m));
}

/** "30 Sep" */
export function dayMonth(date: ISODate): string {
  const p = parts(date);
  return `${p.d} ${MONTHS.at(p.m - 1) ?? ''}`;
}

/** "Wed 30 Sep" */
export function weekdayDayMonth(date: ISODate): string {
  const p = parts(date);
  return `${DAYS.at(p.weekday) ?? ''} ${p.d} ${MONTHS.at(p.m - 1) ?? ''}`;
}

/** "31 Mar 2027" */
export function fullDate(date: ISODate): string {
  const p = parts(date);
  return `${p.d} ${MONTHS.at(p.m - 1) ?? ''} ${p.y}`;
}

/** "Dec 2027" */
export function monthShortYear(date: ISODate): string {
  const p = parts(date);
  return `${MONTHS.at(p.m - 1) ?? ''} ${p.y}`;
}

/** Day-group heading on Activity: "Today · Wed 30 Sep", "Yesterday · …", or "Mon 28 Sep". */
export function dayHeading(date: ISODate, today: ISODate): string {
  const diff = daysBetween(date, today);
  if (diff === 0) return `Today · ${weekdayDayMonth(date)}`;
  return weekdayDayMonth(date);
}

/** Relative label for upcoming items: "Today", "Tomorrow", or "in 5 days". */
export function relativeDay(date: ISODate, today: ISODate): string {
  const diff = daysBetween(today, date);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  return diff > 0 ? `in ${diff} days` : `${-diff} days ago`;
}

/** "1:20 pm" from "13:20". */
export function time12(t?: string): string {
  if (!t) return '';
  const [hStr, mStr] = t.split(':');
  const h = Number(hStr);
  const suffix = h >= 12 ? 'pm' : 'am';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${mStr ?? '00'} ${suffix}`;
}

/** Day of the month, month label for date badges: { day: '1', mon: 'OCT' }. */
export function badge(date: ISODate): { day: string; mon: string } {
  const p = parts(date);
  return { day: String(p.d), mon: (MONTHS.at(p.m - 1) ?? '').toUpperCase() };
}

export function isSameMonth(date: ISODate, month: MonthKey): boolean {
  return monthOf(date) === month;
}
