// FastAPI <-> app domain shapes. Pure functions: no network, no state.
import type { IconName } from '@/components/icons/paths';
import { iconPaths } from '@/components/icons/paths';
import type {
  Account,
  AccountType,
  Asset,
  AssetKind,
  Category,
  ChartToken,
  Goal,
  Group,
  GroupExpense,
  Liability,
  Person,
  Recurring,
  RecurringKind,
  Settlement,
  SettlementMethod,
  SplitMethod,
  Transaction,
  User,
} from '@/types/domain';
import { inr } from '@/utils/format';
import { IST_OFFSET_MINUTES } from './config';

// ---------------------------------------------------------------- wire types (FastAPI responses)

export interface WireUser {
  id: string;
  name: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
}
export interface WireAccount {
  id: string;
  name: string;
  type: string;
  balance: string;
  credit_limit: string | null;
  due_date: number | null;
  archived: boolean;
  include_in_total: boolean;
  institution_name?: string;
  account_number_mask?: string;
}
export interface WireCategory {
  id: string;
  user_id: string | null;
  name: string;
  category_type: string;
  icon: string;
  is_default: boolean;
  is_active: boolean;
}
export interface WireTransaction {
  id: string;
  account_id: string;
  destination_account_id: string | null;
  category_id: string | null;
  amount: string;
  type: string;
  description: string;
  transaction_date: string;
  notes: string;
  status: string;
  split_expense_id?: string | null;
}
export interface WireBudget {
  id: string;
  category_id: string | null;
  amount: string;
  month: string | null;
  warn_at_percent: number;
  rollover: boolean;
}
export interface WireGroup {
  id: string;
  name: string;
  description: string;
  about: string | null;
  members: { user_id: string; user_name: string }[];
  created_at: string;
}
export interface WirePerson {
  id: string;
  name: string;
  initials: string;
  avatar_tone: string;
}
export interface WireSplitExpense {
  id: string;
  group_id: string | null;
  title: string;
  amount: string;
  paid_by_id: string;
  split_type: string;
  display_method?: string | null;
  shares: Record<string, string>;
  date: string;
}
export interface WireSettlement {
  id: string;
  payer_id: string;
  payee_id: string;
  amount: string;
  method: string;
  created_at: string;
}
export interface WireGoal {
  id: string;
  name: string;
  icon: string;
  target_amount: string;
  target_date: string;
  created_at: string;
  contributions: { id: string; amount: string; account_id: string | null; date: string }[];
}
export interface WireRecurring {
  id: string;
  title: string;
  kind: string;
  amount: string;
  account_id: string;
  category_id: string | null;
  next_due_date: string;
  status: string;
  notes: string | null;
  metadata_json: Record<string, unknown> | null;
}
export interface WireAsset {
  id: string;
  name: string;
  asset_type: string;
  current_value: string;
  updated_at: string;
}
export interface WireLiability {
  id: string;
  name: string;
  liability_type: string;
  remaining_amount: string;
  monthly_emi: string | null;
}

// ---------------------------------------------------------------- the categories the app is built around

export interface StandardCategory {
  name: string;
  short: string;
  icon: IconName;
  kind: 'expense' | 'income';
  chartToken?: ChartToken;
}

/** Created for each new user so the entry screens' chips work as designed (spec §9.4). */
export const STANDARD_CATEGORIES: StandardCategory[] = [
  { name: 'Food', short: 'Food', icon: 'food', kind: 'expense', chartToken: 'chart2' },
  { name: 'Transport', short: 'Transport', icon: 'car', kind: 'expense', chartToken: 'chart3' },
  { name: 'Shopping', short: 'Shopping', icon: 'bag', kind: 'expense', chartToken: 'chart4' },
  { name: 'Bills', short: 'Bills', icon: 'bolt', kind: 'expense', chartToken: 'chart1' },
  { name: 'Health', short: 'Health', icon: 'heart', kind: 'expense' },
  { name: 'Fun and subscriptions', short: 'Fun', icon: 'film', kind: 'expense' },
  { name: 'Home', short: 'Home', icon: 'home', kind: 'expense' },
  { name: 'Gifts', short: 'Gifts', icon: 'gift', kind: 'expense' },
  { name: 'Salary', short: 'Salary', icon: 'income', kind: 'income' },
  { name: 'Freelancing', short: 'Freelancing', icon: 'briefcase', kind: 'income' },
  { name: 'Business', short: 'Business', icon: 'briefcase', kind: 'income' },
  { name: 'Gift', short: 'Gift', icon: 'gift', kind: 'income' },
  { name: 'Cashback', short: 'Cashback', icon: 'coin', kind: 'income' },
  { name: 'Interest', short: 'Interest', icon: 'percent', kind: 'income' },
  { name: 'Other', short: 'Other', icon: 'coin', kind: 'income' },
];

export const EXPENSE_CHIP_ORDER = ['Food', 'Transport', 'Shopping', 'Bills', 'Health', 'Fun and subscriptions'];
export const INCOME_CHIP_ORDER = ['Salary', 'Freelancing', 'Business', 'Gift', 'Cashback', 'Interest', 'Other'];

