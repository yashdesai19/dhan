import * as seed from '@/mock/seed';
import { TODAY } from '@/mock/clock';
import { dayHeading, monthsUntil, relativeDay, time12, weekdayDayMonth } from '@/utils/dates';
import { applyFilters, defaultFilters } from '@/utils/filters';
import { formatAmountInput, groupIN, inr, signedPercent } from '@/utils/format';
import { pressKey } from '@/utils/keypad';

describe('INR formatting', () => {
  it('groups the Indian way', () => {
    expect(groupIN(124580)).toBe('1,24,580');
    expect(groupIN(100000)).toBe('1,00,000');
    expect(groupIN(12000)).toBe('12,000');
    expect(groupIN(450)).toBe('450');
    expect(groupIN(21868000)).toBe('2,18,68,000');
  });
  it('signs amounts with a real minus sign', () => {
    expect(inr(-450)).toBe('−₹450');
    expect(inr(35000, 'plus')).toBe('+₹35,000');
    expect(inr(450, 'minus')).toBe('−₹450');
    expect(inr(-5000, 'none')).toBe('₹5,000');
    expect(signedPercent(-12)).toBe('−12%');
    expect(signedPercent(42)).toBe('+42%');
  });
  it('formats keypad input with decimals intact', () => {
    expect(formatAmountInput('35000')).toBe('35,000');
    expect(formatAmountInput('1234.5')).toBe('1,234.5');
  });
});

describe('keypad', () => {
  it('follows the spec rules', () => {
    expect(pressKey('0', '4')).toBe('4');
    expect(pressKey('45', '0')).toBe('450');
    expect(pressKey('450', '.')).toBe('450.');
    expect(pressKey('450.5', '.')).toBe('450.5');
    expect(pressKey('450.55', '1')).toBe('450.55');
    expect(pressKey('123456789', '1')).toBe('123456789');
    expect(pressKey('4', 'del')).toBe('0');
    expect(pressKey('450', 'del')).toBe('45');
  });
});

describe('dates', () => {
  it('labels days relative to the mock clock', () => {
    expect(dayHeading('2026-09-30', TODAY)).toBe(`Today · ${weekdayDayMonth('2026-09-30')}`);
    expect(relativeDay('2026-10-01', TODAY)).toBe('Tomorrow');
    expect(time12('13:20')).toBe('1:20 pm');
    expect(time12('09:05')).toBe('9:05 am');
    expect(monthsUntil(TODAY, '2027-03-31')).toBe(6);
  });
});

describe('filters', () => {
  it('quick filter Splits shows only the Beach villa', () => {
    const r = applyFilters(seed.transactions, { ...defaultFilters, quick: 'Splits' }, TODAY);
    expect(r.map((t) => t.title)).toEqual(['Beach villa']);
  });
  it('Food + Transport, ₹100 to ₹5,000, expenses only', () => {
    const r = applyFilters(
      seed.transactions,
      {
        ...defaultFilters,
        types: ['expense'],
        categoryIds: ['food', 'transport'],
        min: '₹100',
        max: '₹5,000',
      },
      TODAY,
    );
    expect(r.every((t) => t.amount >= 100 && t.amount <= 5000)).toBe(true);
    expect(r.length).toBe(18); // 12 food (≥ ₹100) + 6 transport
  });
  it('Last month is empty (no August transactions in the seed)', () => {
    expect(applyFilters(seed.transactions, { ...defaultFilters, range: 'Last month' }, TODAY)).toHaveLength(
      0,
    );
  });
});
