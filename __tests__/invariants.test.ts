// Financial invariants from the implementation spec (§6). If any of these fail, a screen
// would show a number that disagrees with the approved canvas.
import * as seed from '@/mock/seed';
import { TODAY } from '@/mock/clock';
import { budgetStatus, suggestBudget, threeMonthAverage } from '@/utils/budget';
import { goalProgress, goalsTotals } from '@/utils/goals';
import { netWorth } from '@/utils/netWorth';
import { outgoingInMonth, subscriptions, upcomingSplit } from '@/utils/recurring';
import { compareWithPrevious, topExpenses } from '@/utils/reports';
import { groupPosition, overallPosition } from '@/utils/splits';
import {
  accountActivity,
  categoryCounts,
  categoryTotals,
  merchantTotal,
  monthTotals,
  netBalance,
  spendingBreakdown,
} from '@/utils/summary';

const SEP = '2026-09';

describe('balances and monthly totals', () => {
  it('net balance is ₹1,24,580 across 5 accounts', () => {
    const nb = netBalance(seed.accounts);
    expect(nb.total).toBe(124580);
    expect(nb.count).toBe(5);
  });

  it('September: spent ₹18,640, income ₹43,000, net +₹24,360, savings rate 57%', () => {
    const t = monthTotals(seed.transactions, SEP);
    expect(t.spent).toBe(18640);
    expect(t.income).toBe(43000);
    expect(t.net).toBe(24360);
    expect(t.savingsRate).toBe(57);
  });

  it('category totals match the canvas', () => {
    const c = categoryTotals(seed.transactions, SEP);
    expect(c.bills).toBe(8000);
    expect(c.food).toBe(4200);
    expect(c.transport).toBe(2800);
    expect(c.shopping).toBe(2100);
    expect((c.health ?? 0) + (c.fun ?? 0)).toBe(1540);
    expect(c.health).toBe(1040);
    expect(c.fun).toBe(500);
  });

  it('category counts match the Categories screen', () => {
    const n = categoryCounts(seed.transactions, SEP);
    expect(n.food).toBe(14);
    expect(n.transport).toBe(6);
    expect(n.shopping).toBe(3);
    expect(n.bills).toBe(10);
    expect(n.health).toBe(2);
    expect(n.fun).toBe(3);
    expect(n.home ?? 0).toBe(0);
  });

  it('Home breakdown orders Bills, Food, Transport, Shopping, Other', () => {
    const b = spendingBreakdown(seed.transactions, SEP, seed.categories);
    expect(b.slices.map((s) => s.label)).toEqual(['Bills', 'Food', 'Transport', 'Shopping', 'Other']);
    expect(b.slices[0]?.share).toBeCloseTo(42.9, 1);
  });

  it('Swiggy is ₹1,370 of food, 33%', () => {
    const s = merchantTotal(seed.transactions, SEP, 'Swiggy');
    expect(s).toBe(1370);
    expect(Math.round((s / 4200) * 100)).toBe(33);
  });

  it('HDFC Bank: in ₹35,000, out ₹8,761, moved ₹5,000', () => {
    const a = accountActivity(seed.transactions, 'hdfc', SEP);
    expect(a.in).toBe(35000);
    expect(a.out).toBe(8761);
    expect(a.moved).toBe(5000);
  });
});

describe('budget', () => {
  const status = budgetStatus(seed.budgets[0], seed.transactions, SEP, TODAY);

  it('₹17,100 of ₹24,000, ₹6,900 left', () => {
    expect(status?.spent).toBe(17100);
    expect(status?.limit).toBe(24000);
    expect(status?.left).toBe(6900);
    expect(status?.pct).toBe(71);
  });

  it('Transport is at 93% and in warning', () => {
    const t = status?.categories.find((c) => c.categoryId === 'transport');
    expect(t?.pct).toBe(93);
    expect(t?.left).toBe(200);
    expect(t?.tone).toBe('warn');
  });

  it('Transport 3-month average is ₹2,850', () => {
    expect(threeMonthAverage(seed.history, seed.transactions, 'transport', SEP)).toBe(2850);
  });

  it('suggests ₹22,000 when there is no budget', () => {
    const s = suggestBudget(seed.history, seed.transactions, ['bills', 'food', 'transport', 'shopping'], SEP);
    expect(s.total).toBe(22000);
    expect(Object.values(s.split).reduce((a, b) => a + b, 0)).toBe(22000);
  });
});

