// Indian-rupee formatting (en-IN grouping: 1,00,000). Implemented by hand so it
// behaves the same on Hermes, iOS and Android regardless of Intl support.

export const MINUS = '−';

/** Groups digits the Indian way: 124580 → "1,24,580". */
export function groupIN(n: number): string {
  const abs = Math.abs(Math.round(n));
  const s = String(abs);
  if (s.length <= 3) return s;
  const last3 = s.slice(-3);
  let head = s.slice(0, -3);
  const parts: string[] = [];
  while (head.length > 2) {
    parts.unshift(head.slice(-2));
    head = head.slice(0, -2);
  }
  if (head) parts.unshift(head);
  return `${parts.join(',')},${last3}`;
}

export type Sign = 'auto' | 'plus' | 'minus' | 'none';

/**
 * Formats integer rupees. `sign`:
 * - auto: "−₹450" for negatives, "₹450" otherwise
 * - plus: "+₹450" (always shows direction)
 * - minus: "−₹450" (value treated as an outflow)
 * - none: "₹450" (absolute value)
 */
export function inr(n: number, sign: Sign = 'auto'): string {
  const body = `₹${groupIN(n)}`;
  switch (sign) {
    case 'plus':
      return n < 0 ? `${MINUS}${body}` : `+${body}`;
    case 'minus':
      return `${MINUS}${body}`;
    case 'none':
      return body;
    default:
      return n < 0 ? `${MINUS}${body}` : body;
  }
}

/** Formats a keypad string ("1234.5") with Indian grouping, keeping the typed decimals. */
export function formatAmountInput(raw: string): string {
  const [int = '0', dec] = raw.split('.');
  const grouped = groupIN(Number(int || '0'));
  return dec !== undefined ? `${grouped}.${dec}` : grouped;
}

export function percent(part: number, whole: number): number {
  if (whole === 0) return 0;
  return Math.round((part / whole) * 100);
}

/** "+42%" / "−12%" */
export function signedPercent(p: number): string {
  if (p > 0) return `+${p}%`;
  if (p < 0) return `${MINUS}${Math.abs(p)}%`;
  return '0%';
}

/** Screen-reader form: "450 rupees". */
export function inrSpoken(n: number): string {
  return `${Math.abs(Math.round(n))} rupees`;
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
}

export function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
