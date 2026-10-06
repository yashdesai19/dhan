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
import { useAddHolding } from '@/data/queries';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { groupIN } from '@/utils/format';

const KINDS = [
  { value: 'mutual_fund', label: 'Investments', loan: false, placeholder: 'Mutual funds' },
  { value: 'epf', label: 'EPF', loan: false, placeholder: 'EPF' },
  { value: 'gold', label: 'Gold', loan: false, placeholder: 'Gold' },
  { value: 'personal_loan', label: 'Personal loan', loan: true, placeholder: 'Personal loan' },
  { value: 'auto_loan', label: 'Vehicle loan', loan: true, placeholder: 'Bike loan' },
  { value: 'mortgage', label: 'Home loan', loan: true, placeholder: 'Home loan' },
  { value: 'student_loan', label: 'Education loan', loan: true, placeholder: 'Education loan' },
] as const;
type Kind = (typeof KINDS)[number]['value'];

/** Adds something you own (investments, EPF, gold) or owe (a loan) to net worth. */
export function NewHoldingScreen() {
  const router = useRouter();
  const add = useAddHolding();
  const show = useToastStore((s) => s.show);
  const [type, setType] = useState<Kind>('mutual_fund');
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const kind = KINDS.find((k) => k.value === type)!;
  const rupees = Number(value.replace(/[^\d]/g, '') || '0');

  const save = () => {
    setError(null);
    add.mutate(
      { name: name.trim() || kind.placeholder, value: rupees, type },
      {
        onSuccess: () => {
          router.back();
          show({ message: `${name.trim() || kind.placeholder} added`, placement: 'bottom' });
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
            label={kind.loan ? 'Add loan' : 'Add asset'}
            onPress={save}
            loading={add.isPending}
            disabled={rupees === 0}
          />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title="Add to net worth" />
      <View style={styles.gap10}>
        <SectionLabel>What is it?</SectionLabel>
        <ChipGroup
          options={KINDS.map((k) => ({ value: k.value, label: k.label }))}
          selected={[type]}
          onChange={([v]) => v && setType(v)}
        />
      </View>
      <TextField label="Name" value={name} onChangeText={setName} placeholder={kind.placeholder} />
      <TextField
        label={kind.loan ? 'Amount still owed' : 'Current value'}
        value={value}
        onChangeText={(v) =>
          setValue(v.replace(/[^\d]/g, '') ? `₹${groupIN(Number(v.replace(/[^\d]/g, '')))}` : '')
        }
        keyboardType="number-pad"
        placeholder="₹0"
      />
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({ gap10: { gap: space[10] } });
