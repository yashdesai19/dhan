import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Banner,
  Button,
  ListCard,
  ListRow,
  Screen,
  SectionLabel,
  StickyFooter,
  TextField,
  Toggle,
  TopBar,
} from '@/components';
import { useUpsertAccount } from '@/data/queries';
import { useMoneyData } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import type { AccountType } from '@/types/domain';
import { groupIN } from '@/utils/format';
import { AccountTypeGrid } from './AccountTypeGrid';

const SUBTITLE: Record<AccountType, string> = {
  bank: 'Savings',
  savings: 'Savings',
  cash: 'In hand',
  wallet: 'Wallet',
  credit: 'Credit card',
  custom: 'Custom',
};

export function EditAccountScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { accounts } = useMoneyData();
  const upsert = useUpsertAccount();
  const show = useToastStore((s) => s.show);
  const existing = accounts.find((a) => a.id === id);
  const [type, setType] = useState<AccountType>(existing?.type ?? 'bank');
  const [name, setName] = useState(existing?.name ?? '');
  const [balance, setBalance] = useState(existing ? `₹${groupIN(existing.balance)}` : '');
  const [last4, setLast4] = useState(existing?.last4 ?? '');
  const [include, setInclude] = useState(existing?.includeInTotal ?? true);
  const [error, setError] = useState<string | null>(null);

  const save = () => {
    setError(null);
    const digits = balance.replace(/[^\d]/g, '');
    const value =
      (existing?.balance ?? 0) < 0 && type === 'credit' ? -Number(digits || '0') : Number(digits || '0');
    upsert.mutate(
      {
        ...existing,
        id: existing?.id,
        name,
        type,
        subtitle: existing?.subtitle ?? SUBTITLE[type],
        balance: type === 'credit' ? -Math.abs(value) : value,
        last4: last4 || undefined,
        includeInTotal: include,
      },
      {
        onSuccess: (a) => {
          router.back();
          show({ message: existing ? 'Account updated' : `${a.name} added`, placement: 'bottom' });
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
            label={existing ? 'Save account' : 'Add account'}
            onPress={save}
            loading={upsert.isPending}
            disabled={!name.trim()}
          />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title={existing ? 'Edit account' : 'New account'} />
      <View style={styles.gap10}>
        <SectionLabel>Type</SectionLabel>
        <AccountTypeGrid value={type} onChange={setType} />
      </View>
      <TextField
        label="Account name"
        value={name}
        onChangeText={setName}
        placeholder="HDFC Bank"
        error={error}
      />
      <TextField
        label={type === 'credit' ? 'Amount you owe' : 'Current balance'}
        value={balance}
        onChangeText={(v) =>
          setBalance(v.replace(/[^\d]/g, '') ? `₹${groupIN(Number(v.replace(/[^\d]/g, '')))}` : '')
        }
        keyboardType="number-pad"
        placeholder="₹0"
      />
      <TextField
        label="Last 4 digits (optional)"
        value={last4}
        onChangeText={(v) => setLast4(v.replace(/[^\d]/g, '').slice(0, 4))}
        keyboardType="number-pad"
        hint="Helps you tell similar accounts apart."
      />
      <ListCard>
        <ListRow
          title="Include in total balance"
          subtitle="Turn off for money you don’t spend, like a PPF."
          trailing={
            <Toggle value={include} onChange={setInclude} accessibilityLabel="Include in total balance" />
          }
          pad={14}
        />
      </ListCard>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({ gap10: { gap: space[10] } });
