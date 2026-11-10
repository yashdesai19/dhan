import { useMemo } from 'react';

import { useAccounts, useBooks, useCategories, useHistory, useTransactions } from '@/data/queries';
import { today } from '@/mock/clock';
import { usePrefsStore } from '@/store/prefs';
import type { Account, Book, Category, ID } from '@/types/domain';
import { ALL_BOOKS_ID, PERSONAL_BOOK, PERSONAL_BOOK_ID, bookHistory, scopeToBook } from '@/utils/books';
import { monthOf } from '@/utils/dates';

export function useToday(): { today: string; month: string } {
  const t = today();
  return { today: t, month: monthOf(t) };
}

/** The book the app is showing. A saved id that no longer exists falls back to Personal. */
export function useActiveBook() {
  const saved = usePrefsStore((s) => s.activeBookId);
  const business = useBooks().data;
  return useMemo(() => {
    const books: Book[] = [PERSONAL_BOOK, ...(business ?? [])];
    const hasBusiness = books.length > 1;
    const book = books.find((b) => b.id === saved);
    const id = saved === ALL_BOOKS_ID && hasBusiness ? ALL_BOOKS_ID : (book?.id ?? PERSONAL_BOOK_ID);
    return { id, book, books, hasBusiness, isBusiness: book?.kind === 'business' };
  }, [saved, business]);
}

/** Which money a screen reads: the book on show, every book, or Personal alone (budgets). */
export type MoneyScope = 'active' | 'all' | 'personal';

/** Accounts, categories and transactions — the base data most money screens read together. */
export function useMoneyData(scope: MoneyScope = 'active') {
  const accounts = useAccounts();
  const categories = useCategories();
  const transactions = useTransactions();
  const active = useActiveBook();
  const bookId =
    scope === 'all' ? ALL_BOOKS_ID : scope === 'personal' ? PERSONAL_BOOK_ID : active.id;
  const scoped = useMemo(
    () => scopeToBook(accounts.data ?? [], transactions.data ?? [], bookId),
    [accounts.data, transactions.data, bookId],
  );
  const loading = accounts.isPending || categories.isPending || transactions.isPending;
  const error = accounts.error ?? categories.error ?? transactions.error;
  return {
    accounts: scoped.accounts,
    categories: categories.data ?? [],
    transactions: scoped.transactions,
    loading,
    error,
    refetch: () => Promise.all([accounts.refetch(), categories.refetch(), transactions.refetch()]),
    refreshing: accounts.isRefetching || transactions.isRefetching,
  };
}

/**
 * Closed months for one book. The server's history mixes every book, so once a business exists a
 * single book's history is rebuilt from its own transactions. Net worth stays zero in that case.
 */
export function useScopedHistory(scope: Exclude<MoneyScope, 'all'> = 'active') {
  const server = useHistory();
  const { hasBusiness, id } = useActiveBook();
  const { transactions } = useMoneyData(scope);
  const { month } = useToday();
  const single = hasBusiness && (scope === 'personal' || id !== ALL_BOOKS_ID);
  const data = useMemo(
    () => (single ? bookHistory(transactions, month) : server.data),
    [single, transactions, month, server.data],
  );
  return {
    data,
    isError: !single && server.isError,
    isPending: !single && server.isPending,
    isRefetching: server.isRefetching,
    refetch: server.refetch,
    /** False when this history has no net-worth figures. */
    hasNetWorth: !single,
  };
}

export function useLookup(accounts: readonly Account[], categories: readonly Category[]) {
  return useMemo(
    () => ({
      account: (id?: ID) => accounts.find((a) => a.id === id),
      category: (id?: ID) => categories.find((c) => c.id === id),
    }),
    [accounts, categories],
  );
}
