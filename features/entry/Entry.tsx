// Add expense and Add income: the fastest flows in the app (spec §14).
import { useState, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useQueryClient } from '@tanstack/react-query';

import {
  AmountDisplay,
  Banner,
  Button,
  ChipGroup,
  Keypad,
  TextButton,
  TextField,
  type KeypadKey,
} from '@/components';
import { useAddExpense, useAddIncome, useChipOrder } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useReturnTo } from '@/features/shared/nav';
import { amountValue, pressKey, useEntryDraftStore } from '@/store/drafts';
import { useHighlightStore, useToastStore } from '@/store/ui';
import { layout, space, useColors } from '@/theme';
import { addDays } from '@/utils/dates';
import { formatAmountInput, inr } from '@/utils/format';
import { dateLabel, EntryHeader, EntryPill, nextAccount, useValidDraftIds } from './EntryParts';

function useEntry(kind: 'expense' | 'income') {
  const { today } = useToday();
  const { accounts, categories, loading } = useMoneyData();
  const chipOrder = useChipOrder().data;
  useValidDraftIds(accounts, categories, chipOrder);
  const draft = useEntryDraftStore((s) => s.draft);
  const patch = useEntryDraftStore((s) => s.patch);
  const reset = useEntryDraftStore((s) => s.reset);
  const restore = useEntryDraftStore((s) => s.restore);
  const show = useToastStore((s) => s.show);
  const highlight = useHighlightStore((s) => s.set);
  const returnTo = useReturnTo();
  const qc = useQueryClient();
  const addExpense = useAddExpense();
  const addIncome = useAddIncome();
  const [error, setError] = useState<string | null>(null);

  const order = kind === 'expense' ? (chipOrder?.expense ?? []) : (chipOrder?.income ?? []);
  const options = order
    .map((id) => categories.find((c) => c.id === id))
    .filter((c): c is NonNullable<typeof c> => !!c)
    .map((c) => ({ value: c.id, label: c.short }));
  const catId = kind === 'expense' ? draft.categoryId : draft.incomeSourceId;
  const cat = categories.find((c) => c.id === catId);
  const live = accounts.filter((a) => !a.archived);
  const account = live.find((a) => a.id === draft.accountId) ?? live[0];
  const value = amountValue(draft.amount);
  const pending = addExpense.isPending || addIncome.isPending;

  const save = () => {
    setError(null);
    // Still loading: keep the draft's account rather than dropping the tap
    if (!account && !loading) {
      setError('Please add an account in Accounts first.');
      return;
    }
    const snapshot = draft;
    const input = {
      amount: value,
      categoryId: catId,
      accountId: account?.id ?? draft.accountId,
      date: draft.date,
      note: draft.note || undefined,
    };
    const onSuccess = (t: { id: string; title: string; amount: number }) => {
      reset();
      highlight(t.id);
      returnTo('/(tabs)');
      show({
        message:
          kind === 'expense'
            ? `Expense saved · ${t.title} ${inr(t.amount)}`
            : `Income added · ${t.title} ${inr(t.amount)}`,
        actionLabel: 'Undo',
        onAction: () => {
          void undo.createdTransaction(qc, t.id).then(() => {
            restore(snapshot);
            router.push(kind === 'expense' ? '/add/expense' : '/add/income');
          });
        },
      });
    };
    const onError = (e: Error) => setError(e.message);
    if (kind === 'expense') addExpense.mutate(input, { onSuccess, onError });
    else addIncome.mutate(input, { onSuccess, onError });
  };

  return {
    today,
    accounts,
    categories,
    draft,
    patch,
    options,
    catId,
    cat,
    account,
    value,
    save,
    pending,
    error,
  };
}

function Frame({ children }: { children: ReactNode }) {
  const c = useColors();
  const insets = useSafeAreaInsets();
  return (
    <View
      style={[
        styles.frame,
        {
          backgroundColor: c.bg,
          paddingTop: insets.top + space[8],
          paddingBottom: Math.max(insets.bottom, space[20]),
          paddingHorizontal: layout.gutter,
        },
      ]}
    >
      {children}
    </View>
  );
}

