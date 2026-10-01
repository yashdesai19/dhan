// Mock repositories (spec §13, step 2). Screens never import this file directly — they use the
// hooks in data/queries. To connect FastAPI later, reimplement these functions with the same
// signatures; nothing above this layer changes.
import { db, type DbState } from '@/mock/db';
import { today } from '@/mock/clock';
import type {
  Account,
  Budget,
  CategoryBudget,
  GoalContribution,
  GroupExpense,
  ID,
  MonthKey,
  Rupees,
  Settlement,
  SettlementMethod,
  SplitMethod,
  Transaction,
  User,
} from '@/types/domain';
import { applyEffects, balanceEffects } from '@/utils/summary';
import { MockError, simulate } from './simulate';

export { MockError } from './simulate';

const read = <K extends keyof DbState>(key: K) => simulate(() => db.get()[key]);

// ---------------------------------------------------------------- reads

export const readRepo = {
  user: () => read('user'),
  accounts: () => read('accounts'),
  categories: () => read('categories'),
  transactions: () => read('transactions'),
  budgets: () => read('budgets'),
  people: () => read('people'),
  groups: () => read('groups'),
  groupExpenses: () => read('groupExpenses'),
  settlements: () => read('settlements'),
  goals: () => read('goals'),
  recurring: () => read('recurring'),
  assets: () => read('assets'),
  liabilities: () => read('liabilities'),
  history: () => simulate(() => db.get().history, { readsReports: true }),
  notifications: () => read('notifications'),
  aiResponses: () => read('aiResponses'),
  insights: () => read('insights'),
  devices: () => read('devices'),
  recentSearches: () => read('recentSearches'),
  chipOrder: () => read('chipOrder'),
};

// ---------------------------------------------------------------- transactions

export interface NewEntry {
  amount: Rupees;
  categoryId: ID;
  accountId: ID;
  date?: string;
  note?: string;
  title?: string;
}

