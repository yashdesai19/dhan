import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  Button,
  EmptyState,
  IconButton,
  IconTile,
  ListCard,
  Money,
  Pill,
  ProgressBar,
  Screen,
  Skeleton,
  Text,
  TopBar,
  Touchable,
} from '@/components';
import { useGoals, useInsights } from '@/data/queries';
import { useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import { fullDate, monthShortYear } from '@/utils/dates';
import { inr, plural } from '@/utils/format';
import { goalProgress, goalsTotals } from '@/utils/goals';

export function GoalsScreen() {
  const router = useRouter();
  const { today } = useToday();
  const goals = useGoals();
  const insights = useInsights();

  const rows = useMemo(
    () => (goals.data ?? []).map((g) => ({ g, p: goalProgress(g, today) })),
    [goals.data, today],
  );
  const totals = goalsTotals(goals.data ?? []);

  return (
    <Screen gap={space[22]}>
      <TopBar title="Goals" trailing={<IconButton icon="plus" accessibilityLabel="New goal" />} />
      <View style={styles.gap6}>
        <Text variant="small" color="muted">
          {`Saved across ${plural(totals.count, 'goal', 'goals')}`}
        </Text>
        {goals.isPending ? <Skeleton width={200} height={56} /> : <Money amount={totals.saved} size="hero" />}
        <Text variant="meta" color="muted">{`${inr(totals.left)} still to go`}</Text>
      </View>
      {rows.length === 0 && !goals.isPending ? (
        <EmptyState
          icon="target"
          title="No goals yet"
          body="Pick something you’re saving for. DHAN works out what to put aside each month."
        />
      ) : (
        <ListCard>
          {rows.map(({ g, p }) => {
            // Near-term goals show the exact date; long ones show month and year (canvas).
            const by = p.monthsLeft > 12 ? monthShortYear(g.targetDate) : fullDate(g.targetDate);
            return (
              <Touchable
                key={g.id}
                onPress={() => router.push(`/goals/${g.id}`)}
                accessibilityLabel={`${g.name}, ${inr(p.saved)} of ${inr(g.target)}, ${p.pct} percent, ${p.pill}`}
                style={styles.goal}
              >
                <View style={styles.head}>
                  <IconTile icon={g.icon} />
                  <View style={styles.grow}>
                    <Text variant="body" weight="medium">
                      {g.name}
                    </Text>
                    <Text variant="meta" color="muted">{`By ${by}`}</Text>
                  </View>
                  <Pill
                    label={p.pill}
                    tone={p.status === 'behind' ? 'warn' : p.pill === 'On track' ? 'income' : 'neutral'}
                  />
                </View>
                <ProgressBar value={p.pct} height={8} />
                <View style={styles.between}>
                  <Text variant="meta" color="muted" tabular>
                    <Text variant="meta" weight="semibold" tabular>
                      {inr(p.saved)}
                    </Text>
                    {` of ${inr(g.target)}`}
                  </Text>
                  <Text variant="meta" color="muted" tabular>{`${p.pct}%`}</Text>
                </View>
              </Touchable>
            );
          })}
        </ListCard>
      )}
      {insights.data && rows.some((r) => r.p.status === 'behind') ? (
        <Banner icon="sparkle">{insights.data.goals}</Banner>
      ) : null}
      <Button label="+ New goal" kind="dashed" size="md" onPress={() => router.push('/goals/new')} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap6: { gap: space[6] },
  goal: { gap: space[10], paddingVertical: space[16] },
  head: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1, gap: 2 },
  between: { flexDirection: 'row', justifyContent: 'space-between' },
});