export function AddExpenseScreen() {
  const e = useEntry('expense');
  const [noteOpen, setNoteOpen] = useState(!!e.draft.note);
  const [repeat, setRepeat] = useState(false);
  const empty = e.value === 0;
  const onKey = (k: KeypadKey) => e.patch({ amount: pressKey(e.draft.amount, k) });

  return (
    <Frame>
      <EntryHeader kind="expense" />
      <View style={styles.center}>
        <AmountDisplay
          value={e.draft.amount}
          accessibilityLabel={`Amount ${formatAmountInput(e.draft.amount)} rupees`}
        />
        <View style={styles.pills}>
          <EntryPill
            icon="card"
            label={e.account?.name ?? 'Account'}
            chevron
            accessibilityHint="Switches to your next account"
            onPress={() => {
              const live = e.accounts.filter((a) => !a.archived);
              if (live.length === 0) {
                router.push('/accounts/edit');
                return;
              }
              const n = nextAccount(e.accounts, e.account?.id ?? e.draft.accountId);
              if (n) e.patch({ accountId: n.id });
            }}
          />
          <EntryPill
            icon="calendar"
            label={dateLabel(e.draft.date, e.today)}
            accessibilityHint="Switches between today and yesterday"
            onPress={() =>
              e.patch({ date: e.draft.date && e.draft.date !== e.today ? undefined : addDays(e.today, -1) })
            }
          />
        </View>
      </View>
      <ChipGroup
        wrap={false}
        options={e.options}
        selected={[e.catId]}
        onChange={([v]) => v && e.patch({ categoryId: v })}
      />
      {noteOpen ? (
        <TextField
          label="Note"
          value={e.draft.note}
          onChangeText={(note) => e.patch({ note })}
          placeholder="What was it for?"
          autoFocus
        />
      ) : null}
      <View style={styles.extras}>
        <TextButton label={noteOpen ? '− Note' : '+ Note'} size="sm" onPress={() => setNoteOpen(!noteOpen)} />
        <TextButton
          label="+ Receipt"
          size="sm"
          accessibilityHint="Attaching receipts is not available in this preview"
        />
        <TextButton
          label="+ Split"
          size="sm"
          onPress={() =>
            router.replace({ pathname: '/add/split', params: { amount: String(Math.round(e.value) || '') } })
          }
        />
        <TextButton label={repeat ? '✓ Repeats' : '+ Repeat'} size="sm" onPress={() => setRepeat(!repeat)} />
      </View>
      {e.error ? (
        <Banner icon="alert" tone="error">
          {e.error}
        </Banner>
      ) : null}
      <Keypad onKey={onKey} />
      <Button
        label={
          empty ? 'Enter an amount' : `Save ₹${formatAmountInput(e.draft.amount)} · ${e.cat?.short ?? ''}`
        }
        disabled={empty}
        loading={e.pending}
        onPress={e.save}
      />
    </Frame>
  );
}

export function AddIncomeScreen() {
  const e = useEntry('income');
  const [noteOpen, setNoteOpen] = useState(!!e.draft.note);
  const [custom, setCustom] = useState<string | null>(null);
  const empty = e.value === 0;
  const onKey = (k: KeypadKey) => e.patch({ amount: pressKey(e.draft.amount, k) });

  return (
    <Frame>
      <EntryHeader kind="income" />
      <View style={styles.center}>
        <AmountDisplay
          value={e.draft.amount}
          tone="income"
          accessibilityLabel={`Amount plus ${formatAmountInput(e.draft.amount)} rupees`}
        />
        <View style={styles.pills}>
          <EntryPill
            label={`To ${e.account?.name ?? 'account'}`}
            accessibilityHint="Switches to your next account"
            onPress={() => {
              const n = nextAccount(e.accounts, e.draft.accountId);
              if (n) e.patch({ accountId: n.id });
            }}
          />
          <EntryPill
            label={dateLabel(e.draft.date, e.today)}
            onPress={() =>
              e.patch({ date: e.draft.date && e.draft.date !== e.today ? undefined : addDays(e.today, -1) })
            }
          />
          <EntryPill label={noteOpen ? '− Note' : '+ Note'} onPress={() => setNoteOpen(!noteOpen)} />
        </View>
      </View>
      <ChipGroup
        wrap={false}
        options={e.options}
        selected={[e.catId]}
        onChange={([v]) => v && e.patch({ incomeSourceId: v })}
        trailing={{ label: '+ Custom', onPress: () => setCustom(custom === null ? '' : null) }}
      />
      {custom !== null ? (
        <TextField
          label="Income source"
          value={custom}
          onChangeText={(v) => {
            setCustom(v);
            const other = e.categories.find((c) => c.kind === 'income' && /^other/i.test(c.name));
            e.patch({ incomeSourceId: other?.id ?? 'other-in', note: v });
          }}
          placeholder="For example, Rent from tenant"
          autoFocus
        />
      ) : null}
      {noteOpen ? (
        <TextField label="Note" value={e.draft.note} onChangeText={(note) => e.patch({ note })} autoFocus />
      ) : null}
      {e.error ? (
        <Banner icon="alert" tone="error">
          {e.error}
        </Banner>
      ) : null}
      <Keypad onKey={onKey} />
      <Button
        label={
          empty
            ? 'Enter an amount'
            : `Add ₹${formatAmountInput(e.draft.amount)} · ${custom?.trim() || e.cat?.short || ''}`
        }
        disabled={empty}
        loading={e.pending}
        onPress={e.save}
      />
    </Frame>
  );
}

const styles = StyleSheet.create({
  frame: { flex: 1, gap: space[14] },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: space[14], minHeight: 140 },
  pills: { flexDirection: 'row', gap: space[8], flexWrap: 'wrap', justifyContent: 'center' },
  extras: { flexDirection: 'row', gap: space[16], flexWrap: 'wrap' },
});
