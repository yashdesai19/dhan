import { useMemo } from 'react';

import { useAccounts, useCategories, useTransactions } from '@/data/queries';
import { today } from '@/mock/clock';
import type { Account, Category, ID } from '@/types/domain';
import { monthOf } from '@/utils/dates';

export function useToday(): { today: string; month: string } {
  const t = today();
  return { today: t, month: monthOf(t) };
}

/** Accounts, categories and transactions — the base data most money screens read together. */
export function useMoneyData() {
  const accounts = useAccounts();
  const categories = useCategories();
  const transactions = useTransactions();
  const loading = accounts.isPending || categories.isPending || transactions.isPending;
  const error = accounts.error ?? categories.error ?? transactions.error;
  return {
    accounts: accounts.data ?? [],
    categories: categories.data ?? [],
    transactions: transactions.data ?? [],
    loading,
    error,
    refetch: () => Promise.all([accounts.refetch(), categories.refetch(), transactions.refetch()]),
    refreshing: accounts.isRefetching || transactions.isRefetching,
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
