import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Banner,
  Button,
  EmptyState,
  IconButton,
  IconTile,
  KpiTile,
  ListCard,
  ListRow,
  ProgressRing,
  RowAmount,
  Screen,
  SectionHeader,
  StickyFooter,
  Text,
  TopBar,
} from '@/components';
import { useAccounts, useGoals } from '@/data/queries';
import { useToday } from '@/features/shared/hooks';
import { fonts, moneySizes, space } from '@/theme';
import { fullDate, weekdayDayMonth } from '@/utils/dates';
import { inr } from '@/utils/format';
import { goalProgress } from '@/utils/goals';

export function GoalDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { today } = useToday();
  const goals = useGoals();
  const accounts = useAccounts().data ?? [];
  const g = goals.data?.find((x) => x.id === id);

  if (!g) {
    return (
      <Screen>
        <TopBar title="Goal" />
        {goals.isPending ? null : (
          <EmptyState icon="target" title="Goal not found" body="It may have been removed." />
        )}
      </Screen>
    );
  }
  const p = goalProgress(g, today);

  return (
    <Screen
      bottom="footer"
      gap={space[20]}
      overlay={
        <StickyFooter>
          <View style={styles.row}>
            <Button
              label="Withdraw"
              kind="secondary"
              grow
              accessibilityHint="Not available in this preview"
            />
            <Button label="Add money" grow onPress={() => router.push(`/goals/${g.id}/add`)} />
          </View>
        </StickyFooter>
      }
    >
      <TopBar title={g.name} trailing={<IconButton icon="edit" accessibilityLabel="Edit goal" />} />
      <View style={styles.center}>
        <ProgressRing value={p.pct} accessibilityLabel={`${p.pct} percent saved`}>
          <Text maxScale={1.2} tabular style={styles.ringValue}>
            {`${p.pct}%`}
          </Text>
          <Text variant="meta" color="muted">
            saved
          </Text>
        </ProgressRing>
      </View>
      <View style={styles.row8}>
        <KpiTile label="Saved" value={inr(p.saved)} />
        <KpiTile label="Target" value={inr(g.target)} />
        <KpiTile label="Left" value={inr(p.left)} />
      </View>
      {p.left > 0 ? (
        <Banner icon="calendar">{`To reach it by ${fullDate(g.targetDate)}, save about ${inr(p.monthly)} a month.`}</Banner>
      ) : (
        <Banner icon="check">You reached this goal.</Banner>
      )}
      <SectionHeader title="History" />
      <ListCard>
        {g.contributions.map((c) => (
          <ListRow
            key={c.id}
            leading={<IconTile icon="coin" tone="primary" />}
            title={`Added from ${accounts.find((a) => a.id === c.accountId)?.name ?? 'account'}`}
            subtitle={c.date === today ? 'Just now' : weekdayDayMonth(c.date)}
            trailing={<RowAmount value={inr(c.amount, 'plus')} color="income" />}
          />
        ))}
      </ListCard>
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center', paddingVertical: space[6] },
  ringValue: { fontFamily: fonts.serif, fontSize: moneySizes.sm, lineHeight: moneySizes.sm },
  row: { flexDirection: 'row', gap: space[10] },
  row8: { flexDirection: 'row', gap: space[8] },
});
