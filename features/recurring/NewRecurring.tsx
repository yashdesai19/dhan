import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  Button,
  ChipGroup,
  Screen,
  SectionLabel,
  StickyFooter,
  TextField,
  TopBar,
} from '@/components';
import { nextDueDate } from '@/data/api/mappers';
import { useAccounts, useCreateRecurring } from '@/data/queries';
import { useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import type { RecurringKind } from '@/types/domain';
import { dayMonth } from '@/utils/dates';
import { groupIN } from '@/utils/format';

const KINDS: { value: RecurringKind; label: string }[] = [
  { value: 'bill', label: 'Bill' },
  { value: 'subscription', label: 'Subscription' },
  { value: 'emi', label: 'EMI' },
  { value: 'income', label: 'Income' },
];

export function NewRecurringScreen() {
  const router = useRouter();
  const { today } = useToday();
  const accounts = (useAccounts().data ?? []).filter((a) => !a.archived);
  const create = useCreateRecurring();
  const show = useToastStore((s) => s.show);
  const [name, setName] = useState('');
  const [amount, setAmount] = useState('');
  const [kind, setKind] = useState<RecurringKind>('bill');
  const [chosenAccount, setAccount] = useState('');
  const [day, setDay] = useState(String(Number(today.slice(8, 10))));
  const [error, setError] = useState<string | null>(null);

  const accountId = accounts.some((a) => a.id === chosenAccount) ? chosenAccount : (accounts[0]?.id ?? '');
  const dayNum = Number(day);
  const validDay = Number.isInteger(dayNum) && dayNum >= 1 && dayNum <= 31;
  const rupees = Number(amount.replace(/[^\d]/g, '') || '0');
  const nextDate = validDay ? nextDueDate(dayNum, today) : today;

  const save = () => {
    setError(null);
    if (!accountId) {
      setError('Please add an account in Accounts first.');
      return;
    }
    create.mutate(
      { name, kind, amount: rupees, accountId, nextDate },
      {
        onSuccess: () => {
          router.back();
          show({ message: `${name.trim()} added · next on ${dayMonth(nextDate)}`, placement: 'bottom' });
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
          <Button
            label={kind === 'income' ? 'Add recurring income' : 'Add recurring payment'}
            onPress={save}
            loading={create.isPending}
            disabled={!name.trim() || rupees === 0 || !validDay}
          />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title="New recurring" />
      <View style={styles.gap10}>
        <SectionLabel>Kind</SectionLabel>
        <ChipGroup options={KINDS} selected={[kind]} onChange={([v]) => v && setKind(v)} />
      </View>
      <TextField
        label="Name"
        value={name}
        onChangeText={setName}
        placeholder={kind === 'income' ? 'Salary' : 'Electricity bill'}
      />
      <TextField
        label="Amount each month"
        value={amount}
        onChangeText={(v) =>
          setAmount(v.replace(/[^\d]/g, '') ? `₹${groupIN(Number(v.replace(/[^\d]/g, '')))}` : '')
        }
        keyboardType="number-pad"
        placeholder="₹0"
      />
      <TextField
        label="Day of the month"
        value={day}
        onChangeText={(v) => setDay(v.replace(/[^\d]/g, '').slice(0, 2))}
        keyboardType="number-pad"
        placeholder="1"
        hint={validDay ? `Next on ${dayMonth(nextDate)}` : 'Pick a day from 1 to 31.'}
      />
      {accounts.length > 1 ? (
        <View style={styles.gap10}>
          <SectionLabel>{kind === 'income' ? 'Into' : 'From'}</SectionLabel>
          <ChipGroup
            options={accounts.map((a) => ({ value: a.id, label: a.name }))}
            selected={[accountId]}
            onChange={([v]) => v && setAccount(v)}
          />
        </View>
      ) : null}
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({ gap10: { gap: space[10] } });
