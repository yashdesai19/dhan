// Numeric keypad rules for amount entry (spec §14).

/** Keypad rules (spec §14): max 9 digits, 2 decimals; ⌫ on one digit returns 0. */
export function pressKey(amount: string, key: string): string {
  if (key === 'del') return amount.length > 1 ? amount.slice(0, -1) : '0';
  if (key === '.') return amount.includes('.') ? amount : `${amount}.`;
  const [, dec] = amount.split('.');
  if (dec !== undefined && dec.length >= 2) return amount;
  if (amount.replace('.', '').length >= 9) return amount;
  return amount === '0' ? key : amount + key;
}

export function amountValue(amount: string): number {
  const n = Number(amount);
  return Number.isFinite(n) ? n : 0;
}
