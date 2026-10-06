// Pure selectors over transactions and accounts. Every total shown in the UI comes from here.
import type { Account, Category, ChartToken, ID, MonthKey, Rupees, Transaction } from '@/types/domain';
import { monthOf } from './dates';
import { percent } from './format';

export function activeAccounts(accounts: readonly Account[]): Account[] {
  return accounts.filter((a) => !a.archived);
}

export function netBalance(accounts: readonly Account[]): { total: Rupees; count: number } {
  const counted = accounts.filter((a) => a.includeInTotal && !a.archived);
  return { total: counted.reduce((s, a) => s + a.balance, 0), count: counted.length };
}

export function inMonth(txs: readonly Transaction[], month: MonthKey): Transaction[] {
  return txs.filter((t) => monthOf(t.date) === month);
}

export interface MonthTotals {
  income: Rupees;
  spent: Rupees;
  net: Rupees;
  savingsRate: number;
}

/**
 * Spending = expense transactions only. Transfers move money between your own accounts, and
 * your share of a group expense counts once you settle (spec §6 invariants).
 */
export function monthTotals(txs: readonly Transaction[], month: MonthKey): MonthTotals {
  let income = 0;
  let spent = 0;
  for (const t of inMonth(txs, month)) {
    if (t.type === 'income') income += t.amount;
    else if (t.type === 'expense') spent += t.amount;
  }
  const net = income - spent;
  return { income, spent, net, savingsRate: percent(net, income) };
}

export function categoryTotals(txs: readonly Transaction[], month: MonthKey): Record<ID, Rupees> {
  const out: Record<ID, Rupees> = {};
  for (const t of inMonth(txs, month)) {
    if (t.type !== 'expense' || !t.categoryId) continue;
    out[t.categoryId] = (out[t.categoryId] ?? 0) + t.amount;
  }
  return out;
}

export function categoryCounts(txs: readonly Transaction[], month: MonthKey): Record<ID, number> {
  const out: Record<ID, number> = {};
  for (const t of inMonth(txs, month)) {
    if (!t.categoryId) continue;
    out[t.categoryId] = (out[t.categoryId] ?? 0) + 1;
  }
  return out;
}

export interface BreakdownSlice {
  id: ID;
  label: string;
  amount: Rupees;
  /** Share of total spending, 0–100 with one decimal. */
  share: number;
  token: ChartToken;
}

/** Home "Where it went": the charted categories by size, then everything else as Other. */
export function spendingBreakdown(
  txs: readonly Transaction[],
  month: MonthKey,
  categories: readonly Category[],
): { total: Rupees; slices: BreakdownSlice[] } {
  const totals = categoryTotals(txs, month);
  const total = Object.values(totals).reduce((s, v) => s + v, 0);
  const charted: BreakdownSlice[] = [];
  let other = 0;
  for (const [id, amount] of Object.entries(totals)) {
    const cat = categories.find((c) => c.id === id);
    if (cat?.chartToken) {
      charted.push({ id, label: cat.short, amount, share: 0, token: cat.chartToken });
    } else {
      other += amount;
    }
  }
  charted.sort((a, b) => b.amount - a.amount);
  if (other > 0) charted.push({ id: 'other', label: 'Other', amount: other, share: 0, token: 'chart5' });
  const share = (v: number) => (total === 0 ? 0 : Math.round((v / total) * 1000) / 10);
  return { total, slices: charted.map((s) => ({ ...s, share: share(s.amount) })) };
}

export function merchantTotal(txs: readonly Transaction[], month: MonthKey, title: string): Rupees {
  return inMonth(txs, month)
    .filter((t) => t.type === 'expense' && t.title === title)
    .reduce((s, t) => s + t.amount, 0);
}

export interface AccountActivity {
  in: Rupees;
  out: Rupees;
  moved: Rupees;
}

/** Account details KPIs: money in, spending out, and transfers moved out this month. */
export function accountActivity(
  txs: readonly Transaction[],
  accountId: ID,
  month: MonthKey,
): AccountActivity {
  const res: AccountActivity = { in: 0, out: 0, moved: 0 };
  for (const t of inMonth(txs, month)) {
    if (t.type === 'income' && t.accountId === accountId) res.in += t.amount;
    if (t.type === 'transfer' && t.toAccountId === accountId) res.in += t.amount;
    if (t.type === 'expense' && t.accountId === accountId) res.out += t.amount;
    if (t.type === 'transfer' && t.accountId === accountId) res.moved += t.amount;
  }
  return res;
}

export function sortNewestFirst(txs: readonly Transaction[]): Transaction[] {
  return [...txs].sort((a, b) =>
    a.date === b.date ? (b.time ?? '').localeCompare(a.time ?? '') : b.date.localeCompare(a.date),
  );
}

export function groupByDay(txs: readonly Transaction[]): { date: string; items: Transaction[] }[] {
  const out: { date: string; items: Transaction[] }[] = [];
  for (const t of sortNewestFirst(txs)) {
    const last = out.at(-1);
    if (last && last.date === t.date) last.items.push(t);
    else out.push({ date: t.date, items: [t] });
  }
  return out;
}

/** Effect of a transaction on account balances, used by mutations and undo. */
export function balanceEffects(
  t: Pick<Transaction, 'type' | 'amount' | 'accountId' | 'toAccountId'>,
): Record<ID, Rupees> {
  const fx: Record<ID, Rupees> = {};
  const add = (id: ID | undefined, v: number) => {
    if (id) fx[id] = (fx[id] ?? 0) + v;
  };
  switch (t.type) {
    case 'expense':
    case 'split':
      add(t.accountId, -t.amount);
      break;
    case 'income':
      add(t.accountId, t.amount);
      break;
    case 'transfer':
      add(t.accountId, -t.amount);
      add(t.toAccountId, t.amount);
      break;
  }
  return fx;
}

export function applyEffects(
  accounts: readonly Account[],
  fx: Record<ID, Rupees>,
  direction: 1 | -1 = 1,
): Account[] {
  return accounts.map((a) => (fx[a.id] ? { ...a, balance: a.balance + direction * (fx[a.id] ?? 0) } : a));
}

/**
 * Ids of the named expense categories, in the order given. The app's standard categories are found
 * by name because their ids differ between the demo ('food') and the server (a UUID).
 */
export function expenseCategoryIds(categories: readonly Category[], names: readonly string[]): ID[] {
  return names
    .map((name) => categories.find((c) => c.kind === 'expense' && c.short === name)?.id)
    .filter((id): id is ID => !!id);
}
