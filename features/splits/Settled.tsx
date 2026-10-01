import { StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button, Card, Icon, Text } from '@/components';
import { undo } from '@/data/queries/actions';
import { useToday } from '@/features/shared/hooks';
import { layout, space, useColors } from '@/theme';
import { weekdayDayMonth } from '@/utils/dates';
import { inr } from '@/utils/format';
import { useSplits } from './useSplits';

const METHOD_LABEL: Record<string, string> = { upi: 'UPI', cash: 'cash', bank: 'bank transfer' };

/** Settle up — success (SettleSuccess artboard). */
export function SettledScreen() {
  const c = useColors();
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const { today } = useToday();
  const {
    personId = '',
    amount = '0',
    method = 'upi',
    settlementId = '',
  } = useLocalSearchParams<{ personId: string; amount: string; method: string; settlementId: string }>();
  const s = useSplits();
  const p = s.person(personId);
  const square = (s.overall.byPerson[personId] ?? 0) === 0;

  return (
    <View
      style={[
        styles.root,
        {
          backgroundColor: c.bg,
          paddingTop: insets.top + space[8],
          paddingBottom: Math.max(insets.bottom, 34),
          paddingHorizontal: layout.gutterAuth,
        },
      ]}
    >
      <View
        style={styles.body}
        accessible
        accessibilityLabel={`${square ? `You and ${p.name} are all square` : 'Payment recorded'}. ${inr(Number(amount))} recorded.`}
      >
        <View style={[styles.check, { backgroundColor: c.primarySoft }]}>
          <Icon name="check" size={40} color="primary" strokeWidth={2.4} />
        </View>
        <Text variant="displaySm" align="center" style={styles.title}>
          {square ? `You and ${p.name}\nare all square` : 'Payment recorded'}
        </Text>
        <Text variant="body" color="muted" align="center">
          {`${inr(Number(amount))} recorded as paid by ${METHOD_LABEL[method] ?? method} · ${weekdayDayMonth(today)}`}
        </Text>
        <View style={styles.card}>
          <Card gap={space[10]}>
            <View style={styles.between}>
              <Text variant="body">Overall, you’re owed</Text>
              <Text variant="body" weight="semibold" color="income" tabular>
                {inr(s.overall.owed)}
              </Text>
            </View>
            <View style={styles.between}>
              <Text variant="body">You owe</Text>
              <Text variant="body" weight="semibold" tabular>
                {inr(s.overall.owe)}
              </Text>
            </View>
          </Card>
        </View>
      </View>
      <View style={styles.actions}>
        <Button label="Done" onPress={() => router.back()} />
        <Button
          label="Undo"
          kind="ghost"
          size="sm"
          onPress={() =>
            void undo.settlement(qc, settlementId).then(() => router.replace(`/splits/settle/${personId}`))
          }
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  body: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: space[14] },
  check: { width: 88, height: 88, borderRadius: 44, alignItems: 'center', justifyContent: 'center' },
  title: { paddingTop: space[8] },
  card: { alignSelf: 'stretch', marginTop: space[14] },
  between: { flexDirection: 'row', justifyContent: 'space-between' },
  actions: { gap: space[10] },
});
