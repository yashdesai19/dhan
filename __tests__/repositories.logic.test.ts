// Mutations must keep every derived number consistent (spec §13, step 4).
import { mockConfig } from '@/mock/config';
import { db } from '@/mock/db';
import { TODAY } from '@/mock/clock';
import {
  budgetRepo,
  goalsRepo,
  resetMockData,
  splitsRepo,
  transactionsRepo,
  authRepo,
  MOCK_PASSWORD,
} from '@/data/repositories';
import { budgetStatus } from '@/utils/budget';
import { goalProgress } from '@/utils/goals';
import { computeShares, overallPosition, sumShares } from '@/utils/splits';
import { categoryTotals, monthTotals, netBalance } from '@/utils/summary';

const SEP = '2026-09';
const bal = (id: string) => db.get().accounts.find((a) => a.id === id)?.balance;

beforeEach(() => {
  mockConfig.latency = [0, 0];
  mockConfig.failNext = false;
  resetMockData();
});

describe('add expense flow', () => {
  it('updates transactions, account balance, budget and Home totals', async () => {
    const t = await transactionsRepo.addExpense({ amount: 450, categoryId: 'food', accountId: 'hdfc' });
    const s = db.get();
    expect(s.transactions[0]?.id).toBe(t.id);
    expect(bal('hdfc')).toBe(86000);
    expect(netBalance(s.accounts).total).toBe(124130);
    expect(monthTotals(s.transactions, SEP).spent).toBe(19090);
    expect(categoryTotals(s.transactions, SEP).food).toBe(4650);
    expect(budgetStatus(s.budgets[0], s.transactions, SEP, TODAY)?.left).toBe(6450);
  });

  it('rejects ₹0', async () => {
    let msg = '';
    await transactionsRepo
      .addExpense({ amount: 0, categoryId: 'food', accountId: 'hdfc' })
      .catch((e: Error) => {
        msg = e.message;
      });
    expect(msg).toBe('Enter an amount.');
  });
});

describe('income and transfer', () => {
  it('income adds to the account and to monthly income', async () => {
    await transactionsRepo.addIncome({ amount: 35000, categoryId: 'salary', accountId: 'hdfc' });
    expect(bal('hdfc')).toBe(121450);
    expect(monthTotals(db.get().transactions, SEP).income).toBe(78000);
  });

  it('transfer moves money without changing the total or spending', async () => {
    await transactionsRepo.addTransfer({ amount: 5000, fromId: 'hdfc', toId: 'cash' });
    expect(bal('hdfc')).toBe(81450);
    expect(bal('cash')).toBe(8200);
    expect(netBalance(db.get().accounts).total).toBe(124580);
    expect(monthTotals(db.get().transactions, SEP).spent).toBe(18640);
  });
});

describe('delete and undo', () => {
  it('delete restores the balance; undo puts everything back', async () => {
    const swiggy = db.get().transactions.find((t) => t.title === 'Swiggy' && t.amount === 450)!;
    const removed = await transactionsRepo.remove(swiggy.id);
    expect(bal('hdfc')).toBe(86900);
    expect(categoryTotals(db.get().transactions, SEP).food).toBe(3750);
    await transactionsRepo.restore(removed);
    expect(bal('hdfc')).toBe(86450);
    expect(categoryTotals(db.get().transactions, SEP).food).toBe(4200);
  });

  it('edit moves the amount between accounts correctly', async () => {
    const swiggy = db.get().transactions.find((t) => t.title === 'Swiggy' && t.amount === 450)!;
    await transactionsRepo.update(swiggy.id, { amount: 500, accountId: 'paytm' });
    expect(bal('hdfc')).toBe(86900);
    expect(bal('paytm')).toBe(1130);
  });
});

describe('budget edits', () => {
  it('raising Transport to ₹3,500 changes the monthly total', async () => {
    await budgetRepo.setCategory(SEP, {
      categoryId: 'transport',
      limit: 3500,
      rollover: false,
      warnAtPercent: 90,
    });
    const st = budgetStatus(
      db.get().budgets.find((b) => b.month === SEP),
      db.get().transactions,
      SEP,
      TODAY,
    );
    expect(st?.limit).toBe(24500);
    expect(st?.categories.find((c) => c.categoryId === 'transport')?.tone).toBe('ok');
  });
});

describe('splits', () => {
  it('equal split of ₹12,000 among 3 people is ₹4,000 each', () => {
    const s = computeShares('equal', {
      amount: 12000,
      memberIds: ['me', 'aman', 'rahul', 'karan'],
      included: { me: true, aman: true, rahul: true, karan: false },
    });
    expect(s).toEqual({ me: 4000, aman: 4000, rahul: 4000, karan: 0 });
  });

  it('shares 2:1:1:1 give ₹4,800 and ₹2,400 each', () => {
    const s = computeShares('shares', {
      amount: 12000,
      memberIds: ['me', 'aman', 'rahul', 'karan'],
      shares: { me: 2, aman: 1, rahul: 1, karan: 1 },
    });
    expect(s).toEqual({ me: 4800, aman: 2400, rahul: 2400, karan: 2400 });
  });

  it('percent and item-wise always add up to the total', () => {
    const ids = ['me', 'aman', 'rahul', 'karan'];
    expect(
      sumShares(
        computeShares('percent', {
          amount: 12000,
          memberIds: ids,
          percent: { me: 25, aman: 25, rahul: 25, karan: 25 },
        }),
      ),
    ).toBe(12000);
    const iw = computeShares('itemwise', {
      amount: 12000,
      memberIds: ids,
      items: [
        { id: 'a', title: 'Villa rent', amount: 10000, memberIds: ids },
        { id: 'b', title: 'Late checkout fee', amount: 2000, memberIds: ['me', 'aman'] },
      ],
    });
    expect(iw).toEqual({ me: 3500, aman: 3500, rahul: 2500, karan: 2500 });
  });

  it('settling with Karan clears what you owe', async () => {
    await splitsRepo.settle({ withId: 'karan', amount: 1000, method: 'upi', direction: 'pay' });
    const p = overallPosition(db.get().groupExpenses, db.get().settlements, 'me');
    expect(p.owe).toBe(0);
    expect(p.owed).toBe(5700);
  });

  it('a split you paid creates a transaction that is not spending', async () => {
    await splitsRepo.addExpense({
      groupId: 'goa',
      title: 'Parasailing',
      amount: 4000,
      paidBy: 'me',
      method: 'equal',
      shares: { me: 1000, aman: 1000, rahul: 1000, karan: 1000 },
    });
    expect(monthTotals(db.get().transactions, SEP).spent).toBe(18640);
    expect(overallPosition(db.get().groupExpenses, db.get().settlements, 'me').net).toBe(7700);
  });
});

describe('goals', () => {
  it('adding ₹12,500 to MacBook moves it to 48%', async () => {
    await goalsRepo.addContribution('macbook', 12500, 'hdfc');
    const g = db.get().goals.find((x) => x.id === 'macbook')!;
    expect(goalProgress(g, TODAY).pct).toBe(48);
  });
});

describe('mock auth', () => {
  it('accepts the demo password and counts failed attempts', async () => {
    let left = '';
    await authRepo.signIn('yash@example.com', 'wrong').catch((e: Error) => {
      left = e.message;
    });
    expect(left).toBe('2');
    const ok = await authRepo.signIn('yash@example.com', MOCK_PASSWORD);
    expect(ok.email).toBe('yash@example.com');
  });
});
