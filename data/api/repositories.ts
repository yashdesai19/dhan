// FastAPI-backed repositories: the same exports and signatures as the mock ones in
// data/repositories/mock.ts, so the query hooks and every screen above them are unchanged.
import type {
  AIResponse,
  Account,
  AppNotification,
  Asset,
  Budget,
  Category,
  CategoryBudget,
  Device,
  GoalContribution,
  GroupExpense,
  ID,
  Insights,
  Liability,
  MonthHistory,
  MonthKey,
  Rupees,
  Settlement,
  SettlementMethod,
  Transaction,
  User,
} from '@/types/domain';
import { aiResponses as SUGGESTED_QUESTIONS } from '@/mock/seed';
import { shiftMonth } from '@/utils/dates';
import { inr } from '@/utils/format';
import { netWorth } from '@/utils/netWorth';
import { isLoanType, type NewHolding, type NewRecurring } from '@/data/repositories/mock';
import { ApiError, api } from './client';
import {
  EXPENSE_CHIP_ORDER,
  INCOME_CHIP_ORDER,
  STANDARD_CATEGORIES,
  categoryKey,
  fromAccount,
  fromMe,
  istToday,
  localParts,
  toAccount,
  toAsset,
  toCategory,
  toGoal,
  toGroup,
  toGroupExpense,
  toLiability,
  toPerson,
  toRecurring,
  toSettlement,
  toTransaction,
  toUser,
  type WireAccount,
  type WireAsset,
  type WireBudget,
  type WireCategory,
  type WireGoal,
  type WireGroup,
  type WireLiability,
  type WirePerson,
  type WireRecurring,
  type WireSettlement,
  type WireSplitExpense,
  type WireTransaction,
  type WireUser,
  toInstant,
} from './mappers';
import { tokens } from './tokens';

// ---------------------------------------------------------------- per-session state

let provisioning: Promise<void> | null = null;
let conversationId: string | null = null;
let recentSearches: string[] = [];
let failedLogins = 0;
const MAX_LOGIN_ATTEMPTS = 5; // backend: 5 wrong passwords, then a 15-minute pause

/** Forget everything tied to the previous user. */
function resetSessionState(): void {
  provisioning = null;
  conversationId = null;
  recentSearches = [];
}

async function meId(): Promise<string> {
  const cached = await tokens.userId();
  if (cached) return cached;
  const me = await api.get<WireUser>('/auth/me');
  await tokens.saveUserId(me.id);
  return me.id;
}

async function startSession(body: { access_token: string; refresh_token: string; user: WireUser }) {
  resetSessionState();
  await tokens.save(body.access_token, body.refresh_token);
  await tokens.saveUserId(body.user.id);
}

// ---------------------------------------------------------------- reads

/**
 * Creates the app's standard categories the user doesn't have yet. Several screens load
 * categories at once on first launch; they all share this one run so nothing is created twice.
 */
function provisionCategories(): Promise<void> {
  provisioning ??= (async () => {
    const wire = await api.get<WireCategory[]>('/categories');
    const owned = new Set(wire.filter((c) => c.user_id).map((c) => categoryKey(c.name, c.category_type)));
    for (const c of STANDARD_CATEGORIES.filter((x) => !owned.has(categoryKey(x.name, x.kind)))) {
      try {
        await api.post('/categories', { name: c.name, category_type: c.kind, icon: c.icon });
      } catch (e) {
        // A same-named category already covers it
        if (!(e instanceof ApiError) || e.code !== 'invalid') throw e;
      }
    }
  })().catch((e: unknown) => {
    provisioning = null; // try again next time
    throw e;
  });
  return provisioning;
}

