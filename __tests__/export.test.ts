import type { Account, Category, Transaction } from '@/types/domain';
import { profitAndLoss } from '@/utils/books';
import { exportRows, statementHtml, toCsv } from '@/utils/export';

const account = (id: string): Account => ({
  id,
  name: id.toUpperCase(),
  type: 'bank',
  subtitle: '',
  balance: 0,
  includeInTotal: true,
  archived: false,
});
const tx = (id: string, p: Partial<Transaction>): Transaction => ({
  id,
  type: 'expense',
  title: id,
  amount: 100,
  date: '2026-09-10',
  accountId: 'shop',
  repeats: 'never',
  ...p,
});
const categories: Category[] = [{ id: 'sales', name: 'Sales', short: 'Sales', icon: 'tag', kind: 'income' }];
const shop = [account('shop')];

describe('exportRows', () => {
  it('signs money in and out from the exported accounts’ side', () => {
    const rows = exportRows(
      [
        tx('stock', { amount: 300, date: '2026-09-12' }),
        tx('sale', { type: 'income', amount: 900, categoryId: 'sales', date: '2026-09-11' }),
        tx('drawings', { type: 'transfer', toAccountId: 'home', amount: 200 }),
        tx('august', { date: '2026-08-30' }),
      ],
      '2026-09',
      shop,
      categories,
    );
    expect(rows.map((r) => [r.title, r.amount])).toEqual([
      ['stock', -300],
      ['sale', 900],
      ['drawings', -200],
    ]);
    expect(rows[1]!.category).toBe('Sales');
    expect(rows[2]!.account).toBe('SHOP → Other book');
  });

  it('leaves a transfer between two exported accounts unsigned', () => {
    const rows = exportRows(
      [tx('move', { type: 'transfer', toAccountId: 'cash' })],
      '2026-09',
      [account('shop'), account('cash')],
      [],
    );
    expect(rows[0]!.amount).toBe(100);
  });
});

describe('toCsv', () => {
  const rows = exportRows([tx('Chai, "special"', { note: '=HYPERLINK("x")' })], '2026-09', shop, []);
  const csv = toCsv(rows);

  it('starts with a byte-order mark and a header', () => {
    expect(csv.startsWith('﻿Date,Type,Title,Category,Account,Amount (INR),Note\r\n')).toBe(true);
  });

  it('quotes commas and quotes, and defuses formulas', () => {
    expect(csv).toContain('"Chai, ""special"""');
    expect(csv).toContain(`"'=HYPERLINK(""x"")"`);
    expect(csv).toContain(',-100,');
  });
});

it('statementHtml escapes names and shows profit', () => {
  const t = [tx('sale', { type: 'income', amount: 900, categoryId: 'sales' })];
  const html = statementHtml({
    bookName: '<Sharma & Sons>',
    month: '2026-09',
    business: true,
    pl: profitAndLoss(t, '2026-09', categories),
    rows: exportRows(t, '2026-09', shop, categories),
  });
  expect(html).toContain('&lt;Sharma &amp; Sons&gt;');
  expect(html).not.toContain('<Sharma');
  expect(html).toContain('Net profit');
});