function nowTime(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function insertTx(t: Transaction): Transaction {
  db.update((s) => ({
    ...s,
    transactions: [t, ...s.transactions],
    accounts: applyEffects(s.accounts, balanceEffects(t)),
  }));
  return t;
}

function removeTx(id: ID): Transaction {
  const t = db.get().transactions.find((x) => x.id === id);
  if (!t) throw new MockError('That transaction no longer exists.', 'not_found');
  db.update((s) => ({
    ...s,
    transactions: s.transactions.filter((x) => x.id !== id),
    accounts: applyEffects(s.accounts, balanceEffects(t), -1),
  }));
  return t;
}

export const transactionsRepo = {
  addExpense: (e: NewEntry) =>
    simulate(() => {
      if (!(e.amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      const cat = db.get().categories.find((c) => c.id === e.categoryId);
      return insertTx({
        id: db.id('t'),
        type: 'expense',
        title: e.title?.trim() || cat?.short || 'Expense',
        categoryId: e.categoryId,
        accountId: e.accountId,
        amount: Math.round(e.amount),
        date: e.date ?? today(),
        time: nowTime(),
        note: e.note,
        repeats: 'never',
      });
    }),

  addIncome: (e: NewEntry) =>
    simulate(() => {
      if (!(e.amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      const cat = db.get().categories.find((c) => c.id === e.categoryId);
      return insertTx({
        id: db.id('t'),
        type: 'income',
        title: e.title?.trim() || cat?.short || 'Income',
        categoryId: e.categoryId,
        accountId: e.accountId,
        amount: Math.round(e.amount),
        date: e.date ?? today(),
        time: nowTime(),
        note: e.note,
        repeats: 'never',
      });
    }),

  addTransfer: (t: { amount: Rupees; fromId: ID; toId: ID; date?: string; note?: string }) =>
    simulate(() => {
      if (!(t.amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      if (t.fromId === t.toId) throw new MockError('Pick two different accounts.', 'invalid');
      const s = db.get();
      const from = s.accounts.find((a) => a.id === t.fromId);
      const to = s.accounts.find((a) => a.id === t.toId);
      return insertTx({
        id: db.id('t'),
        type: 'transfer',
        title: `${from?.name ?? 'Account'} → ${to?.name ?? 'Account'}`,
        accountId: t.fromId,
        toAccountId: t.toId,
        amount: Math.round(t.amount),
        date: t.date ?? today(),
        time: nowTime(),
        note: t.note,
        repeats: 'never',
      });
    }),

  update: (id: ID, patch: Partial<Omit<Transaction, 'id' | 'type'>>) =>
    simulate(() => {
      const before = removeTx(id);
      return insertTx({ ...before, ...patch, id });
    }),

  remove: (id: ID) => simulate(() => removeTx(id)),

  /** Undo for delete and for a just-saved entry. */
  restore: (t: Transaction) => simulate(() => insertTx(t)),

  addRecentSearch: (q: string) =>
    simulate(() => {
      const term = q.trim();
      if (!term) return db.get().recentSearches;
      db.update((s) => ({
        ...s,
        recentSearches: [term, ...s.recentSearches.filter((x) => x !== term)].slice(0, 6),
      }));
      return db.get().recentSearches;
    }),
};

// ---------------------------------------------------------------- accounts

export type AccountInput = Omit<Account, 'id' | 'archived'> & { id?: ID };

export const accountsRepo = {
  upsert: (a: AccountInput) =>
    simulate(() => {
      if (!a.name.trim()) throw new MockError('Give the account a name.', 'invalid');
      const id = a.id ?? db.id('a');
      const next: Account = { ...a, id, name: a.name.trim(), archived: false };
      db.update((s) => ({
        ...s,
        accounts: s.accounts.some((x) => x.id === id)
          ? s.accounts.map((x) => (x.id === id ? next : x))
          : [...s.accounts, next],
      }));
      return next;
    }),
  archive: (id: ID) =>
    simulate(() => {
      db.update((s) => ({
        ...s,
        accounts: s.accounts.map((a) => (a.id === id ? { ...a, archived: true, includeInTotal: false } : a)),
      }));
      return id;
    }),
};

// ---------------------------------------------------------------- budget

function withBudget(month: MonthKey, fn: (b: Budget) => Budget) {
  db.update((s) => {
    const existing = s.budgets.find((b) => b.month === month) ?? { month, categories: [] };
    const next = fn(existing);
    return { ...s, budgets: [...s.budgets.filter((b) => b.month !== month), next] };
  });
}

export const budgetRepo = {
  setCategory: (month: MonthKey, c: CategoryBudget) =>
    simulate(() => {
      if (!(c.limit > 0)) throw new MockError('Set a limit above ₹0.', 'invalid');
      withBudget(month, (b) => ({
        ...b,
        categories: b.categories.some((x) => x.categoryId === c.categoryId)
          ? b.categories.map((x) => (x.categoryId === c.categoryId ? c : x))
          : [...b.categories, c],
      }));
      return c;
    }),
  removeCategory: (month: MonthKey, categoryId: ID) =>
    simulate(() => {
      withBudget(month, (b) => ({
        ...b,
        categories: b.categories.filter((x) => x.categoryId !== categoryId),
      }));
      return categoryId;
    }),
  replace: (month: MonthKey, categories: CategoryBudget[]) =>
    simulate(() => {
      withBudget(month, (b) => ({ ...b, categories }));
      return categories;
    }),
};

// ---------------------------------------------------------------- splits

export interface NewGroupExpense {
  groupId: ID;
  title: string;
  amount: Rupees;
  paidBy: ID;
  method: SplitMethod;
  shares: Record<ID, Rupees>;
  accountId?: ID;
}

export const splitsRepo = {
  addExpense: (e: NewGroupExpense) =>
    simulate(() => {
      const assigned = Object.values(e.shares).reduce((s, v) => s + v, 0);
      if (!(e.amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      if (assigned !== e.amount) throw new MockError('Shares must add up to the total.', 'invalid');
      const me = db.get().user.id;
      const ge: GroupExpense = { id: db.id('ge'), icon: 'receipt', date: today(), ...e };
      db.update((s) => ({ ...s, groupExpenses: [ge, ...s.groupExpenses] }));
      if (e.paidBy === me) {
        const group = db.get().groups.find((g) => g.id === e.groupId);
        insertTx({
          id: db.id('t'),
          type: 'split',
          title: e.title,
          accountId: e.accountId ?? 'hdfc',
          amount: e.amount,
          lentAmount: e.amount - (e.shares[me] ?? 0),
          date: today(),
          time: nowTime(),
          groupId: e.groupId,
          groupExpenseId: ge.id,
          detail: `${group?.name ?? 'Group'} · you paid, split ${Object.values(e.shares).filter((v) => v > 0).length} ways`,
          repeats: 'never',
        });
      }
      return ge;
    }),
  removeExpense: (id: ID) =>
    simulate(() => {
      const linked = db.get().transactions.find((t) => t.groupExpenseId === id);
      if (linked) removeTx(linked.id);
      db.update((s) => ({ ...s, groupExpenses: s.groupExpenses.filter((g) => g.id !== id) }));
      return id;
    }),
  settle: (p: { withId: ID; amount: Rupees; method: SettlementMethod; direction: 'pay' | 'receive' }) =>
    simulate(() => {
      if (!(p.amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      const me = db.get().user.id;
      const st: Settlement = {
        id: db.id('s'),
        fromId: p.direction === 'pay' ? me : p.withId,
        toId: p.direction === 'pay' ? p.withId : me,
        amount: Math.round(p.amount),
        method: p.method,
        date: today(),
      };
      db.update((s) => ({ ...s, settlements: [...s.settlements, st] }));
      return st;
    }),
  undoSettlement: (id: ID) =>
    simulate(() => {
      db.update((s) => ({ ...s, settlements: s.settlements.filter((x) => x.id !== id) }));
      return id;
    }),
};

// ---------------------------------------------------------------- goals

export const goalsRepo = {
  addContribution: (goalId: ID, amount: Rupees, accountId: ID) =>
    simulate(() => {
      if (!(amount > 0)) throw new MockError('Enter an amount.', 'invalid');
      const c: GoalContribution = { id: db.id('c'), amount: Math.round(amount), accountId, date: today() };
      db.update((s) => ({
        ...s,
        goals: s.goals.map((g) => (g.id === goalId ? { ...g, contributions: [c, ...g.contributions] } : g)),
      }));
      return c;
    }),
  removeContribution: (goalId: ID, contributionId: ID) =>
    simulate(() => {
      db.update((s) => ({
        ...s,
        goals: s.goals.map((g) =>
          g.id === goalId
            ? { ...g, contributions: g.contributions.filter((c) => c.id !== contributionId) }
            : g,
        ),
      }));
      return contributionId;
    }),
};

// ---------------------------------------------------------------- profile, notifications

export const profileRepo = {
  update: (patch: Partial<Pick<User, 'name' | 'email' | 'phone'>>) =>
    simulate(() => {
      db.update((s) => ({ ...s, user: { ...s.user, ...patch } }));
      return db.get().user;
    }),
};

export const notificationsRepo = {
  markAllRead: () =>
    simulate(() => {
      db.update((s) => ({ ...s, notifications: s.notifications.map((n) => ({ ...n, unread: false })) }));
      return db.get().notifications;
    }),
};

// ---------------------------------------------------------------- auth (mock, local only)

/** The mock account accepts this password; anything else shows the Log in error state. */
export const MOCK_PASSWORD = 'dhan-2026';
const MAX_ATTEMPTS = 3;
let failedAttempts = 0;

export const authRepo = {
  signIn: (email: string, password: string) =>
    simulate(() => {
      if (!email.includes('@')) throw new MockError('Enter a valid email address.', 'invalid');
      if (password !== MOCK_PASSWORD) {
        failedAttempts += 1;
        const left = Math.max(0, MAX_ATTEMPTS - failedAttempts);
        throw new MockError(String(left), 'invalid');
      }
      failedAttempts = 0;
      return { email };
    }),
  signUp: (name: string, email: string, password: string) =>
    simulate(() => {
      if (!name.trim()) throw new MockError('Enter your name.', 'invalid');
      if (!email.includes('@')) throw new MockError('Enter a valid email address.', 'invalid');
      if (password.length < 8) throw new MockError('Use at least 8 characters.', 'invalid');
      db.update((s) => ({ ...s, user: { ...s.user, name: name.trim(), email: email.trim() } }));
      return db.get().user;
    }),
  requestReset: (email: string) =>
    simulate(() => {
      if (!email.includes('@')) throw new MockError('Enter a valid email address.', 'invalid');
      return { email };
    }),
  resetAttempts: () => {
    failedAttempts = 0;
  },
};

/** Test helper: restore the seed. */
export function resetMockData(): void {
  db.reset();
  failedAttempts = 0;
}
