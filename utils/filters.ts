// Transaction filtering for Activity, Search and the Filters sheet.
import type { ID, Transaction, TxType } from '@/types/domain';
import { monthOf, shiftMonth } from './dates';

export type QuickFilter = 'All' | 'Expenses' | 'Income' | 'Transfers' | 'Splits';
export type DateRange = 'This month' | 'Last month' | '3 months' | 'Custom';

export interface TxFilters {
  quick: QuickFilter;
  range: DateRange;
  types: TxType[];
  categoryIds: ID[];
  accountIds: ID[];
  min: string;
  max: string;
}

export const defaultFilters: TxFilters = {
  quick: 'All',
  range: 'This month',
  types: [],
  categoryIds: [],
  accountIds: [],
  min: '',
  max: '',
};

const QUICK: Record<QuickFilter, TxType | null> = {
  All: null,
  Expenses: 'expense',
  Income: 'income',
  Transfers: 'transfer',
  Splits: 'split',
};

/** Applies the sheet filters and the quick chip to a list (pure, used by Activity and Filters). */
export function applyFilters(txs: readonly Transaction[], f: TxFilters, today: string): Transaction[] {
  const month = monthOf(today);
  const months =
    f.range === 'This month'
      ? [month]
      : f.range === 'Last month'
        ? [shiftMonth(month, -1)]
        : f.range === '3 months'
          ? [month, shiftMonth(month, -1), shiftMonth(month, -2)]
          : null;
  const quick = QUICK[f.quick];
  const min = f.min ? Number(f.min.replace(/[^\d]/g, '')) : null;
  const max = f.max ? Number(f.max.replace(/[^\d]/g, '')) : null;
  return txs.filter((t) => {
    if (months && !months.includes(monthOf(t.date))) return false;
    if (quick && t.type !== quick) return false;
    if (f.types.length && !f.types.includes(t.type)) return false;
    if (f.categoryIds.length && !(t.categoryId && f.categoryIds.includes(t.categoryId))) return false;
    if (f.accountIds.length && !(t.accountId && f.accountIds.includes(t.accountId))) return false;
    if (min !== null && t.amount < min) return false;
    if (max !== null && t.amount > max) return false;
    return true;
  });
}