export const categoryKey = (name: string, kind: string) => `${kind}:${name.trim().toLowerCase()}`;
const STANDARD_BY_KEY = new Map(STANDARD_CATEGORIES.map((c) => [categoryKey(c.name, c.kind), c]));

// ---------------------------------------------------------------- small helpers

/** The signed-in user appears as 'me' everywhere in the app (splits math compares with it). */
export const ME = 'me';
export const toMe = (id: string, meId: string): string => (id === meId ? ME : id);
export const fromMe = (id: string, meId: string): string => (id === ME ? meId : id);

export const num = (value: string | number | null | undefined): number => Number(value ?? 0);

const isIcon = (name: string | undefined): name is IconName => !!name && name in iconPaths;
const icon = (name: string | undefined, fallback: IconName): IconName => (isIcon(name) ? name : fallback);

/** A stored instant as India-time date and clock time. */
export function localParts(iso: string): { date: string; time: string } {
  const shifted = new Date(Date.parse(iso) + IST_OFFSET_MINUTES * 60_000).toISOString();
  return { date: shifted.slice(0, 10), time: shifted.slice(11, 16) };
}

export const localDate = (iso: string): string => localParts(iso).date;

/** 'YYYY-MM-DD' + 'HH:mm' (India time) as an ISO timestamp with offset. */
export function toInstant(date: string, time = '12:00'): string {
  return `${date}T${time}:00+05:30`;
}

/** Today's date in India time. */
export function istToday(): string {
  return localDate(new Date().toISOString());
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return (parts.length > 1 ? `${parts[0]![0]}${parts[1]![0]}` : (parts[0] ?? 'U').slice(0, 2)).toUpperCase();
}

/** Next calendar date falling on a card's bill day (the API stores just the day number). */
export function nextDueDate(day: number, today: string): string {
  const [y, m, d] = today.split('-').map(Number) as [number, number, number];
  const build = (year: number, month: number) => {
    const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
    return `${year}-${String(month).padStart(2, '0')}-${String(Math.min(day, last)).padStart(2, '0')}`;
  };
  if (day >= d) return build(y, m);
  return m === 12 ? build(y + 1, 1) : build(y, m + 1);
}

// ---------------------------------------------------------------- mappers

export function toUser(u: WireUser): User {
  return {
    id: ME,
    name: u.name,
    email: u.email,
    phone: '',
    initials: initials(u.name),
    memberSince: localDate(u.created_at),
    currency: 'INR',
    monthStartsOn: 1,
  };
}

const ACCOUNT_TYPE_IN: Record<string, AccountType> = {
  bank: 'bank',
  savings: 'savings',
  cash: 'cash',
  wallet: 'wallet',
  credit_card: 'credit',
  credit: 'credit',
  other: 'custom',
  custom: 'custom',
  investment: 'custom',
};
const ACCOUNT_TYPE_OUT: Record<AccountType, string> = {
  bank: 'bank',
  savings: 'savings',
  cash: 'cash',
  wallet: 'wallet',
  credit: 'credit_card',
  custom: 'other',
};

export function toAccount(a: WireAccount, today: string): Account {
  return {
    id: a.id,
    name: a.name,
    type: ACCOUNT_TYPE_IN[a.type] ?? 'custom',
    subtitle: a.institution_name ?? '',
    last4: a.account_number_mask || undefined,
    balance: num(a.balance),
    creditLimit: a.credit_limit !== null ? num(a.credit_limit) : undefined,
    dueDate: a.due_date ? nextDueDate(a.due_date, today) : undefined,
    includeInTotal: a.include_in_total,
    archived: a.archived,
  };
}

export function fromAccount(a: Omit<Account, 'id' | 'archived'>) {
  return {
    name: a.name.trim(),
    type: ACCOUNT_TYPE_OUT[a.type],
    balance: String(a.balance),
    credit_limit: a.creditLimit !== undefined ? String(a.creditLimit) : null,
    due_date: a.dueDate ? Number(a.dueDate.slice(8, 10)) : null,
    include_in_total: a.includeInTotal,
    institution_name: a.subtitle ?? '',
    account_number_mask: a.last4 ?? '',
  };
}

export function toCategory(c: WireCategory): Category {
  const standard = STANDARD_BY_KEY.get(categoryKey(c.name, c.category_type));
  const kind = c.category_type === 'income' ? 'income' : 'expense';
  return {
    id: c.id,
    name: c.name,
    short: standard?.short ?? c.name,
    icon: icon(c.icon, standard?.icon ?? (kind === 'income' ? 'income' : 'tag')),
    kind,
    chartToken: standard?.chartToken,
  };
}

