// What goes into an exported file: a CSV for Excel and an HTML page printed to PDF. Pure functions.
import type { Account, Category, MonthKey, Transaction } from '@/types/domain';
import type { ProfitAndLoss } from './books';
import { monthYear } from './dates';
import { inr } from './format';
import { inMonth, sortNewestFirst } from './summary';

export interface ExportRow {
  date: string;
  type: string;
  title: string;
  category: string;
  account: string;
  /** Money in is positive, money out negative; a transfer inside the exported accounts is unsigned. */
  amount: number;
  note: string;
}

const TYPE_LABEL: Record<Transaction['type'], string> = {
  expense: 'Expense',
  income: 'Income',
  transfer: 'Transfer',
  split: 'Split',
};

/** The month's entries for the given accounts, newest first, signed from those accounts' side. */
export function exportRows(
  transactions: readonly Transaction[],
  month: MonthKey,
  accounts: readonly Account[],
  categories: readonly Category[],
): ExportRow[] {
  const name = new Map(accounts.map((a) => [a.id, a.name]));
  return sortNewestFirst(inMonth(transactions, month)).map((t) => {
    let amount = t.amount;
    if (t.type === 'expense' || t.type === 'split') amount = -t.amount;
    if (t.type === 'transfer') {
      const fromHere = !!t.accountId && name.has(t.accountId);
      const toHere = !!t.toAccountId && name.has(t.toAccountId);
      if (fromHere && !toHere) amount = -t.amount;
    }
    const account =
      t.type === 'transfer'
        ? [t.accountId, t.toAccountId].map((id) => (id ? (name.get(id) ?? 'Other book') : '')).join(' → ')
        : (name.get(t.accountId ?? '') ?? '');
    return {
      date: t.date,
      type: TYPE_LABEL[t.type],
      title: t.title,
      category: categories.find((c) => c.id === t.categoryId)?.name ?? '',
      account,
      amount,
      note: t.note ?? '',
    };
  });
}

/** Excel reads this as a spreadsheet: UTF-8 with a byte-order mark so ₹ and Hindi text survive. */
export function toCsv(rows: readonly ExportRow[]): string {
  const cell = (v: string | number) => {
    let s = String(v);
    // A cell starting like a formula would run as one in Excel
    if (typeof v === 'string' && /^[=+\-@\t\r]/.test(s)) s = `'${s}`;
    return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = ['Date', 'Type', 'Title', 'Category', 'Account', 'Amount (INR)', 'Note'];
  const lines = rows.map((r) =>
    [r.date, r.type, r.title, r.category, r.account, r.amount, r.note].map(cell).join(','),
  );
  return `﻿${[head.join(','), ...lines].join('\r\n')}\r\n`;
}

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

/** A printable statement: profit and loss (or income and spending), then every entry. */
export function statementHtml(opts: {
  bookName: string;
  month: MonthKey;
  business: boolean;
  pl: ProfitAndLoss;
  rows: readonly ExportRow[];
}): string {
  const { bookName, month, business, pl, rows } = opts;
  const line = (label: string, amount: number, cls = '') =>
    `<tr class="${cls}"><td>${esc(label)}</td><td class="num">${esc(inr(amount))}</td></tr>`;
  const result = pl.profit >= 0 ? (business ? 'Net profit' : 'Saved') : business ? 'Net loss' : 'Overspent';
  return `<!doctype html><html><head><meta charset="utf-8"><style>
body{font-family:-apple-system,Roboto,sans-serif;color:#1c1b1a;margin:32px;font-size:12px}
h1{font-size:20px;margin:0}h2{font-size:14px;margin:24px 0 8px}.muted{color:#6b6862}
table{width:100%;border-collapse:collapse}td,th{padding:6px 4px;border-bottom:1px solid #e6e3dd;text-align:left}
.num{text-align:right;font-variant-numeric:tabular-nums}.total td{font-weight:600;border-top:2px solid #1c1b1a}
</style></head><body>
<h1>${esc(bookName)}</h1><div class="muted">${esc(monthYear(month))} · DHAN</div>
<h2>${business ? 'Profit and loss' : 'Income and spending'}</h2><table>
${pl.income.map((l) => line(l.label, l.amount)).join('')}
${line(business ? 'Total sales' : 'Total income', pl.totalIncome, 'total')}
${pl.expenses.map((l) => line(l.label, l.amount)).join('')}
${line(business ? 'Total expenses' : 'Total spending', pl.totalExpenses, 'total')}
${line(result, Math.abs(pl.profit), 'total')}
</table>
<h2>Entries (${rows.length})</h2><table>
<tr><th>Date</th><th>Title</th><th>Category</th><th>Account</th><th class="num">Amount</th></tr>
${rows
  .map(
    (r) =>
      `<tr><td>${esc(r.date)}</td><td>${esc(r.title)}</td><td>${esc(r.category)}</td><td>${esc(r.account)}</td><td class="num">${esc(inr(r.amount, r.amount > 0 ? 'plus' : 'none'))}</td></tr>`,
  )
  .join('')}
</table></body></html>`;
}
