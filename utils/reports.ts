// Report selectors: 6-month series, month-on-month comparison, top expenses.
import type { MonthHistory, MonthKey, Rupees, Transaction } from '@/types/domain';
import { monthName, shiftMonth } from './dates';
import { categoryTotals, inMonth, monthTotals } from './summary';

export interface MonthPoint {
  month: MonthKey;
  label: string;
  income: Rupees;
  spent: Rupees;
}

export function sixMonthSeries(
  history: readonly MonthHistory[],
  txs: readonly Transaction[],
  month: MonthKey,
): MonthPoint[] {
  return [-5, -4, -3, -2, -1, 0].map((d) => {
    const m = shiftMonth(month, d);
    if (d === 0) {
      const t = monthTotals(txs, m);
      return { month: m, label: monthName(m), income: t.income, spent: t.spent };
    }
    const h = history.find((x) => x.month === m);
    return { month: m, label: monthName(m), income: h?.income ?? 0, spent: h?.spent ?? 0 };
  });
}

export interface Comparison {
  id: string;
  label: string;
  previous: Rupees;
  current: Rupees;
  /** Rounded % change. */
  change: number;
}

export function compareWithPrevious(
  history: readonly MonthHistory[],
  txs: readonly Transaction[],
  month: MonthKey,
  rows: readonly { id: string; label: string }[],
): Comparison[] {
  const prevMonth = shiftMonth(month, -1);
  const prev = history.find((h) => h.month === prevMonth);
  const cur = categoryTotals(txs, month);
  const curTotal = monthTotals(txs, month).spent;
  return rows.map((r) => {
    const previous = r.id === 'total' ? (prev?.spent ?? 0) : (prev?.byCategory[r.id] ?? 0);
    const current = r.id === 'total' ? curTotal : (cur[r.id] ?? 0);
    const change = previous === 0 ? 0 : Math.round(((current - previous) / previous) * 100);
    return { id: r.id, label: r.label, previous, current, change };
  });
}

export function topExpenses(txs: readonly Transaction[], month: MonthKey, n = 4): Transaction[] {
  return inMonth(txs, month)
    .filter((t) => t.type === 'expense')
    .sort((a, b) => b.amount - a.amount)
    .slice(0, n);
}
