import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  Button,
  Card,
  EmptyState,
  Icon,
  IconButton,
  IconTile,
  ListCard,
  Money,
  ProgressBar,
  Screen,
  Skeleton,
  Text,
  Touchable,
} from '@/components';
import { useBudgets, useHistory, useRecurring, useReplaceBudget } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { iconSize, space } from '@/theme';
import { budgetStatus, suggestBudget, type CategoryBudgetStatus } from '@/utils/budget';
import { dayMonth, monthName, monthOf, shiftMonth } from '@/utils/dates';
import { inr, plural } from '@/utils/format';

const BUDGETABLE = ['bills', 'food', 'transport', 'shopping'];

function MonthSwitch({ month, onChange }: { month: string; onChange: (m: string) => void }) {
  return (
    <View style={styles.monthRow}>
      <IconButton
        variant="bare"
        icon="chevL"
        accessibilityLabel="Previous month"
        onPress={() => onChange(shiftMonth(month, -1))}
      />
      <Text variant="small" weight="medium">
        {monthName(month, true)}
      </Text>
      <IconButton
        variant="bare"
        icon="chevR"
        accessibilityLabel="Next month"
        onPress={() => onChange(shiftMonth(month, 1))}
      />
    </View>
  );
}

function CategoryRow({
  s,
  name,
  icon,
  note,
  onPress,
}: {
  s: CategoryBudgetStatus;
  name: string;
  icon: Parameters<typeof IconTile>[0]['icon'];
  note: string;
  onPress: () => void;
}) {
  const warn = s.tone !== 'ok';
  return (
    <Touchable
      onPress={onPress}
      style={styles.catRow}
      accessibilityLabel={`${name}, ${inr(s.spent)} of ${inr(s.limit)}, ${note}`}
      accessibilityHint="Opens category budget"
    >
      <View style={styles.catHead}>
        <IconTile icon={icon} tone={warn ? 'warn' : 'neutral'} size="md" />
        <Text variant="body" weight="medium" style={styles.grow}>
          {name}
        </Text>
        <Text variant="small" tabular>
          <Text variant="small" weight="semibold">
            {inr(s.spent)}
          </Text>
          <Text variant="small" color="muted">{` / ${inr(s.limit)}`}</Text>
        </Text>
      </View>
      <ProgressBar value={s.pct} tone={s.tone === 'over' ? 'expense' : warn ? 'warn' : 'primary'} />
      <Text
        variant="caption"
        weight={warn ? 'medium' : 'regular'}
        color={s.tone === 'over' ? 'expense' : warn ? 'warnText' : 'muted'}
      >
        {note}
      </Text>
    </Touchable>
  );
}

