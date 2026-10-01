// Flow tests: hooks → repositories → mock DB, with query invalidation (spec §13).
import { QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';

import {
  createQueryClient,
  useAccounts,
  useAddExpense,
  useAddIncome,
  useAddTransfer,
  useDeleteTransaction,
  useTransactions,
} from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { resetMockData } from '@/data/repositories';
import { netBalance } from '@/utils/summary';

function setup() {
  const qc = createQueryClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
  return { qc, wrapper };
}

beforeEach(() => resetMockData());

it('adding an expense updates transactions and balances, and Undo reverts both', async () => {
  const { qc, wrapper } = setup();
  const { result } = renderHook(
    () => ({ accounts: useAccounts(), txs: useTransactions(), add: useAddExpense() }),
    { wrapper },
  );
  await waitFor(() => expect(result.current.accounts.data).toBeDefined());
  expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580);
  const before = result.current.txs.data?.length ?? 0;

  let createdId = '';
  await act(async () => {
    const t = await result.current.add.mutateAsync({
      amount: 450,
      title: 'Lunch',
      categoryId: 'food',
      accountId: 'hdfc',
      date: '2026-09-30',
    });
    createdId = t.id;
  });
  await waitFor(() => expect(netBalance(result.current.accounts.data ?? []).total).toBe(124130));
  expect(result.current.txs.data?.length).toBe(before + 1);

  await act(async () => {
    await undo.createdTransaction(qc, createdId);
  });
  await waitFor(() => expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580));
  expect(result.current.txs.data?.length).toBe(before);
});

it('deleting and restoring a transaction round-trips the balance', async () => {
  const { qc, wrapper } = setup();
  const { result } = renderHook(
    () => ({ accounts: useAccounts(), txs: useTransactions(), del: useDeleteTransaction() }),
    {
      wrapper,
    },
  );
  await waitFor(() => expect(result.current.txs.data).toBeDefined());
  const target = result.current.txs.data?.find((t) => t.type === 'expense');
  if (!target) throw new Error('seed has expenses');

  let removed = target;
  await act(async () => {
    removed = await result.current.del.mutateAsync(target.id);
  });
  await waitFor(() => expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580 + target.amount));
  await act(async () => {
    await undo.deletedTransaction(qc, removed);
  });
  await waitFor(() => expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580));
});

it('adding income updates account balance and transaction list', async () => {
  const { wrapper } = setup();
  const { result } = renderHook(
    () => ({ accounts: useAccounts(), txs: useTransactions(), addIncome: useAddIncome() }),
    { wrapper },
  );
  await waitFor(() => expect(result.current.accounts.data).toBeDefined());
  expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580);
  const before = result.current.txs.data?.length ?? 0;

  await act(async () => {
    await result.current.addIncome.mutateAsync({
      amount: 10000,
      title: 'Freelance',
      categoryId: 'salary',
      accountId: 'hdfc',
      date: '2026-09-30',
    });
  });
  await waitFor(() => expect(netBalance(result.current.accounts.data ?? []).total).toBe(134580));
  expect(result.current.txs.data?.length).toBe(before + 1);
});

it('transferring between accounts updates both balances without changing net total', async () => {
  const { wrapper } = setup();
  const { result } = renderHook(
    () => ({ accounts: useAccounts(), txs: useTransactions(), transfer: useAddTransfer() }),
    { wrapper },
  );
  await waitFor(() => expect(result.current.accounts.data).toBeDefined());
  expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580);
  const hdfcBefore = result.current.accounts.data?.find((a) => a.id === 'hdfc')?.balance ?? 0;
  const cashBefore = result.current.accounts.data?.find((a) => a.id === 'cash')?.balance ?? 0;

  await act(async () => {
    await result.current.transfer.mutateAsync({
      amount: 2000,
      fromId: 'hdfc',
      toId: 'cash',
      date: '2026-09-30',
    });
  });
  await waitFor(() => {
    const hdfc = result.current.accounts.data?.find((a) => a.id === 'hdfc')?.balance;
    const cash = result.current.accounts.data?.find((a) => a.id === 'cash')?.balance;
    expect(hdfc).toBe(hdfcBefore - 2000);
    expect(cash).toBe(cashBefore + 2000);
  });
  expect(netBalance(result.current.accounts.data ?? []).total).toBe(124580);
});

