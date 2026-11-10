// Books keep a business's money apart from personal money. An account with no bookId is Personal.
import type { IconName } from '@/components/icons/paths';
import type {
  Account,
  Book,
  Category,
  ID,
  MonthHistory,
  MonthKey,
  Rupees,
  Transaction,
} from '@/types/domain';
import { shiftMonth } from './dates';
import { categoryTotals, inMonth, monthTotals } from './summary';

export const PERSONAL_BOOK_ID = 'personal';
export const ALL_BOOKS_ID = 'all';
export const PERSONAL_BOOK: Book = { id: PERSONAL_BOOK_ID, name: 'Personal', kind: 'personal' };

export interface BusinessCategory {
  name: string;
  short: string;
  icon: IconName;
  kind: 'expense' | 'income';
}

/** Added when a user's first business book is created; they stay out of everyone else's lists. */
export const BUSINESS_CATEGORIES: BusinessCategory[] = [
  { name: 'Stock purchase', short: 'Stock', icon: 'bag', kind: 'expense' },
  { name: 'Shop rent', short: 'Rent', icon: 'home', kind: 'expense' },
  { name: 'Staff salary', short: 'Staff', icon: 'users', kind: 'expense' },
  { name: 'Utilities', short: 'Utilities', icon: 'bolt', kind: 'expense' },
  { name: 'Business travel', short: 'Travel', icon: 'car', kind: 'expense' },
  { name: 'Other business expense', short: 'Other', icon: 'tag', kind: 'expense' },
  { name: 'Sales', short: 'Sales', icon: 'income', kind: 'income' },
  { name: 'Services', short: 'Services', icon: 'briefcase', kind: 'income' },
  { name: 'Other business income', short: 'Other', icon: 'coin', kind: 'income' },
];

/** The entry-screen chips for a business book, as ids of the categories that exist. */
export function businessChips(categories: readonly Category[]): { expense: ID[]; income: ID[] } {
  const ids = (kind: 'expense' | 'income') =>
    BUSINESS_CATEGORIES.filter((b) => b.kind === kind)
      .map((b) => categories.find((c) => c.kind === kind && c.name === b.name)?.id)
      .filter((id): id is ID => !!id);
  return { expense: ids('expense'), income: ids('income') };
}

const bookOf = (a: Account): ID => a.bookId ?? PERSONAL_BOOK_ID;

/**
 * The accounts and transactions of one book. A transfer between books shows in both, and is never
 * income or spending, so taking money out of a business doesn't change its profit.
 */
export function scopeToBook(
  accounts: readonly Account[],
  transactions: readonly Transaction[],
  bookId: ID,
): { accounts: Account[]; transactions: Transaction[] } {
  if (bookId === ALL_BOOKS_ID) return { accounts: [...accounts], transactions: [...transactions] };
  const inBook = accounts.filter((a) => bookOf(a) === bookId);
  const ids = new Set(inBook.map((a) => a.id));
  return {
    accounts: inBook,
    transactions: transactions.filter((t) =>
      t.accountId
        ? ids.has(t.accountId) || (!!t.toAccountId && ids.has(t.toAccountId))
        : bookId === PERSONAL_BOOK_ID,
    ),
  };
}

/** Closed months rebuilt from a book's own transactions (the server's history covers all books). */
export function bookHistory(
  transactions: readonly Transaction[],
  month: MonthKey,
  count = 5,
): MonthHistory[] {
  return Array.from({ length: count }, (_, i) => shiftMonth(month, i - count)).map((m) => {
    const { income, spent } = monthTotals(transactions, m);
    return { month: m, income, spent, byCategory: categoryTotals(transactions, m), netWorth: 0 };
  });
}

export interface ProfitLine {
  id: ID;
  label: string;
  amount: Rupees;
}

export interface ProfitAndLoss {
  income: ProfitLine[];
  expenses: ProfitLine[];
  totalIncome: Rupees;
  totalExpenses: Rupees;
  profit: Rupees;
  /** Profit as a share of income, whole percent; 0 with no income. */
  margin: number;
}

export function profitAndLoss(
  transactions: readonly Transaction[],
  month: MonthKey,
  categories: readonly Category[],
): ProfitAndLoss {
  const lines = (type: 'income' | 'expense'): ProfitLine[] => {
    const totals = new Map<ID, Rupees>();
    for (const t of inMonth(transactions, month)) {
      if (t.type !== type) continue;
      const id = t.categoryId ?? 'uncategorised';
      totals.set(id, (totals.get(id) ?? 0) + t.amount);
    }
    return [...totals]
      .map(([id, amount]) => ({
        id,
        amount,
        label: categories.find((c) => c.id === id)?.short ?? 'Uncategorised',
      }))
      .sort((a, b) => b.amount - a.amount);
  };
  const income = lines('income');
  const expenses = lines('expense');
  const sum = (xs: ProfitLine[]) => xs.reduce((s, x) => s + x.amount, 0);
  const totalIncome = sum(income);
  const totalExpenses = sum(expenses);
  const profit = totalIncome - totalExpenses;
  return {
    income,
    expenses,
    totalIncome,
    totalExpenses,
    profit,
    margin: totalIncome === 0 ? 0 : Math.round((profit / totalIncome) * 100),
  };
}
