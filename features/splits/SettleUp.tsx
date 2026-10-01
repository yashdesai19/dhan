import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';

import {
  Avatar,
  Banner,
  Button,
  ChipGroup,
  Icon,
  Money,
  SectionLabel,
  Sheet,
  Text,
  TextButton,
  TextField,
  useSheet,
} from '@/components';
import { useSettle } from '@/data/queries';
import { iconSize, space } from '@/theme';
import type { SettlementMethod } from '@/types/domain';
import { groupIN, inr } from '@/utils/format';
import { ME, useSplits } from './useSplits';

const METHODS: { value: SettlementMethod; label: string }[] = [
  { value: 'upi', label: 'UPI' },
  { value: 'cash', label: 'Cash' },
  { value: 'bank', label: 'Bank transfer' },
];

function Body() {
  const { personId } = useLocalSearchParams<{ personId: string }>();
  const { close } = useSheet();
  const s = useSplits();
  const settle = useSettle();
  const p = s.person(personId ?? '');
  const balance = s.overall.byPerson[personId ?? ''] ?? 0;
  const pay = balance < 0;
  const full = Math.abs(balance);
  const [partial, setPartial] = useState<number | null>(null);
  const [method, setMethod] = useState<SettlementMethod>('upi');
  const amount = partial ?? full;
  const me = s.person(ME);

  return (
    <>
      <View style={styles.people} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        <Avatar
          initials={pay ? me.initials : p.initials}
          tone={pay ? me.avatarTone : p.avatarTone}
          size="hero"
        />
        <Icon name="transfer" size={iconSize.xxl} color="muted" />
        <Avatar
          initials={pay ? p.initials : me.initials}
          tone={pay ? p.avatarTone : me.avatarTone}
          size="hero"
        />
      </View>
      <View style={styles.center}>
        <Text variant="body" color="muted">
          {pay ? `You pay ${p.name}` : `${p.name} pays you`}
        </Text>
        <Money amount={amount} size="hero" />
        {partial === null ? (
          <TextButton label="Pay part of it" size="sm" onPress={() => setPartial(full)} />
        ) : (
          <View style={styles.partial}>
            <TextField
              label="Amount"
              value={amount ? `₹${groupIN(amount)}` : ''}
              onChangeText={(v) => setPartial(Math.min(full, Number(v.replace(/[^\d]/g, '') || '0')))}
              keyboardType="number-pad"
              hint={`Up to ${inr(full)}`}
              autoFocus
            />
          </View>
        )}
      </View>
      <View style={styles.gap10}>
        <SectionLabel>Paid with</SectionLabel>
        <ChipGroup options={METHODS} selected={[method]} onChange={([v]) => v && setMethod(v)} />
      </View>
      <Banner icon="info" tone="neutral">
        DHAN records this payment. It doesn’t move any money.
      </Banner>
      <Button
        label={`Record ${inr(amount)} payment`}
        disabled={amount <= 0}
        loading={settle.isPending}
        onPress={() =>
          settle.mutate(
            { withId: p.id, amount, method, direction: pay ? 'pay' : 'receive' },
            {
              onSuccess: (st) =>
                close(() =>
                  router.push({
                    pathname: '/splits/settled',
                    params: {
                      personId: p.id,
                      amount: String(st.amount),
                      method: st.method,
                      settlementId: st.id,
                    },
                  }),
                ),
            },
          )
        }
      />
    </>
  );
}

export function SettleUpSheet() {
  return (
    <Sheet title="Settle up" label="Settle up">
      <Body />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  people: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space[14],
    paddingVertical: space[6],
  },
  center: { alignItems: 'center', gap: space[6] },
  partial: { alignSelf: 'stretch' },
  gap10: { gap: space[10] },
});
