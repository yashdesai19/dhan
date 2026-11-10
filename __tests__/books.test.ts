import type { Account, Category, Transaction } from '@/types/domain';
import {
  ALL_BOOKS_ID,
  PERSONAL_BOOK_ID,
  bookHistory,
  businessChips,
  profitAndLoss,
  scopeToBook,
} from '@/utils/books';
import { monthTotals } from '@/utils/summary';

const account = (id: string, bookId?: string): Account => ({
  id,
  name: id,
  type: 'bank',
  subtitle: '',
  balance: 0,
  includeInTotal: true,
  archived: false,
  bookId,
});
const tx = (id: string, p: Partial<Transaction>): Transaction => ({
  id,
  type: 'expense',
  title: id,
  amount: 100,
  date: '2026-09-10',
  repeats: 'never',
  ...p,
});
const category = (id: string, name: string, kind: 'expense' | 'income'): Category => ({
  id,
  name,
  short: name,
  icon: 'tag',
  kind,
});

const accounts = [account('home'), account('shop', 'b1')];
const transactions = [
  tx('groceries', { accountId: 'home', amount: 500 }),
  tx('stock', { accountId: 'shop', amount: 3000, categoryId: 'stock' }),
  tx('sale', { accountId: 'shop', type: 'income', amount: 10000, categoryId: 'sales' }),
  tx('drawings', { accountId: 'shop', toAccountId: 'home', type: 'transfer', amount: 2000 }),
];
const ids = (xs: { id: string }[]) => xs.map((x) => x.id);

describe('scopeToBook', () => {
  it('treats an account with no book as Personal', () => {
    expect(ids(scopeToBook(accounts, transactions, PERSONAL_BOOK_ID).accounts)).toEqual(['home']);
  });

  it('keeps a book to its own entries and shows a cross-book transfer in both', () => {
    expect(ids(scopeToBook(accounts, transactions, 'b1').transactions)).toEqual([
      'stock',
      'sale',
      'drawings',
    ]);
    expect(ids(scopeToBook(accounts, transactions, PERSONAL_BOOK_ID).transactions)).toEqual([
      'groceries',
      'drawings',
    ]);
  });

  it('returns everything for All', () => {
    expect(scopeToBook(accounts, transactions, ALL_BOOKS_ID).transactions).toHaveLength(4);
  });

  it('never counts taking money out of a business as income or spending', () => {
    const business = monthTotals(scopeToBook(accounts, transactions, 'b1').transactions, '2026-09');
    const personal = monthTotals(
      scopeToBook(accounts, transactions, PERSONAL_BOOK_ID).transactions,
      '2026-09',
    );
    expect(business).toMatchObject({ income: 10000, spent: 3000 });
    expect(personal).toMatchObject({ income: 0, spent: 500 });
  });
});

describe('profitAndLoss', () => {
  const categories = [category('stock', 'Stock', 'expense'), category('sales', 'Sales', 'income')];

  it('adds up by category and works out profit and margin', () => {
    const pl = profitAndLoss(scopeToBook(accounts, transactions, 'b1').transactions, '2026-09', categories);
    expect(pl.income).toEqual([{ id: 'sales', label: 'Sales', amount: 10000 }]);
    expect(pl.expenses).toEqual([{ id: 'stock', label: 'Stock', amount: 3000 }]);
    expect(pl).toMatchObject({ profit: 7000, margin: 70 });
  });

  it('has a zero margin with no income', () => {
    expect(profitAndLoss([tx('x', {})], '2026-09', []).margin).toBe(0);
  });
});

it('bookHistory lists the closed months before the current one, oldest first', () => {
  const h = bookHistory(transactions, '2026-10', 2);
  expect(h.map((m) => m.month)).toEqual(['2026-08', '2026-09']);
  expect(h[1]).toMatchObject({ income: 10000, spent: 3500 });
});

it('businessChips only lists categories that exist', () => {
  const chips = businessChips([category('s', 'Sales', 'income'), category('r', 'Shop rent', 'expense')]);
  expect(chips).toEqual({ expense: ['r'], income: ['s'] });
});
