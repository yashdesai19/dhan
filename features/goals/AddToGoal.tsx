import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import {
  Button,
  Card,
  ChipGroup,
  ListCard,
  Money,
  ProgressBar,
  SelectRow,
  Sheet,
  Text,
  TextField,
  useSheet,
} from '@/components';
import { useAccounts, useAddToGoal, useGoals } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { nextAccount } from '@/features/entry/EntryParts';
import { useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { groupIN, inr, percent } from '@/utils/format';
import { goalProgress } from '@/utils/goals';

function Body() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { today } = useToday();
  const { close } = useSheet();
  const qc = useQueryClient();
  const goals = useGoals();
  const accounts = useAccounts().data ?? [];
  const add = useAddToGoal();
  const show = useToastStore((s) => s.show);
  const g = goals.data?.find((x) => x.id === id);
  const p = g ? goalProgress(g, today) : null;
  const suggested = p?.monthly ?? 0;
  const [amount, setAmount] = useState(suggested);
  const [custom, setCustom] = useState(false);
  const [chosenId, setAccountId] = useState('hdfc');
  // 'hdfc' is the demo's default; on real data fall back to the user's first active account
  const live = accounts.filter((a) => !a.archived);
  const accountId = live.some((a) => a.id === chosenId) ? chosenId : (live[0]?.id ?? chosenId);
  if (!g || !p) return null;

  const presets = Array.from(new Set([5000, 10000, suggested].filter((v) => v > 0))).sort((a, b) => a - b);
  const after = p.saved + amount;
  const acct = accounts.find((a) => a.id === accountId);

  return (
    <>
      <View style={styles.center}>
        <Money amount={amount} size="lg" />
      </View>
      <ChipGroup
        options={[
          ...presets.map((v) => ({ value: String(v), label: inr(v) })),
          { value: 'custom', label: 'Custom' },
        ]}
        selected={[custom ? 'custom' : String(amount)]}
        onChange={([v]) => {
          if (v === 'custom') setCustom(true);
          else if (v) {
            setCustom(false);
            setAmount(Number(v));
          }
        }}
      />
      {custom ? (
        <TextField
          label="Amount"
          value={amount ? `₹${groupIN(amount)}` : ''}
          onChangeText={(v) => setAmount(Number(v.replace(/[^\d]/g, '') || '0'))}
          keyboardType="number-pad"
          autoFocus
        />
      ) : null}
      <ListCard>
        <SelectRow
          label="From"
          value={acct?.name ?? ''}
          icon="bank"
          onPress={() => setAccountId(nextAccount(accounts, accountId)?.id ?? accountId)}
        />
      </ListCard>
      <Card gap={space[10]}>
        <View style={styles.between}>
          <Text variant="small">After this</Text>
          <Text variant="small" tabular>
            <Text variant="small" weight="semibold">
              {inr(after)}
            </Text>
            <Text variant="small" color="muted">{` / ${inr(g.target)}`}</Text>
          </Text>
        </View>
        <ProgressBar value={percent(after, g.target)} height={8} />
      </Card>
      <Button
        label={`Add ${inr(amount)}`}
        disabled={amount <= 0}
        loading={add.isPending}
        onPress={() =>
          add.mutate(
            { goalId: g.id, amount, accountId },
            {
              onSuccess: (c) =>
                close(() =>
                  show({
                    message: `${inr(c.amount)} added to ${g.name}`,
                    actionLabel: 'Undo',
                    placement: 'footer',
                    onAction: () =>
                      void undo
                        .goalContribution(qc, g.id, c.id)
                        .then(() => router.push(`/goals/${g.id}/add`)),
                  }),
                ),
            },
          )
        }
      />
    </>
  );
}

export function AddToGoalSheet() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const goals = useGoals();
  const g = goals.data?.find((x) => x.id === id);
  return (
    <Sheet title={`Add to ${g?.name ?? 'goal'}`} label="Add money to goal">
      <Body />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', paddingVertical: space[6] },
  between: { flexDirection: 'row', justifyContent: 'space-between' },
});
