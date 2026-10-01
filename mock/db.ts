// In-memory mock database (spec §13, step 1). Only repositories import this file.
import * as seed from './seed';
import type {
  AIResponse,
  Account,
  AppNotification,
  Asset,
  Budget,
  Category,
  Device,
  Goal,
  Group,
  GroupExpense,
  Insights,
  Liability,
  MonthHistory,
  Person,
  Recurring,
  Settlement,
  Transaction,
  User,
} from '@/types/domain';

export interface DbState {
  user: User;
  accounts: Account[];
  categories: Category[];
  transactions: Transaction[];
  budgets: Budget[];
  people: Person[];
  groups: Group[];
  groupExpenses: GroupExpense[];
  settlements: Settlement[];
  goals: Goal[];
  recurring: Recurring[];
  assets: Asset[];
  liabilities: Liability[];
  history: MonthHistory[];
  notifications: AppNotification[];
  aiResponses: AIResponse[];
  insights: Insights;
  devices: Device[];
  recentSearches: string[];
  /** Chip order on the entry screens (spec §9.4). */
  chipOrder: { expense: string[]; income: string[] };
}

function fromSeed(): DbState {
  const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;
  return clone({
    user: seed.user,
    accounts: seed.accounts,
    categories: seed.categories,
    transactions: seed.transactions,
    budgets: seed.budgets,
    people: seed.people,
    groups: seed.groups,
    groupExpenses: seed.groupExpenses,
    settlements: seed.settlements,
    goals: seed.goals,
    recurring: seed.recurring,
    assets: seed.assets,
    liabilities: seed.liabilities,
    history: seed.history,
    notifications: seed.notifications,
    aiResponses: seed.aiResponses,
    insights: seed.insights,
    devices: seed.devices,
    recentSearches: seed.recentSearches,
    chipOrder: { expense: seed.expenseChipOrder, income: seed.incomeChipOrder },
  });
}

let state: DbState = fromSeed();
let idCounter = 1000;

export const db = {
  get(): Readonly<DbState> {
    return state;
  },
  /** Immutable update: callers return the next state. */
  update(fn: (s: DbState) => DbState): void {
    state = fn(state);
  },
  reset(): void {
    state = fromSeed();
    idCounter = 1000;
  },
  id(prefix: string): string {
    idCounter += 1;
    return `${prefix}${idCounter}`;
  },
};
