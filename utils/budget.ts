// Budget maths (spec §6 invariants: ₹17,100 of ₹24,000, ₹6,900 left).
import type { Budget, ID, MonthHistory, MonthKey, Rupees, Transaction } from '@/types/domain';
import { daysInMonth, monthOf, parts, shiftMonth } from './dates';
import { percent } from './format';
import { categoryTotals } from './summary';

export type BudgetTone = 'ok' | 'warn' | 'over';

export interface CategoryBudgetStatus {
  categoryId: ID;
  limit: Rupees;
  spent: Rupees;
  left: Rupees;
  pct: number;
  tone: BudgetTone;
}

export interface BudgetStatus {
  month: MonthKey;
  limit: Rupees;
  spent: Rupees;
  left: Rupees;
  pct: number;
  /** Days left in the month, counting today. */
  daysLeft: number;
  perDay: Rupees;
  categories: CategoryBudgetStatus[];
}

export function toneFor(pct: number, warnAt: number): BudgetTone {
  if (pct > 100) return 'over';
  if (pct >= warnAt) return 'warn';
  return 'ok';
}

export function daysLeftInMonth(month: MonthKey, today: string): number {
  if (monthOf(today) !== month) return monthOf(today) < month ? daysInMonth(month) : 0;
  return daysInMonth(month) - parts(today).d + 1;
}

export function budgetStatus(
  budget: Budget | undefined,
  txs: readonly Transaction[],
  month: MonthKey,
  today: string,
): BudgetStatus | null {
  if (!budget || budget.categories.length === 0) return null;
  const totals = categoryTotals(txs, month);
  const categories = budget.categories.map<CategoryBudgetStatus>((c) => {
    const spent = totals[c.categoryId] ?? 0;
    const pct = percent(spent, c.limit);
    return {
      categoryId: c.categoryId,
      limit: c.limit,
      spent,
      left: c.limit - spent,
      pct,
      tone: toneFor(pct, c.warnAtPercent),
    };
  });
  const limit = categories.reduce((s, c) => s + c.limit, 0);
  const spent = categories.reduce((s, c) => s + c.spent, 0);
  const left = limit - spent;
  const daysLeft = daysLeftInMonth(month, today);
  return {
    month,
    limit,
    spent,
    left,
    pct: percent(spent, limit),
    daysLeft,
    perDay: daysLeft > 0 ? Math.round(Math.max(0, left) / daysLeft) : 0,
    categories,
  };
}

/** Spending projected to month end at the current daily pace. */
export function projectedSpend(spent: Rupees, month: MonthKey, today: string): Rupees {
  if (monthOf(today) !== month) return spent;
  const day = parts(today).d;
  return Math.round((spent / day) * daysInMonth(month));
}

/** Spend for a category over [month-2, month-1, month], closed months from history. */
export function categoryHistory(
  history: readonly MonthHistory[],
  txs: readonly Transaction[],
  categoryId: ID,
  month: MonthKey,
): { month: MonthKey; spent: Rupees }[] {
  return [-2, -1, 0].map((delta) => {
    const m = shiftMonth(month, delta);
    const spent =
      delta === 0
        ? (categoryTotals(txs, m)[categoryId] ?? 0)
        : (history.find((h) => h.month === m)?.byCategory[categoryId] ?? 0);
    return { month: m, spent };
  });
}

export function threeMonthAverage(
  history: readonly MonthHistory[],
  txs: readonly Transaction[],
  categoryId: ID,
  month: MonthKey,
): Rupees {
  const rows = categoryHistory(history, txs, categoryId, month);
  return Math.round(rows.reduce((s, r) => s + r.spent, 0) / rows.length);
}

/**
 * Budget suggestion (Budget empty state): 3-month average of the budgeted categories plus
 * 10% breathing room, rounded to the nearest ₹1,000, split by each category's average.
 */
export function suggestBudget(
  history: readonly MonthHistory[],
  txs: readonly Transaction[],
  categoryIds: readonly ID[],
  month: MonthKey,
): { total: Rupees; split: Record<ID, Rupees> } {
  const avgs = categoryIds.map((id) => ({ id, avg: threeMonthAverage(history, txs, id, month) }));
  const base = avgs.reduce((s, a) => s + a.avg, 0);
  const total = Math.round((base * 1.1) / 1000) * 1000;
  const split: Record<ID, Rupees> = {};
  let assigned = 0;
  avgs.forEach((a, i) => {
    const v =
      i === avgs.length - 1 ? total - assigned : Math.round((total * (a.avg / (base || 1))) / 100) * 100;
    split[a.id] = v;
    assigned += v;
  });
  return { total, split };
}
