// TanStack Query hooks (spec §13, step 3). Screens only talk to these.
import { QueryClient, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  accountsRepo,
  authRepo,
  budgetRepo,
  goalsRepo,
  notificationsRepo,
  profileRepo,
  readRepo,
  splitsRepo,
  transactionsRepo,
} from '@/data/repositories';
import type { MonthKey } from '@/types/domain';
import { qk, type QueryKeyName } from './keys';

export { qk } from './keys';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { staleTime: 60_000, retry: 1 },
      mutations: { retry: 0 },
    },
  });
}

// ---------------------------------------------------------------- reads

export const useUser = () => useQuery({ queryKey: qk.user, queryFn: readRepo.user });
export const useAccounts = () => useQuery({ queryKey: qk.accounts, queryFn: readRepo.accounts });
export const useCategories = () => useQuery({ queryKey: qk.categories, queryFn: readRepo.categories });
export const useTransactions = () => useQuery({ queryKey: qk.transactions, queryFn: readRepo.transactions });
export const useBudgets = () => useQuery({ queryKey: qk.budgets, queryFn: readRepo.budgets });
export const usePeople = () => useQuery({ queryKey: qk.people, queryFn: readRepo.people });
export const useGroups = () => useQuery({ queryKey: qk.groups, queryFn: readRepo.groups });
export const useGroupExpenses = () =>
  useQuery({ queryKey: qk.groupExpenses, queryFn: readRepo.groupExpenses });
export const useSettlements = () => useQuery({ queryKey: qk.settlements, queryFn: readRepo.settlements });
export const useGoals = () => useQuery({ queryKey: qk.goals, queryFn: readRepo.goals });
export const useRecurring = () => useQuery({ queryKey: qk.recurring, queryFn: readRepo.recurring });
export const useAssets = () => useQuery({ queryKey: qk.assets, queryFn: readRepo.assets });
export const useLiabilities = () => useQuery({ queryKey: qk.liabilities, queryFn: readRepo.liabilities });
export const useNotifications = () =>
  useQuery({ queryKey: qk.notifications, queryFn: readRepo.notifications });
export const useAIResponses = () => useQuery({ queryKey: qk.aiResponses, queryFn: readRepo.aiResponses });
export const useInsights = () => useQuery({ queryKey: qk.insights, queryFn: readRepo.insights });
export const useDevices = () => useQuery({ queryKey: qk.devices, queryFn: readRepo.devices });
export const useRecentSearches = () =>
  useQuery({ queryKey: qk.recentSearches, queryFn: readRepo.recentSearches });
/** Entry-screen chip order; static for the session. */
export const useChipOrder = () =>
  useQuery({ queryKey: qk.chipOrder, queryFn: readRepo.chipOrder, staleTime: Infinity });

/** Closed-month history for Reports; fails when offline (OfflineError state). */
export function useHistory() {
  return useQuery({ queryKey: qk.history, queryFn: readRepo.history, retry: 0 });
}

// ---------------------------------------------------------------- invalidation (spec §13, step 4)

function useInvalidate() {
  const qc = useQueryClient();
  return (...keys: QueryKeyName[]) => Promise.all(keys.map((k) => qc.invalidateQueries({ queryKey: qk[k] })));
}

const MONEY: QueryKeyName[] = ['transactions', 'accounts'];

export function useAddExpense() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: transactionsRepo.addExpense, onSuccess: () => inv(...MONEY) });
}
export function useAddIncome() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: transactionsRepo.addIncome, onSuccess: () => inv(...MONEY) });
}
export function useAddTransfer() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: transactionsRepo.addTransfer, onSuccess: () => inv(...MONEY) });
}
export function useUpdateTransaction() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (v: { id: string; patch: Parameters<typeof transactionsRepo.update>[1] }) =>
      transactionsRepo.update(v.id, v.patch),
    onSuccess: () => inv(...MONEY),
  });
}
export function useDeleteTransaction() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: transactionsRepo.remove, onSuccess: () => inv(...MONEY) });
}
export function useRestoreTransaction() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: transactionsRepo.restore, onSuccess: () => inv(...MONEY) });
}
export function useAddRecentSearch() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: transactionsRepo.addRecentSearch,
    onSuccess: () => inv('recentSearches'),
  });
}

export function useUpsertAccount() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: accountsRepo.upsert, onSuccess: () => inv('accounts') });
}
export function useArchiveAccount() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: accountsRepo.archive, onSuccess: () => inv('accounts') });
}

export function useSetCategoryBudget(month: MonthKey) {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (c: Parameters<typeof budgetRepo.setCategory>[1]) => budgetRepo.setCategory(month, c),
    onSuccess: () => inv('budgets'),
  });
}
export function useRemoveCategoryBudget(month: MonthKey) {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (id: string) => budgetRepo.removeCategory(month, id),
    onSuccess: () => inv('budgets'),
  });
}
export function useReplaceBudget(month: MonthKey) {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (cats: Parameters<typeof budgetRepo.replace>[1]) => budgetRepo.replace(month, cats),
    onSuccess: () => inv('budgets'),
  });
}

export function useAddGroupExpense() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: splitsRepo.addExpense, onSuccess: () => inv('groupExpenses', ...MONEY) });
}
export function useRemoveGroupExpense() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: splitsRepo.removeExpense,
    onSuccess: () => inv('groupExpenses', ...MONEY),
  });
}
export function useSettle() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: splitsRepo.settle, onSuccess: () => inv('settlements') });
}
export function useUndoSettlement() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: splitsRepo.undoSettlement, onSuccess: () => inv('settlements') });
}

export function useAddToGoal() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (v: { goalId: string; amount: number; accountId: string }) =>
      goalsRepo.addContribution(v.goalId, v.amount, v.accountId),
    onSuccess: () => inv('goals'),
  });
}
export function useRemoveGoalContribution() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (v: { goalId: string; contributionId: string }) =>
      goalsRepo.removeContribution(v.goalId, v.contributionId),
    onSuccess: () => inv('goals'),
  });
}

export function useUpdateProfile() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: profileRepo.update, onSuccess: () => inv('user') });
}
export function useMarkAllRead() {
  const inv = useInvalidate();
  return useMutation({ mutationFn: notificationsRepo.markAllRead, onSuccess: () => inv('notifications') });
}

export function useSignIn() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (v: { email: string; password: string }) => authRepo.signIn(v.email, v.password),
    onSuccess: () => inv('user'),
  });
}
export function useSignUp() {
  const inv = useInvalidate();
  return useMutation({
    mutationFn: (v: { name: string; email: string; password: string }) =>
      authRepo.signUp(v.name, v.email, v.password),
    onSuccess: () => inv('user'),
  });
}
export function useRequestReset() {
  return useMutation({ mutationFn: (email: string) => authRepo.requestReset(email) });
}