export function toTransaction(t: WireTransaction, categories: Map<string, Category>): Transaction {
  const { date, time } = localParts(t.transaction_date);
  const type = t.type === 'income' || t.type === 'transfer' || t.type === 'split' ? t.type : 'expense';
  const category = t.category_id ? categories.get(t.category_id) : undefined;
  return {
    id: t.id,
    type,
    title: t.description || category?.short || (type === 'income' ? 'Income' : type === 'transfer' ? 'Transfer' : 'Expense'),
    groupExpenseId: t.split_expense_id ?? undefined,
    categoryId: t.category_id ?? undefined,
    accountId: t.account_id,
    toAccountId: t.destination_account_id ?? undefined,
    amount: num(t.amount),
    date,
    time,
    note: t.notes || undefined,
    repeats: 'never',
  };
}

export function toGroup(g: WireGroup, meId: string): Group {
  return {
    id: g.id,
    name: g.name,
    memberIds: g.members.map((m) => toMe(m.user_id, meId)),
    createdAt: localDate(g.created_at),
    about: g.about || g.description || undefined,
  };
}

const TONES = ['primary', 'blue', 'green', 'sand'] as const;
export function toPerson(p: WirePerson, index: number): Person {
  const tone = (TONES as readonly string[]).includes(p.avatar_tone) ? p.avatar_tone : TONES[index % 4];
  return { id: p.id, name: p.name, initials: p.initials || initials(p.name), avatarTone: tone as Person['avatarTone'] };
}

const SPLIT_METHODS: SplitMethod[] = ['equal', 'exact', 'percent', 'shares', 'itemwise'];
export function toGroupExpense(e: WireSplitExpense, meId: string): GroupExpense {
  const method = e.display_method ?? (e.split_type === 'percentage' ? 'percent' : e.split_type);
  return {
    id: e.id,
    groupId: e.group_id ?? '',
    title: e.title,
    icon: 'receipt',
    amount: num(e.amount),
    paidBy: toMe(e.paid_by_id, meId),
    method: (SPLIT_METHODS as string[]).includes(method) ? (method as SplitMethod) : 'exact',
    shares: Object.fromEntries(Object.entries(e.shares).map(([k, v]) => [toMe(k, meId), num(v)])),
    date: localDate(e.date),
  };
}

export function toSettlement(s: WireSettlement, meId: string): Settlement {
  return {
    id: s.id,
    fromId: toMe(s.payer_id, meId),
    toId: toMe(s.payee_id, meId),
    amount: num(s.amount),
    method: (['upi', 'cash', 'bank'].includes(s.method) ? s.method : 'upi') as SettlementMethod,
    date: localDate(s.created_at),
  };
}

export function toGoal(g: WireGoal): Goal {
  return {
    id: g.id,
    name: g.name,
    icon: icon(g.icon, 'target'),
    target: num(g.target_amount),
    targetDate: g.target_date,
    createdAt: localDate(g.created_at),
    contributions: g.contributions.map((c) => ({
      id: c.id,
      amount: num(c.amount),
      accountId: c.account_id ?? '',
      date: c.date,
    })),
  };
}

const RECURRING_KINDS: RecurringKind[] = ['bill', 'emi', 'subscription', 'income'];
export function toRecurring(r: WireRecurring): Recurring {
  const meta = r.metadata_json ?? {};
  const emi = meta.emi as { paid?: unknown; total?: unknown; remaining?: unknown } | undefined;
  return {
    id: r.id,
    name: r.title,
    kind: (RECURRING_KINDS as string[]).includes(r.kind) ? (r.kind as RecurringKind) : 'bill',
    amount: num(r.amount),
    categoryId: r.category_id ?? '',
    accountId: r.account_id,
    nextDate: r.next_due_date,
    note: r.notes || undefined,
    emi: emi ? { paid: num(emi.paid as string), total: num(emi.total as string), remaining: num(emi.remaining as string) } : undefined,
    letter: typeof meta.letter === 'string' ? meta.letter : undefined,
  };
}

const ASSET_ICON: Record<string, IconName> = { mutual_fund: 'chart', stock: 'trend', epf: 'shield', gold: 'coin', real_estate: 'home', fixed_deposit: 'bank', cash: 'cash', crypto: 'coin' };
export function toAsset(a: WireAsset): Asset {
  return {
    id: a.id,
    name: a.name,
    kind: a.asset_type as AssetKind,
    icon: ASSET_ICON[a.asset_type] ?? 'chart',
    value: num(a.current_value),
    updatedAt: localDate(a.updated_at),
  };
}

const LIABILITY_ICON: Record<string, IconName> = { auto_loan: 'car', mortgage: 'home', credit_card: 'card', student_loan: 'doc' };
const LIABILITY_LABEL: Record<string, string> = { auto_loan: 'Vehicle loan', mortgage: 'Home loan', personal_loan: 'Personal loan', credit_card: 'Card dues', student_loan: 'Education loan' };
export function toLiability(l: WireLiability): Liability {
  return {
    id: l.id,
    name: l.name,
    icon: LIABILITY_ICON[l.liability_type] ?? 'card',
    value: num(l.remaining_amount),
    note: l.monthly_emi ? `EMI ${inr(num(l.monthly_emi))}/mo` : LIABILITY_LABEL[l.liability_type] ?? 'Loan',
  };
}
