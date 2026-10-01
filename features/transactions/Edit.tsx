import { useEffect, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Banner,
  Button,
  ChipGroup,
  ListCard,
  Screen,
  SectionLabel,
  SelectRow,
  StickyFooter,
  Text,
  TextButton,
  TextField,
  TopBar,
} from '@/components';
import { useChipOrder, useUpdateTransaction } from '@/data/queries';
import { nextAccount } from '@/features/entry/EntryParts';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { fonts, moneySizes, size, space, useColors } from '@/theme';
import type { Transaction } from '@/types/domain';
import { addDays, time12, weekdayDayMonth } from '@/utils/dates';
import { groupIN } from '@/utils/format';

export function EditTransactionScreen() {
  const c = useColors();
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { today } = useToday();
  const money = useMoneyData();
  const chipOrder = useChipOrder().data;
  const update = useUpdateTransaction();
  const show = useToastStore((s) => s.show);
  const t = money.transactions.find((x) => x.id === id);
  const [form, setForm] = useState<Transaction | null>(t ?? null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (t && !form) setForm(t);
  }, [t, form]);

  if (!form)
    return (
      <Screen>
        <TopBar variant="modal" title="Edit" />
      </Screen>
    );

  const patch = (p: Partial<Transaction>) => setForm({ ...form, ...p });
  const order = form.type === 'income' ? (chipOrder?.income ?? []) : (chipOrder?.expense ?? []);
  const options = order
    .map((cid) => money.categories.find((x) => x.id === cid))
    .filter((x): x is NonNullable<typeof x> => !!x)
    .map((x) => ({ value: x.id, label: x.short }));
  const acct = money.accounts.find((a) => a.id === form.accountId);

  const save = () => {
    setError(null);
    if (!(form.amount > 0)) return setError('Enter an amount.');
    update.mutate(
      {
        id: form.id,
        patch: {
          amount: form.amount,
          title: form.title.trim() || form.title,
          categoryId: form.categoryId,
          accountId: form.accountId,
          date: form.date,
          note: form.note,
          repeats: form.repeats,
        },
      },
      {
        onSuccess: () => {
          router.back();
          show({ message: 'Changes saved', placement: 'bottom' });
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  return (
    <Screen
      bottom="footer"
      gap={space[20]}
      keyboard
      overlay={
        <StickyFooter>
          <Button label="Save changes" onPress={save} loading={update.isPending} />
        </StickyFooter>
      }
    >
      <TopBar
        variant="modal"
        title={form.type === 'income' ? 'Edit income' : 'Edit expense'}
        backLabel="Cancel"
        trailing={<TextButton label="Save" onPress={save} />}
      />
      <View style={styles.amount}>
        <Text variant="meta" color="muted">
          Amount
        </Text>
        <View style={styles.amountRow}>
          <Text maxScale={1.3} style={{ fontFamily: fonts.serif, fontSize: moneySizes.xs, color: c.faint }}>
            ₹
          </Text>
          <TextInput
            accessibilityLabel="Amount"
            value={form.amount ? groupIN(form.amount) : ''}
            onChangeText={(v) => patch({ amount: Number(v.replace(/[^\d]/g, '').slice(0, 9) || '0') })}
            keyboardType="number-pad"
            placeholder="0"
            placeholderTextColor={c.faint}
            selectionColor={c.primary}
            style={[styles.amountInput, { color: c.ink }]}
          />
        </View>
      </View>
      <TextField
        label={form.type === 'income' ? 'Source' : 'Merchant'}
        value={form.title}
        onChangeText={(title) => patch({ title })}
      />
      <View style={styles.gap10}>
        <SectionLabel>{form.type === 'income' ? 'Income source' : 'Category'}</SectionLabel>
        <ChipGroup
          wrap={false}
          options={options}
          selected={form.categoryId ? [form.categoryId] : []}
          onChange={([v]) => v && patch({ categoryId: v })}
        />
      </View>
      <ListCard>
        <SelectRow
          label="Account"
          value={acct?.name ?? ''}
          icon="bank"
          onPress={() =>
            patch({ accountId: nextAccount(money.accounts, form.accountId ?? '')?.id ?? form.accountId })
          }
        />
        <SelectRow
          label="Date"
          value={`${weekdayDayMonth(form.date)}${form.time && form.date === t?.date ? `, ${time12(form.time)}` : ''}`}
          icon="calendar"
          onPress={() => patch({ date: form.date === today ? addDays(today, -1) : today })}
        />
        <SelectRow
          label="Repeats"
          value={form.repeats === 'monthly' ? 'Monthly' : 'Never'}
          icon="repeat"
          onPress={() => patch({ repeats: form.repeats === 'monthly' ? 'never' : 'monthly' })}
        />
      </ListCard>
      <TextField
        label="Note"
        value={form.note ?? ''}
        onChangeText={(note) => patch({ note })}
        placeholder="Add a note"
      />
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  amount: { alignItems: 'center', gap: space[6], paddingVertical: space[8] },
  amountRow: { flexDirection: 'row', alignItems: 'flex-end', gap: space[4] },
  amountInput: {
    fontFamily: fonts.serif,
    fontSize: moneySizes.lg,
    minWidth: 80,
    padding: 0,
    minHeight: size.touch,
    textAlign: 'center',
  },
  gap10: { gap: space[10] },
});