describe('splits', () => {
  it('overall: owed ₹5,700, owe ₹1,000, net ₹4,700', () => {
    const p = overallPosition(seed.groupExpenses, seed.settlements, 'me');
    expect(p.owed).toBe(5700);
    expect(p.owe).toBe(1000);
    expect(p.net).toBe(4700);
    expect(p.byPerson.aman).toBe(2500);
    expect(p.byPerson.rahul).toBe(3200);
    expect(p.byPerson.karan).toBe(-1000);
  });

  it('Goa Trip: you get back ₹7,800 (Aman 2,400, Rahul 3,000, Karan 2,400)', () => {
    const g = groupPosition(seed.groupExpenses, 'goa', 'me');
    expect(g.net).toBe(7800);
    expect(g.byPerson.aman).toBe(2400);
    expect(g.byPerson.rahul).toBe(3000);
    expect(g.byPerson.karan).toBe(2400);
  });

  it('Flat 402: you owe ₹3,100', () => {
    expect(groupPosition(seed.groupExpenses, 'flat', 'me').net).toBe(-3100);
  });

  it('settling ₹1,000 with Karan leaves owed ₹5,700 and owe ₹0', () => {
    const p = overallPosition(
      seed.groupExpenses,
      [{ id: 's', fromId: 'me', toId: 'karan', amount: 1000, method: 'upi', date: TODAY }],
      'me',
    );
    expect(p.owed).toBe(5700);
    expect(p.owe).toBe(0);
  });
});

describe('goals', () => {
  it('₹98,000 saved, ₹2,52,000 to go', () => {
    const t = goalsTotals(seed.goals);
    expect(t.saved).toBe(98000);
    expect(t.left).toBe(252000);
  });

  it('MacBook: 38%, ₹12,500 a month, pill shows the monthly amount', () => {
    const g = goalProgress(seed.goals[0]!, TODAY);
    expect(g.pct).toBe(38);
    expect(g.monthly).toBe(12500);
    expect(g.pill).toBe('₹12,500/mo');
  });

  it('Emergency Fund is behind; Kerala Trip is on track at 60%', () => {
    expect(goalProgress(seed.goals[1]!, TODAY).pill).toBe('Behind');
    const k = goalProgress(seed.goals[2]!, TODAY);
    expect(k.pct).toBe(60);
    expect(k.pill).toBe('On track');
  });

  it('adding ₹12,500 to MacBook gives 48% and ₹10,417 a month', () => {
    const g = seed.goals[0]!;
    const after = goalProgress(
      {
        ...g,
        contributions: [...g.contributions, { id: 'x', amount: 12500, accountId: 'hdfc', date: TODAY }],
      },
      TODAY,
    );
    expect(after.pct).toBe(48);
    expect(after.monthly).toBe(10417);
  });
});

describe('recurring and subscriptions', () => {
  it('October outgoing ₹14,391 across 9 payments; next 7 days ₹8,499', () => {
    const o = outgoingInMonth(seed.recurring, '2026-10');
    expect(o.total).toBe(14391);
    expect(o.count).toBe(9);
    const u = upcomingSplit(seed.recurring, TODAY, '2026-10');
    expect(u.soonTotal).toBe(8499);
    expect(u.later.map((r) => r.name)).toEqual(['ChatGPT Plus', 'Bike loan EMI']);
  });

  it('subscriptions ₹2,692 a month, ₹32,304 a year', () => {
    const s = subscriptions(seed.recurring);
    expect(s.monthly).toBe(2692);
    expect(s.yearly).toBe(32304);
    expect(s.count).toBe(5);
  });
});

describe('reports and net worth', () => {
  it('net worth ₹2,18,680 = ₹2,62,080 − ₹43,400', () => {
    const nw = netWorth(seed.accounts, seed.assets, seed.liabilities);
    expect(nw.totalAssets).toBe(262080);
    expect(nw.totalLiabilities).toBe(43400);
    expect(nw.net).toBe(218680);
    expect(nw.net - (seed.history.at(-1)?.netWorth ?? 0)).toBe(14200);
  });

  it('compared with August: −12%, food −18%, transport −10%, shopping +42%', () => {
    const c = compareWithPrevious(seed.history, seed.transactions, SEP, [
      { id: 'total', label: 'Total spending' },
      { id: 'food', label: 'Food' },
      { id: 'transport', label: 'Transport' },
      { id: 'shopping', label: 'Shopping' },
    ]);
    expect(c.map((x) => x.change)).toEqual([-12, -18, -10, 42]);
  });

  it('top expenses: ChatGPT Plus, Gym, Amazon, Electricity', () => {
    expect(topExpenses(seed.transactions, SEP).map((t) => t.title)).toEqual([
      'ChatGPT Plus',
      'Gym membership',
      'Amazon',
      'Electricity',
    ]);
  });
});