export function BudgetScreen() {
  const router = useRouter();
  const { today, month: current } = useToday();
  const [month, setMonth] = useState(current);
  const money = useMoneyData();
  const budgets = useBudgets();
  const history = useHistory();
  const recurring = useRecurring();
  const replace = useReplaceBudget(month);
  const show = useToastStore((s) => s.show);

  const status = useMemo(
    () =>
      budgetStatus(
        budgets.data?.find((b) => b.month === month),
        money.transactions,
        month,
        today,
      ),
    [budgets.data, money.transactions, month, today],
  );
  const suggestion = useMemo(
    () => suggestBudget(history.data ?? [], money.transactions, BUDGETABLE, current),
    [history.data, money.transactions, current],
  );

  if (money.loading || budgets.isPending) {
    return (
      <Screen top="tab" bottom="tabs" scroll={false}>
        <Skeleton width={120} height={26} />
        <Skeleton width={200} height={56} />
        <Skeleton width="100%" height={10} radius={5} />
        <Skeleton width="100%" height={320} radius={20} />
      </Screen>
    );
  }

  const header = (
    <View style={styles.header}>
      <Text variant="title" accessibilityRole="header">
        Budget
      </Text>
      <MonthSwitch month={month} onChange={setMonth} />
    </View>
  );

  if (!status) {
    return (
      <Screen top="tab" bottom="tabs" gap={space[18]}>
        {header}
        <EmptyState
          icon="pie"
          title="Set your first budget"
          body="A monthly limit lets DHAN warn you before you overspend, not after."
        />
        <Card>
          <View style={styles.sugHead}>
            <Icon name="sparkle" size={iconSize.lg} color="primary" />
            <Text variant="small" weight="semibold">
              Suggested for you
            </Text>
          </View>
          <Money amount={suggestion.total} size="sm" />
          <Text variant="small" color="muted">
            Based on your last 3 months, with 10% breathing room. Split across Bills, Food, Transport and
            Shopping.
          </Text>
          <View style={styles.row10}>
            <Button
              label={`Use ${inr(suggestion.total)}`}
              size="sm"
              grow
              loading={replace.isPending}
              onPress={() =>
                replace.mutate(
                  Object.entries(suggestion.split).map(([categoryId, limit]) => ({
                    categoryId,
                    limit,
                    rollover: false,
                    warnAtPercent: 90,
                  })),
                  { onSuccess: () => show({ message: `Budget set · ${inr(suggestion.total)} a month` }) },
                )
              }
            />
            <Button
              label="Set my own"
              kind="secondary"
              size="sm"
              grow
              onPress={() => router.push({ pathname: '/budget/food/edit', params: { month } })}
            />
          </View>
        </Card>
      </Screen>
    );
  }

  const warn = status.categories.find((c) => c.tone !== 'ok');
  const catName = (id: string) => money.categories.find((c) => c.id === id)?.short ?? id;
  const catIcon = (id: string) => money.categories.find((c) => c.id === id)?.icon ?? 'tag';
  const rest =
    status.daysLeft === 1 ? 'the rest of the month' : `the next ${plural(status.daysLeft, 'day', 'days')}`;
  const dueFor = (id: string) =>
    (recurring.data ?? [])
      .filter((r) => r.categoryId === id && r.kind !== 'subscription' && r.kind !== 'income')
      .sort((a, b) => a.nextDate.localeCompare(b.nextDate))[0];
  const noteFor = (s: CategoryBudgetStatus) => {
    if (s.tone === 'over') return `${inr(-s.left)} over`;
    if (s.tone === 'warn') return `${inr(s.left)} left · slow down a little`;
    const due = dueFor(s.categoryId);
    return due && monthOf(due.nextDate) === shiftMonth(month, 1)
      ? `${inr(s.left)} left · ${due.name} due ${dayMonth(due.nextDate)}`
      : `${inr(s.left)} left`;
  };

  return (
    <Screen
      top="tab"
      bottom="tabs"
      refresh={{ refreshing: money.refreshing, onRefresh: () => void money.refetch() }}
    >
      {header}
      <View style={styles.gap12}>
        <View style={styles.leftRow}>
          <Money amount={Math.max(0, status.left)} size="hero" />
          <Text variant="body" color="muted">
            {status.left >= 0 ? 'left to spend' : 'over budget'}
          </Text>
        </View>
        <ProgressBar
          value={status.pct}
          height={10}
          tone={status.pct > 100 ? 'expense' : 'primary'}
          accessibilityLabel={`${status.pct} percent of budget used`}
        />
        <View style={styles.between}>
          <Text variant="meta" color="muted" tabular>{`${inr(status.spent)} spent`}</Text>
          <Text variant="meta" color="muted" tabular>{`${inr(status.limit)} budget`}</Text>
        </View>
        {month === current ? (
          <Text variant="small">
            {`${plural(status.daysLeft, 'day', 'days')} to go · about `}
            <Text variant="small" weight="semibold">{`${inr(status.perDay)} a day`}</Text>
            {' keeps you on track'}
          </Text>
        ) : null}
      </View>
      {warn ? (
        <Banner icon="alert" tone="warn">
          {warn.tone === 'over'
            ? `${catName(warn.categoryId)} is over by ${inr(-warn.left)} this month.`
            : `${catName(warn.categoryId)} is at ${warn.pct}%. Only ${inr(warn.left)} left for ${rest}.`}
        </Banner>
      ) : null}
      <ListCard>
        {status.categories.map((s) => (
          <CategoryRow
            key={s.categoryId}
            s={s}
            name={catName(s.categoryId)}
            icon={catIcon(s.categoryId)}
            note={noteFor(s)}
            onPress={() => router.push(`/budget/${s.categoryId}`)}
          />
        ))}
      </ListCard>
      <Button
        label="+ Add category budget"
        kind="dashed"
        size="md"
        onPress={() => router.push({ pathname: '/budget/new/edit', params: { month } })}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  monthRow: { flexDirection: 'row', alignItems: 'center', gap: space[4] },
  gap12: { gap: space[12] },
  leftRow: { flexDirection: 'row', alignItems: 'baseline', gap: space[10], flexWrap: 'wrap' },
  between: { flexDirection: 'row', justifyContent: 'space-between' },
  catRow: { gap: space[10], paddingVertical: space[16] },
  catHead: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1 },
  sugHead: { flexDirection: 'row', alignItems: 'center', gap: space[10] },
  row10: { flexDirection: 'row', gap: space[10] },
});
