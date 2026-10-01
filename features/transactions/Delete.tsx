import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import { ConfirmSheet, Sheet, useSheet } from '@/components';
import { useDeleteTransaction } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useReturnTo } from '@/features/shared/nav';
import { useToastStore } from '@/store/ui';
import { weekdayDayMonth } from '@/utils/dates';
import { inr } from '@/utils/format';
import { categoryTotals } from '@/utils/summary';

function Body() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { month } = useToday();
  const money = useMoneyData();
  const del = useDeleteTransaction();
  const show = useToastStore((s) => s.show);
  const returnTo = useReturnTo();
  const qc = useQueryClient();
  const { close } = useSheet();
  const t = money.transactions.find((x) => x.id === id);
  if (!t) return null;
  const cat = money.categories.find((c) => c.id === t.categoryId);
  const kind = t.type === 'income' ? 'income' : 'expense';
  const after =
    t.type === 'expense' && t.categoryId
      ? (categoryTotals(money.transactions, month)[t.categoryId] ?? 0) - t.amount
      : null;
  const body =
    `${t.title} · ${inr(t.amount)} · ${weekdayDayMonth(t.date)}.` +
    (after !== null && cat ? ` Your ${cat.short} spending goes back to ${inr(after)} this month.` : '');

  return (
    <ConfirmSheet
      icon="trash"
      title={`Delete this ${kind}?`}
      body={body}
      confirmLabel={`Delete ${kind}`}
      cancelLabel="Keep it"
      loading={del.isPending}
      onConfirm={() =>
        del.mutate(t.id, {
          onSuccess: (removed) => {
            close(() => {
              returnTo('/activity');
              show({
                message: `${kind === 'income' ? 'Income' : 'Expense'} deleted`,
                actionLabel: 'Undo',
                onAction: () => {
                  void undo
                    .deletedTransaction(qc, removed)
                    .then(() => router.push(`/transactions/${removed.id}`));
                },
              });
            });
          },
        })
      }
    />
  );
}

export function DeleteTransactionSheet() {
  return (
    <Sheet label="Delete confirmation">
      <Body />
    </Sheet>
  );
}
