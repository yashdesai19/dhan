// Imperative actions used by toast Undo buttons. A toast outlives the screen that created it,
// so these call the repository and invalidate through the QueryClient instead of a hook.
import type { QueryClient } from '@tanstack/react-query';

import { accountsRepo, goalsRepo, splitsRepo, transactionsRepo } from '@/data/repositories';
import type { Account, ID, Transaction } from '@/types/domain';
import { qk, type QueryKeyName } from './keys';

const refresh = (qc: QueryClient, ...keys: QueryKeyName[]) =>
  Promise.all(keys.map((k) => qc.invalidateQueries({ queryKey: qk[k] })));

export const undo = {
  /** Remove a just-saved expense, income or transfer. */
  createdTransaction: async (qc: QueryClient, id: ID) => {
    await transactionsRepo.remove(id);
    await refresh(qc, 'transactions', 'accounts');
  },
  /** Put back a deleted transaction with its original id. */
  deletedTransaction: async (qc: QueryClient, t: Transaction) => {
    await transactionsRepo.restore(t);
    await refresh(qc, 'transactions', 'accounts');
  },
  groupExpense: async (qc: QueryClient, id: ID) => {
    await splitsRepo.removeExpense(id);
    await refresh(qc, 'groupExpenses', 'transactions', 'accounts');
  },
  settlement: async (qc: QueryClient, id: ID) => {
    await splitsRepo.undoSettlement(id);
    await refresh(qc, 'settlements');
  },
  archivedAccount: async (qc: QueryClient, a: Account) => {
    await accountsRepo.upsert(a);
    await refresh(qc, 'accounts');
  },
  goalContribution: async (qc: QueryClient, goalId: ID, contributionId: ID) => {
    await goalsRepo.removeContribution(goalId, contributionId);
    await refresh(qc, 'goals');
  },
};