async function fetchCategories(): Promise<Category[]> {
  await provisionCategories();
  const wire = await api.get<WireCategory[]>('/categories');
  // The user's own first, then shared ones not duplicating a name
  const seen = new Set<string>();
  const ordered = [...wire.filter((c) => c.user_id), ...wire.filter((c) => !c.user_id)];
  return ordered
    .filter((c) => c.is_active !== false)
    .filter((c) => {
      const key = categoryKey(c.name, c.category_type);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map(toCategory);
}

async function fetchAccounts(): Promise<Account[]> {
  const today = istToday();
  const wire = await api.get<WireAccount[]>('/accounts?include_archived=true&limit=500');
  return wire.map((a) => toAccount(a, today));
}

async function fetchTransactions(): Promise<Transaction[]> {
  const categories = new Map((await fetchCategories()).map((c) => [c.id, c]));
  const page = 500;
  const all: WireTransaction[] = [];
  for (let offset = 0; ; offset += page) {
    const batch = await api.get<WireTransaction[]>(`/transactions?limit=${page}&offset=${offset}`);
    all.push(...batch);
    if (batch.length < page) break;
  }
  const txs = all.filter((t) => t.status === 'completed').map((t) => toTransaction(t, categories));
  if (!txs.some((t) => t.type === 'split')) return txs;
  // A group-expense payment shows which group it was for and what you paid for others
  const me = await meId();
  const expenses = new Map(
    (await api.get<WireSplitExpense[]>('/splits')).map((e) => [e.id, toGroupExpense(e, me)]),
  );
  const groups = new Map((await api.get<WireGroup[]>('/groups')).map((g) => [g.id, g.name]));
  return txs.map((t) => {
    const e = t.groupExpenseId ? expenses.get(t.groupExpenseId) : undefined;
    if (t.type !== 'split' || !e) return t;
    const ways = Object.values(e.shares).filter((v) => v > 0).length;
    return {
      ...t,
      groupId: e.groupId,
      lentAmount: e.amount - (e.shares.me ?? 0),
      detail: `${groups.get(e.groupId) ?? 'Group'} · you paid, split ${ways} ways`,
    };
  });
}

async function fetchBudgets(): Promise<Budget[]> {
  const wire = await api.get<WireBudget[]>('/budgets');
  const byMonth = new Map<MonthKey, CategoryBudget[]>();
  for (const b of wire) {
    if (!b.category_id || !b.month) continue; // the app budgets per category
    const list = byMonth.get(b.month) ?? [];
    list.push({
      categoryId: b.category_id,
      limit: Number(b.amount),
      rollover: b.rollover,
      warnAtPercent: b.warn_at_percent,
    });
    byMonth.set(b.month, list);
  }
  return [...byMonth].map(([month, categories]) => ({ month, categories }));
}

async function fetchAssets(): Promise<Asset[]> {
  return (await api.get<WireAsset[]>('/net-worth/assets')).map(toAsset);
}

async function fetchLiabilities(): Promise<Liability[]> {
  return (await api.get<WireLiability[]>('/net-worth/liabilities')).map(toLiability);
}

/**
 * Closed months for Reports and Budget: income, spending and per-category spending come from
 * the reports API. Net worth at each month end is rebuilt from today's net worth minus the
 * net flow of every later month (the API keeps no snapshots; assets/loans are taken as unchanged).
 */
async function fetchHistory(): Promise<MonthHistory[]> {
  const current = istToday().slice(0, 7);
  const months = [-5, -4, -3, -2, -1].map((d) => shiftMonth(current, d));
  const [snapshots, monthly, accounts, assets, liabilities, ...byCategory] = await Promise.all([
    api.get<{ month: string; net_worth: string }[]>('/net-worth/history'),
    api.get<{ trend: { month: string; income: string; spent: string; net: string }[] }>(
      `/reports/monthly?month=${current}&months=6`,
    ),
    fetchAccounts(),
    fetchAssets(),
    fetchLiabilities(),
    ...months.map((m) =>
      api.get<{ categories: { category_id: string | null; amount: string }[] }>(
        `/reports/categories?month=${m}`,
      ),
    ),
  ]);
  const trend = new Map(monthly.trend.map((p) => [p.month, p]));
  const recorded = new Map(snapshots.map((s) => [s.month, s.net_worth]));
  let worth = netWorth(accounts, assets, liabilities).net;
  const history: MonthHistory[] = [];
  // Walk back from the current month: each month's end = the following month's end - its flow
  for (let i = months.length - 1; i >= 0; i -= 1) {
    const later = i === months.length - 1 ? current : months[i + 1]!;
    worth -= Number(trend.get(later)?.net ?? 0);
    const month = months[i]!;
    const point = trend.get(month);
    history.unshift({
      month,
      income: Number(point?.income ?? 0),
      spent: Number(point?.spent ?? 0),
      byCategory: Object.fromEntries(
        (byCategory[i]?.categories ?? [])
          .filter((c) => c.category_id)
          .map((c) => [c.category_id as string, Number(c.amount)]),
      ),
      // A recorded month-end value when there is one; otherwise the estimate
      netWorth: Math.round(Number(recorded.get(month) ?? worth)),
    });
  }
  return history;
}

const DAY_MS = 86_400_000;
const daysUntil = (date: string, today: string) =>
  Math.round((Date.parse(date) - Date.parse(today)) / DAY_MS);

/** Reminders worked out from the user's data: bills due soon and budgets running out. */
async function buildNotifications(): Promise<AppNotification[]> {
  const today = istToday();
  const month = today.slice(0, 7);
  const [recurring, budgets, transactions, categories] = await Promise.all([
    api.get<WireRecurring[]>('/recurring'),
    fetchBudgets(),
    fetchTransactions(),
    fetchCategories(),
  ]);
  const out: AppNotification[] = [];
  for (const r of recurring.filter((x) => x.status === 'active' && x.kind !== 'income')) {
    const days = daysUntil(r.next_due_date, today);
    if (days < 0 || days > 3) continue;
    const when = days === 0 ? 'today' : days === 1 ? 'tomorrow' : `in ${days} days`;
    out.push({
      id: `due-${r.id}`,
      icon: 'calendar',
      tone: days <= 1 ? 'warn' : 'neutral',
      title: `${r.title} due ${when}`,
      body: `${inr(Number(r.amount))} from your account.`,
      at: r.next_due_date,
      section: days <= 1 ? 'today' : 'earlier',
      unread: true,
      route: '/recurring',
    });
  }
  const spent = new Map<string, number>();
  for (const t of transactions) {
    if (t.type === 'expense' && t.categoryId && t.date.startsWith(month)) {
      spent.set(t.categoryId, (spent.get(t.categoryId) ?? 0) + t.amount);
    }
  }
  for (const c of budgets.find((b) => b.month === month)?.categories ?? []) {
    const used = c.limit > 0 ? Math.round(((spent.get(c.categoryId) ?? 0) / c.limit) * 100) : 0;
    if (used < c.warnAtPercent) continue;
    const name = categories.find((x) => x.id === c.categoryId)?.name ?? 'A category';
    out.push({
      id: `budget-${c.categoryId}`,
      icon: 'alert',
      tone: 'warn',
      title: `${name} is at ${used}% of its budget`,
      body: `${inr(Math.max(0, c.limit - (spent.get(c.categoryId) ?? 0)))} left this month.`,
      at: today,
      section: 'today',
      unread: true,
      route: '/budget',
    });
  }
  return out;
}

/** One-line observations from the user's real numbers (null when there's nothing to say). */
async function buildInsights(): Promise<Insights | null> {
  const today = istToday();
  const month = today.slice(0, 7);
  const [transactions, recurring, goals] = await Promise.all([
    fetchTransactions(),
    api.get<WireRecurring[]>('/recurring'),
    api.get<WireGoal[]>('/goals'),
  ]);
  const thisMonth = transactions.filter((t) => t.date.startsWith(month));
  const income = thisMonth.filter((t) => t.type === 'income').reduce((s, t) => s + t.amount, 0);
  const spent = thisMonth.filter((t) => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
  if (!thisMonth.length && !recurring.length && !goals.length) return null;
  const byTitle = new Map<string, number>();
  for (const t of thisMonth.filter((x) => x.type === 'expense')) {
    byTitle.set(t.title, (byTitle.get(t.title) ?? 0) + t.amount);
  }
  const top = [...byTitle].sort((a, b) => b[1] - a[1])[0];
  const subs = recurring.filter((r) => r.status === 'active' && r.kind === 'subscription');
  const subsMonthly = subs.reduce((s, r) => s + Number(r.amount), 0);
  return {
    home:
      income > 0
        ? `You’ve kept ${inr(Math.max(0, income - spent))} of ${inr(income)} earned this month.`
        : `You’ve spent ${inr(spent)} so far this month.`,
    search:
      top && spent > 0
        ? `${top[0]} is ${Math.round((top[1] / spent) * 100)}% of your spending this month.`
        : '',
    goals: 'A goal is behind schedule. Adding a little each month keeps it on track.',
    subscriptions: subs.length
      ? `You pay ${inr(subsMonthly)} a month for ${subs.length} subscription${subs.length === 1 ? '' : 's'}.`
      : '',
    budgetSuggestion: 'Based on your recent spending, with some breathing room.',
  };
}

async function fetchChipOrder(): Promise<{ expense: string[]; income: string[] }> {
  const categories = await fetchCategories();
  const idFor = (name: string, kind: string) =>
    categories.find((c) => c.kind === kind && c.name.toLowerCase() === name.toLowerCase())?.id;
  const pick = (names: string[], kind: string) =>
    names.map((n) => idFor(n, kind)).filter((id): id is string => !!id);
  return { expense: pick(EXPENSE_CHIP_ORDER, 'expense'), income: pick(INCOME_CHIP_ORDER, 'income') };
}

export const readRepo = {
  user: async (): Promise<User> => toUser(await api.get<WireUser>('/auth/me')),
  accounts: fetchAccounts,
  categories: fetchCategories,
  transactions: fetchTransactions,
  budgets: fetchBudgets,
  people: async () => (await api.get<WirePerson[]>('/people')).map(toPerson),
  groups: async () => {
    const me = await meId();
    return (await api.get<WireGroup[]>('/groups')).map((g) => toGroup(g, me));
  },
  groupExpenses: async (): Promise<GroupExpense[]> => {
    const me = await meId();
    return (await api.get<WireSplitExpense[]>('/splits'))
      .filter((e) => e.group_id)
      .map((e) => toGroupExpense(e, me));
  },
  settlements: async (): Promise<Settlement[]> => {
    const me = await meId();
    return (await api.get<WireSettlement[]>('/settlements')).map((s) => toSettlement(s, me));
  },
  goals: async () => (await api.get<WireGoal[]>('/goals')).map(toGoal),
  recurring: async () =>
    (await api.get<WireRecurring[]>('/recurring')).filter((r) => r.status === 'active').map(toRecurring),
  assets: fetchAssets,
  liabilities: fetchLiabilities,
  history: fetchHistory,
  notifications: buildNotifications,
  aiResponses: async (): Promise<AIResponse[]> =>
    SUGGESTED_QUESTIONS.map((r) => ({ id: r.id, question: r.question, answer: '', stats: [] })),
  insights: buildInsights,
  devices: async (): Promise<Device[]> => [
    { id: 'this', name: 'This device', lastUsed: 'This device', current: true },
  ],
  recentSearches: async () => recentSearches,
  chipOrder: fetchChipOrder,
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
  return localParts(new Date().toISOString()).time;
}

async function created(t: WireTransaction): Promise<Transaction> {
  const categories = new Map((await fetchCategories()).map((c) => [c.id, c]));
  return toTransaction(t, categories);
}

function requireAmount(amount: Rupees) {
  if (!(amount > 0)) throw new ApiError('Enter an amount.', 'invalid');
}

async function addEntry(type: 'expense' | 'income', e: NewEntry): Promise<Transaction> {
  requireAmount(e.amount);
  const accounts = await fetchAccounts();
  const validAccount = accounts.find((a) => a.id === e.accountId) ?? accounts.filter((a) => !a.archived)[0];
  if (!validAccount) {
    throw new ApiError('Please add an account before adding a transaction.', 'invalid');
  }
  const category = (await fetchCategories()).find((c) => c.id === e.categoryId);
  return created(
    await api.post<WireTransaction>('/transactions', {
      account_id: validAccount.id,
      category_id: e.categoryId || null,
      amount: String(e.amount),
      type,
      description: e.title?.trim() || category?.short || (type === 'income' ? 'Income' : 'Expense'),
      transaction_date: toInstant(e.date ?? istToday(), nowTime()),
      notes: e.note ?? '',
    }),
  );
}

export const transactionsRepo = {
  addExpense: (e: NewEntry) => addEntry('expense', e),
  addIncome: (e: NewEntry) => addEntry('income', e),

  addTransfer: async (t: { amount: Rupees; fromId: ID; toId: ID; date?: string; note?: string }) => {
    requireAmount(t.amount);
    const accounts = await fetchAccounts();
    const live = accounts.filter((a) => !a.archived);
    const from = live.find((a) => a.id === t.fromId) ?? live[0];
    const to = live.find((a) => a.id === t.toId) ?? live.find((a) => a.id !== from?.id);
    if (!from || !to || from.id === to.id) {
      throw new ApiError('Transfers require at least two different accounts.', 'invalid');
    }
    return created(
      await api.post<WireTransaction>('/transactions', {
        account_id: from.id,
        destination_account_id: to.id,
        amount: String(t.amount),
        type: 'transfer',
        description: `${from.name} → ${to.name}`,
        transaction_date: toInstant(t.date ?? istToday(), nowTime()),
        notes: t.note ?? '',
      }),
    );
  },

  update: async (id: ID, patch: Partial<Omit<Transaction, 'id' | 'type'>>) => {
    const before = await created(await api.get<WireTransaction>(`/transactions/${id}`));
    const body: Record<string, unknown> = {};
    if (patch.amount !== undefined) body.amount = String(patch.amount);
    if (patch.title !== undefined) body.description = patch.title;
    if (patch.note !== undefined) body.notes = patch.note ?? '';
    if (patch.categoryId !== undefined) body.category_id = patch.categoryId || null;
    if (patch.accountId !== undefined) body.account_id = patch.accountId;
    if (patch.toAccountId !== undefined) body.destination_account_id = patch.toAccountId;
    if (patch.date !== undefined || patch.time !== undefined) {
      body.transaction_date = toInstant(patch.date ?? before.date, patch.time ?? before.time);
    }
    return created(await api.patch<WireTransaction>(`/transactions/${id}`, body));
  },

  remove: async (id: ID) => {
    const before = await created(await api.get<WireTransaction>(`/transactions/${id}`));
    await api.del(`/transactions/${id}`);
    return before;
  },

  /** Undo for delete and for a just-saved entry: records it again (with a new id). */
  restore: async (t: Transaction) =>
    created(
      await api.post<WireTransaction>('/transactions', {
        account_id: t.accountId,
        destination_account_id: t.type === 'transfer' ? t.toAccountId : null,
        category_id: t.type === 'transfer' ? null : (t.categoryId ?? null),
        amount: String(t.amount),
        type: t.type === 'split' ? 'expense' : t.type,
        description: t.title,
        transaction_date: toInstant(t.date, t.time),
        notes: t.note ?? '',
      }),
    ),

  addRecentSearch: async (q: string) => {
    const term = q.trim();
    if (term) recentSearches = [term, ...recentSearches.filter((x) => x !== term)].slice(0, 6);
    return recentSearches;
  },
};

// ---------------------------------------------------------------- accounts

export type AccountInput = Omit<Account, 'id' | 'archived'> & { id?: ID };

export const accountsRepo = {
  upsert: async (a: AccountInput): Promise<Account> => {
    if (!a.name.trim()) throw new ApiError('Give the account a name.', 'invalid');
    const body = { ...fromAccount(a), archived: false };
    const wire = a.id
      ? await api.patch<WireAccount>(`/accounts/${a.id}`, body)
      : await api.post<WireAccount>('/accounts', body);
    return toAccount(wire, istToday());
  },
  archive: async (id: ID) => {
    await api.post(`/accounts/${id}/archive`);
    return id;
  },
};

// ---------------------------------------------------------------- budget

async function budgetsFor(month: MonthKey): Promise<WireBudget[]> {
  return (await api.get<WireBudget[]>(`/budgets?month=${month}`)).filter((b) => b.category_id);
}

async function saveCategoryBudget(month: MonthKey, c: CategoryBudget, existing: WireBudget[]) {
  if (!(c.limit > 0)) throw new ApiError('Set a limit above ₹0.', 'invalid');
  const current = existing.find((b) => b.category_id === c.categoryId);
  const fields = { amount: String(c.limit), warn_at_percent: c.warnAtPercent, rollover: c.rollover };
  if (current) await api.patch(`/budgets/${current.id}`, fields);
  else await api.post('/budgets/category', { ...fields, category_id: c.categoryId, month });
}

export const budgetRepo = {
  setCategory: async (month: MonthKey, c: CategoryBudget) => {
    await saveCategoryBudget(month, c, await budgetsFor(month));
    return c;
  },
  removeCategory: async (month: MonthKey, categoryId: ID) => {
    const current = (await budgetsFor(month)).find((b) => b.category_id === categoryId);
    if (current) await api.del(`/budgets/${current.id}`);
    return categoryId;
  },
  replace: async (month: MonthKey, categories: CategoryBudget[]) => {
    const existing = await budgetsFor(month);
    for (const c of categories) await saveCategoryBudget(month, c, existing);
    const keep = new Set(categories.map((c) => c.categoryId));
    for (const b of existing) if (!keep.has(b.category_id!)) await api.del(`/budgets/${b.id}`);
    return categories;
  },
};

// ---------------------------------------------------------------- splits

export interface NewGroupExpense {
  groupId: ID;
  title: string;
  amount: Rupees;
  paidBy: ID;
  method: 'equal' | 'exact' | 'percent' | 'shares' | 'itemwise';
  shares: Record<ID, Rupees>;
  accountId?: ID;
}

export const splitsRepo = {
  addExpense: async (e: NewGroupExpense): Promise<GroupExpense> => {
    if (!(e.amount > 0)) throw new ApiError('Enter an amount.', 'invalid');
    const assigned = Object.values(e.shares).reduce((s, v) => s + v, 0);
    if (assigned !== e.amount) throw new ApiError('Shares must add up to the total.', 'invalid');
    const me = await meId();
    const members = Object.keys(e.shares).filter((id) => (e.shares[id] ?? 0) > 0);
    // The app already worked out each share in rupees; send them as exact amounts so the
    // server stores exactly what the user saw
    const wire = await api.post<WireSplitExpense>('/splits', {
      group_id: e.groupId,
      title: e.title.trim(),
      amount: String(e.amount),
      paid_by_id: fromMe(e.paidBy, me),
      split_type: 'exact',
      display_method: e.method,
      member_ids: members.map((id) => fromMe(id, me)),
      exact: Object.fromEntries(members.map((id) => [fromMe(id, me), String(e.shares[id])])),
      // Paid by you from an account: the server moves its balance (not counted as spending)
      account_id: e.paidBy === 'me' && e.accountId ? e.accountId : null,
    });
    return toGroupExpense(wire, me);
  },
  removeExpense: async (id: ID) => {
    await api.del(`/splits/${id}`);
    return id;
  },
  settle: async (p: {
    withId: ID;
    amount: Rupees;
    method: SettlementMethod;
    direction: 'pay' | 'receive';
  }) => {
    if (!(p.amount > 0)) throw new ApiError('Enter an amount.', 'invalid');
    const me = await meId();
    const wire = await api.post<WireSettlement>('/settlements', {
      payee_id: fromMe(p.withId, me),
      amount: String(p.amount),
      method: p.method,
      direction: p.direction === 'pay' ? 'paid' : 'received',
    });
    return toSettlement(wire, me);
  },
  createGroup: async (g: { name: string; memberEmails: string[] }): Promise<ID> => {
    if (!g.name.trim()) throw new ApiError('Give the group a name.', 'invalid');
    const group = await api.post<WireGroup>('/groups', { name: g.name.trim() });
    for (const email of g.memberEmails.map((e) => e.trim()).filter(Boolean)) {
      try {
        await api.post(`/groups/${group.id}/members`, { email });
      } catch (e) {
        throw new ApiError(
          e instanceof ApiError && e.code === 'not_found'
            ? `${email} doesn’t have a DHAN account yet.`
            : (e as Error).message,
          'invalid',
        );
      }
    }
    return group.id;
  },
  undoSettlement: async (id: ID) => {
    await api.del(`/settlements/${id}`);
    return id;
  },
};

// ---------------------------------------------------------------- recurring

export const recurringRepo = {
  create: async (r: NewRecurring): Promise<ID> => {
    if (!r.name.trim()) throw new ApiError('Give it a name.', 'invalid');
    if (!(r.amount > 0)) throw new ApiError('Enter an amount.', 'invalid');
    const created = await api.post<WireRecurring>('/recurring', {
      title: r.name.trim(),
      kind: r.kind,
      amount: String(r.amount),
      account_id: r.accountId,
      frequency: 'monthly',
      next_due_date: r.nextDate,
    });
    return created.id;
  },
};

// ---------------------------------------------------------------- net worth

export const netWorthRepo = {
  add: async (h: NewHolding): Promise<ID> => {
    if (!h.name.trim()) throw new ApiError('Give it a name.', 'invalid');
    if (!(h.value > 0)) throw new ApiError('Enter an amount.', 'invalid');
    const amount = String(h.value);
    const created = isLoanType(h.type)
      ? await api.post<{ id: ID }>('/net-worth/liabilities', {
          name: h.name.trim(),
          liability_type: h.type,
          total_amount: amount,
          remaining_amount: amount,
        })
      : await api.post<{ id: ID }>('/net-worth/assets', {
          name: h.name.trim(),
          asset_type: h.type,
          current_value: amount,
        });
    return created.id;
  },
};

// ---------------------------------------------------------------- goals

export const goalsRepo = {
  create: async (g: { name: string; target: Rupees; targetDate: string; icon: string }): Promise<ID> => {
    if (!g.name.trim()) throw new ApiError('Give the goal a name.', 'invalid');
    if (!(g.target > 0)) throw new ApiError('Set a target above ₹0.', 'invalid');
    const goal = await api.post<WireGoal>('/goals', {
      name: g.name.trim(),
      target_amount: String(g.target),
      target_date: g.targetDate,
      icon: g.icon,
    });
    return goal.id;
  },
  addContribution: async (goalId: ID, amount: Rupees, accountId: ID): Promise<GoalContribution> => {
    if (!(amount > 0)) throw new ApiError('Enter an amount.', 'invalid');
    const goal = toGoal(
      await api.post<WireGoal>(`/goals/${goalId}/contributions`, {
        amount: String(amount),
        account_id: accountId || null,
        date: istToday(),
      }),
    );
    // Newest first; the one just added is the newest of today's
    return goal.contributions[0]!;
  },
  removeContribution: async (goalId: ID, contributionId: ID) => {
    await api.del(`/goals/${goalId}/contributions/${contributionId}`);
    return contributionId;
  },
};

// ---------------------------------------------------------------- profile, notifications

export const profileRepo = {
  update: async (patch: Partial<Pick<User, 'name' | 'email' | 'phone'>>): Promise<User> => {
    const current = toUser(await api.get<WireUser>('/auth/me'));
    if (patch.email !== undefined && patch.email.trim().toLowerCase() !== current.email) {
      throw new ApiError(
        'Your email can’t be changed here. Contact support to move your account.',
        'invalid',
      );
    }
    if (patch.name === undefined || patch.name.trim() === current.name)
      return { ...current, phone: patch.phone ?? '' };
    return toUser(await api.patch<WireUser>('/auth/me', { name: patch.name.trim() }));
  },
};

export const notificationsRepo = {
  markAllRead: async (): Promise<AppNotification[]> => [],
};

// ---------------------------------------------------------------- AI

export const aiRepo = {
  /** Asks DHAN AI; the answer is computed by the server from this user's own data. */
  ask: async (question: string): Promise<{ answer: string; stats: { label: string; value: string }[] }> => {
    conversationId ??= (await api.post<{ id: string }>('/ai/conversations', {})).id;
    const exchange = await api.post<{
      assistant_message: { content: string; stats: { label: string; value: string }[] };
    }>(`/ai/conversations/${conversationId}/messages`, { content: question });
    return { answer: exchange.assistant_message.content, stats: exchange.assistant_message.stats };
  },
};

// ---------------------------------------------------------------- auth

export const MOCK_PASSWORD = '';

export const authRepo = {
  signIn: async (email: string, password: string) => {
    try {
      const body = await api.post<{ access_token: string; refresh_token: string; user: WireUser }>(
        '/auth/login',
        { email: email.trim(), password },
        { auth: false },
      );
      failedLogins = 0;
      await startSession(body);
      return { email: body.user.email };
    } catch (e) {
      // The Log in screen reads a number as "attempts left" and shows its banner
      if (e instanceof ApiError && e.status === 401) {
        failedLogins += 1;
        throw new ApiError(String(Math.max(0, MAX_LOGIN_ATTEMPTS - failedLogins)), 'invalid', 401);
      }
      if (e instanceof ApiError && e.code === 'limited') throw new ApiError('0', 'limited', 429);
      throw e;
    }
  },
  signUp: async (name: string, email: string, password: string) => {
    if (!name.trim()) throw new ApiError('Enter your name.', 'invalid');
    if (password.length < 8) throw new ApiError('Use at least 8 characters.', 'invalid');
    const body = await api.post<{ access_token: string; refresh_token: string; user: WireUser }>(
      '/auth/register',
      { name: name.trim(), email: email.trim(), password },
      { auth: false },
    );
    await startSession(body);
    return toUser(body.user);
  },
  requestReset: async (email: string): Promise<{ email: string }> => {
    await api.post('/auth/forgot-password', { email: email.trim() }, { auth: false });
    return { email };
  },
  /** Sets a new password with the code from the reset email. */
  confirmReset: async (code: string, password: string): Promise<void> => {
    if (password.length < 8) throw new ApiError('Use at least 8 characters.', 'invalid');
    await api.post('/auth/reset-password', { token: code.trim(), new_password: password }, { auth: false });
  },
  /** Ends the session on the server (best effort) and forgets it on this device. */
  signOut: async () => {
    const refresh = await tokens.refresh();
    try {
      if (refresh) await api.post('/auth/logout', { refresh_token: refresh });
    } catch {
      // Offline or already expired: the local sign-out below still happens
    }
    await tokens.clear();
    resetSessionState();
  },
  resetAttempts: () => {
    failedLogins = 0;
  },
};
