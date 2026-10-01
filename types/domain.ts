// Domain types (spec §6). These shapes are also the future FastAPI contract.
import type { IconName } from '@/components/icons/paths';

export type ID = string;
/** 'YYYY-MM-DD' */
export type ISODate = string;
/** Integer rupees. */
export type Rupees = number;
/** 'YYYY-MM' */
export type MonthKey = string;

export interface User {
  id: ID;
  name: string;
  email: string;
  phone: string;
  initials: string;
  memberSince: ISODate;
  currency: 'INR';
  monthStartsOn: number;
}

export type AccountType = 'bank' | 'cash' | 'savings' | 'credit' | 'wallet' | 'custom';

export interface Account {
  id: ID;
  name: string;
  type: AccountType;
  subtitle: string;
  last4?: string;
  balance: Rupees;
  creditLimit?: Rupees;
  dueDate?: ISODate;
  includeInTotal: boolean;
  archived: boolean;
}

export type CategoryKind = 'expense' | 'income';
export type ChartToken = 'chart1' | 'chart2' | 'chart3' | 'chart4' | 'chart5';

export interface Category {
  id: ID;
  name: string;
  /** Short label used on chips and in row subtitles. */
  short: string;
  icon: IconName;
  kind: CategoryKind;
  chartToken?: ChartToken;
}

export type TxType = 'expense' | 'income' | 'transfer' | 'split';

export interface Transaction {
  id: ID;
  type: TxType;
  title: string;
  categoryId?: ID;
  accountId?: ID;
  toAccountId?: ID;
  amount: Rupees;
  date: ISODate;
  /** 'HH:mm' 24h */
  time?: string;
  note?: string;
  /** Free-text subtitle override (e.g. 'Website project'). */
  detail?: string;
  groupId?: ID;
  groupExpenseId?: ID;
  lentAmount?: Rupees;
  receiptUri?: string;
  repeats: 'never' | 'monthly';
}

export interface CategoryBudget {
  categoryId: ID;
  limit: Rupees;
  rollover: boolean;
  warnAtPercent: number;
}

export interface Budget {
  month: MonthKey;
  categories: CategoryBudget[];
}

export type AvatarTone = 'primary' | 'blue' | 'green' | 'sand';

export interface Person {
  id: ID;
  name: string;
  initials: string;
  avatarTone: AvatarTone;
}

export interface Group {
  id: ID;
  name: string;
  memberIds: ID[];
  createdAt: ISODate;
  /** Short description of what the group splits (Splits overview). */
  about?: string;
}

export type SplitMethod = 'equal' | 'exact' | 'percent' | 'shares' | 'itemwise';

export interface GroupExpense {
  id: ID;
  groupId: ID;
  title: string;
  icon: IconName;
  amount: Rupees;
  paidBy: ID;
  method: SplitMethod;
  /** Each member's share in rupees; sums to amount. */
  shares: Record<ID, Rupees>;
  date: ISODate;
}

export type SettlementMethod = 'upi' | 'cash' | 'bank';

export interface Settlement {
  id: ID;
  fromId: ID;
  toId: ID;
  amount: Rupees;
  method: SettlementMethod;
  date: ISODate;
}

export interface GoalContribution {
  id: ID;
  amount: Rupees;
  accountId: ID;
  date: ISODate;
}

export interface Goal {
  id: ID;
  name: string;
  icon: IconName;
  target: Rupees;
  targetDate: ISODate;
  createdAt: ISODate;
  contributions: GoalContribution[];
}

export type RecurringKind = 'bill' | 'emi' | 'subscription' | 'income';

export interface Recurring {
  id: ID;
  name: string;
  kind: RecurringKind;
  amount: Rupees;
  categoryId: ID;
  accountId: ID;
  nextDate: ISODate;
  note?: string;
  emi?: { paid: number; total: number; remaining: Rupees };
  letter?: string;
}

export type AssetKind = 'mutual_fund' | 'epf' | 'gold';

export interface Asset {
  id: ID;
  name: string;
  kind: AssetKind;
  icon: IconName;
  value: Rupees;
  updatedAt: ISODate;
  note?: string;
}

export interface Liability {
  id: ID;
  name: string;
  icon: IconName;
  value: Rupees;
  note: string;
}

export interface MonthHistory {
  month: MonthKey;
  income: Rupees;
  spent: Rupees;
  /** Spending per category id for the month. */
  byCategory: Record<ID, Rupees>;
  netWorth: Rupees;
}

export interface AppNotification {
  id: ID;
  icon: IconName;
  tone: 'warn' | 'primary' | 'neutral';
  title: string;
  body: string;
  at: string;
  section: 'today' | 'earlier';
  unread: boolean;
  route: string;
}

export interface AIResponse {
  id: 'food' | 'most' | 'save' | 'owe';
  question: string;
  answer: string;
  stats: { label: string; value: string }[];
}

export interface Insights {
  home: string;
  search: string;
  goals: string;
  subscriptions: string;
  budgetSuggestion: string;
}

export interface Device {
  id: ID;
  name: string;
  lastUsed: string;
  current: boolean;
}
