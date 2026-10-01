import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Avatar,
  Banner,
  Card,
  Divider,
  EmptyState,
  Button,
  Icon,
  IconButton,
  Money,
  Pill,
  ProgressBar,
  Screen,
  SectionHeader,
  SegmentedBar,
  Skeleton,
  Text,
  Touchable,
  TransactionRow,
  type IconName,
} from '@/components';
import {
  useBudgets,
  useGroupExpenses,
  useInsights,
  useNotifications,
  usePeople,
  useSettlements,
  useUser,
} from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { usePrefsStore } from '@/store/prefs';
import { useHighlightStore } from '@/store/ui';
import { iconSize, radius, size, space, useColors, type ColorName } from '@/theme';
import { budgetStatus } from '@/utils/budget';
import { dayMonth, monthName, monthOf } from '@/utils/dates';
import { describeTransaction } from '@/utils/describe';
import { inr, plural } from '@/utils/format';
import { overallPosition } from '@/utils/splits';
import { monthTotals, netBalance, sortNewestFirst, spendingBreakdown } from '@/utils/summary';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning,';
  if (h < 17) return 'Good afternoon,';
  return 'Good evening,';
}

const QUICK: { label: string; icon: IconName; color: ColorName; href: string }[] = [
  { label: 'Expense', icon: 'up', color: 'expense', href: '/add/expense' },
  { label: 'Income', icon: 'down', color: 'income', href: '/add/income' },
  { label: 'Transfer', icon: 'transfer', color: 'ink', href: '/add/transfer' },
  { label: 'Split', icon: 'users', color: 'ink', href: '/add/split' },
];

export function HomeLoading() {
  return (
    <Screen top="home" bottom="tabs" scroll={false} testID="home-loading">
      <View
        style={styles.header}
        accessible
        accessibilityRole="progressbar"
        accessibilityLabel="Loading your dashboard"
      >
        <Skeleton width={44} height={44} radius={22} />
        <View style={styles.headerText}>
          <Skeleton width={90} height={10} />
          <Skeleton width={60} height={14} />
        </View>
        <Skeleton width={44} height={44} radius={22} />
        <Skeleton width={44} height={44} radius={22} />
      </View>
      <View style={styles.gap12}>
        <Skeleton width={150} height={12} />
        <Skeleton width={230} height={50} radius={12} />
        <Skeleton width={130} height={22} radius={11} />
      </View>
      <Skeleton width="100%" height={76} radius={radius.card} />
      <View style={styles.quick}>
        {[0, 1, 2, 3].map((i) => (
          <View key={i} style={styles.quickItem}>
            <Skeleton width={56} height={56} radius={radius.quick} />
            <Skeleton width={44} height={10} />
          </View>
        ))}
      </View>
      <Skeleton width="100%" height={190} radius={radius.card} />
      <View style={styles.gap12}>
        <Skeleton width={80} height={14} />
        {[0, 1, 2, 3].map((i) => (
          <View key={i} style={styles.skelRow}>
            <Skeleton width={42} height={42} radius={radius.tile} />
            <View style={styles.headerText}>
              <Skeleton width="55%" height={12} />
              <Skeleton width="35%" height={10} />
            </View>
            <Skeleton width={56} height={12} />
          </View>
        ))}
      </View>
    </Screen>
  );
}

export function HomeScreen() {
  const c = useColors();
  const router = useRouter();
  const { today, month } = useToday();
  const money = useMoneyData();
  const budgets = useBudgets();
  const groupExpenses = useGroupExpenses();
  const settlements = useSettlements();
  const people = usePeople();
  const insights = useInsights();
  const notifications = useNotifications();
  const user = useUser();
  const hideBalances = usePrefsStore((s) => s.hideBalances);
  const [revealed, setRevealed] = useState(!hideBalances);
  const highlightId = useHighlightStore((s) => s.id);
  const setHighlight = useHighlightStore((s) => s.set);

  useEffect(() => setRevealed(!hideBalances), [hideBalances]);
  useEffect(() => {
    if (!highlightId) return;
    const t = setTimeout(() => setHighlight(null), 5000);
    return () => clearTimeout(t);
  }, [highlightId, setHighlight]);

  const view = useMemo(() => {
    const { accounts, transactions, categories } = money;
    const balance = netBalance(accounts);
    const totals = monthTotals(transactions, month);
    const breakdown = spendingBreakdown(transactions, month, categories);
    const budget = budgetStatus(
      budgets.data?.find((b) => b.month === month),
      transactions,
      month,
      today,
    );
    const pos = overallPosition(groupExpenses.data ?? [], settlements.data ?? [], 'me');
    const name = (id: string) => people.data?.find((p) => p.id === id)?.name ?? id;
    const owe = Object.entries(pos.byPerson)
      .filter(([, v]) => v < 0)
      .map(([id]) => name(id));
    const owed = Object.entries(pos.byPerson)
      .filter(([, v]) => v > 0)
      .map(([id]) => name(id));
    const recent = sortNewestFirst(transactions).slice(0, 5);
    return { balance, totals, breakdown, budget, pos, owe, owed, recent };
  }, [money, budgets.data, groupExpenses.data, settlements.data, people.data, month, today]);

  if (money.loading || budgets.isPending) return <HomeLoading />;
  if (money.error) {
    return (
      <Screen top="home" bottom="tabs">
        <EmptyState
          icon="wifioff"
          title="Couldn’t load your dashboard"
          body="Your transactions are safe on this phone. Check your connection and try again."
        >
          <Button
            label="Try again"
            kind="secondary"
            icon="repeat"
            size="sm"
            onPress={() => void money.refetch()}
          />
        </EmptyState>
      </Screen>
    );
  }

  const unread = notifications.data?.some((n) => n.unread) ?? false;
  const firstName = user.data?.name.split(' ')[0] ?? '';
  const { balance, totals, breakdown, budget, pos, owe, owed, recent } = view;
  const joinNames = (xs: string[]) =>
    xs.length <= 2 ? xs.join(', ') : `${xs.slice(0, 2).join(', ')} +${xs.length - 2}`;

  return (
    <Screen
      top="home"
      bottom="tabs"
      refresh={{ refreshing: money.refreshing, onRefresh: () => void money.refetch() }}
    >
      <View style={styles.header}>
        <Avatar initials={user.data?.initials ?? ''} soft size="xxl" />
        <View style={styles.headerText}>
          <Text variant="meta" color="muted">
            {greeting()}
          </Text>
          <Text variant="greeting">{firstName}</Text>
        </View>
        <IconButton
          icon="sparkle"
          accessibilityLabel="Ask DHAN AI"
          onPress={() => router.push('/assistant')}
        />
        <IconButton
          icon="bell"
          accessibilityLabel={unread ? 'Notifications, unread' : 'Notifications'}
          badge={unread}
          onPress={() => router.push('/notifications')}
        />
      </View>

      <View style={styles.gap6}>
        <Text variant="small" color="muted">
          {`Total balance · ${plural(balance.count, 'account', 'accounts')}`}
        </Text>
        {revealed ? (
          <Money
            amount={balance.total}
            size="hero"
            accessibilityLabel={`Total balance ${balance.total} rupees`}
          />
        ) : (
          <Touchable accessibilityLabel="Show balance" onPress={() => setRevealed(true)} feedback="none">
            <Text variant="displayXl" color="faint">
              ₹ ••••••
            </Text>
          </Touchable>
        )}
        <View style={styles.pillRow}>
          <Pill
            label={`${inr(totals.net, 'plus')} this month`}
            tone={totals.net >= 0 ? 'income' : 'expense'}
          />
          <Text variant="meta" color="muted">
            {`vs 1 ${monthName(month)}`}
          </Text>
        </View>
      </View>

      <View style={[styles.kpis, { backgroundColor: c.surface, borderColor: c.line }]}>
        {[
          { label: 'Income', value: inr(totals.income), color: 'ink' as ColorName },
          { label: 'Spent', value: inr(totals.spent), color: 'ink' as ColorName },
          {
            label: 'Net flow',
            value: inr(totals.net, 'plus'),
            color: (totals.net >= 0 ? 'income' : 'expense') as ColorName,
          },
        ].map((k, i) => (
          <View
            key={k.label}
            style={[styles.kpi, i > 0 ? { borderLeftWidth: 1, borderLeftColor: c.line } : null]}
            accessible
            accessibilityLabel={`${k.label} ${k.value}`}
          >
            <Text variant="caption" color="muted">
              {k.label}
            </Text>
            <Text variant="greeting" tabular color={k.color} numberOfLines={1} maxScale={1.3}>
              {k.value}
            </Text>
          </View>
        ))}
      </View>

      <View style={styles.quick}>
        {QUICK.map((q) => (
          <Touchable
            key={q.label}
            accessibilityLabel={`Add ${q.label.toLowerCase()}`}
            onPress={() => router.push(q.href)}
            style={styles.quickItem}
          >
            <View style={[styles.quickTile, { backgroundColor: c.surface, borderColor: c.line }]}>
              <Icon name={q.icon} size={iconSize.xxl} color={q.color} />
            </View>
            <Text variant="caption" weight="medium">
              {q.label}
            </Text>
          </Touchable>
        ))}
      </View>

      {insights.data ? <Banner icon="sparkle">{insights.data.home}</Banner> : null}

      <Card>
        <View style={styles.between}>
          <Text variant="section">Where it went</Text>
          <Text variant="meta" color="muted">
            {monthName(month, true)}
          </Text>
        </View>
        {breakdown.total > 0 ? (
          <SegmentedBar slices={breakdown.slices} />
        ) : (
          <Text variant="small" color="muted">
            No spending yet this month.
          </Text>
        )}
        {budget ? (
          <>
            <Divider />
            <Touchable
              onPress={() => router.navigate('/budget')}
              accessibilityLabel={`Monthly budget, ${inr(budget.spent)} of ${inr(budget.limit)}, ${inr(budget.left)} left`}
              style={styles.gap8}
            >
              <View style={styles.between}>
                <Text variant="small">Monthly budget</Text>
                <Text variant="small" tabular>
                  <Text variant="small" weight="semibold">
                    {inr(budget.spent)}
                  </Text>
                  <Text variant="small" color="muted">{` / ${inr(budget.limit)}`}</Text>
                </Text>
              </View>
              <ProgressBar value={budget.pct} height={8} />
              <Text variant="meta" color="muted">
                {`${inr(budget.left)} left · ${plural(budget.daysLeft, 'day', 'days')} to go`}
              </Text>
            </Touchable>
          </>
        ) : null}
      </Card>

      <View style={styles.tiles}>
        {[
          {
            label: 'You owe',
            value: pos.owe,
            color: 'expense' as ColorName,
            sub: owe.length ? `to ${joinNames(owe)}` : 'All square',
          },
          {
            label: 'You’re owed',
            value: pos.owed,
            color: 'income' as ColorName,
            sub: owed.length ? `from ${joinNames(owed)}` : 'Nothing pending',
          },
        ].map((t) => (
          <Touchable
            key={t.label}
            onPress={() => router.push('/splits')}
            accessibilityLabel={`${t.label} ${inr(t.value)} ${t.sub}`}
            style={[styles.tile, { backgroundColor: c.surface, borderColor: c.line }]}
          >
            <Text variant="meta" color="muted">
              {t.label}
            </Text>
            <Text variant="heading" tabular color={t.color}>
              {inr(t.value)}
            </Text>
            <Text variant="caption" color="muted" numberOfLines={1}>
              {t.sub}
            </Text>
          </Touchable>
        ))}
      </View>

      <View style={styles.gap4}>
        <SectionHeader title="Recent" action="See all" onAction={() => router.navigate('/activity')} />
        {recent.length === 0 ? (
          <Text variant="small" color="muted" style={styles.emptyRecent}>
            Nothing yet. Tap + to add your first expense.
          </Text>
        ) : (
          recent.map((t) => {
            const v = describeTransaction(t, money.categories, money.accounts, { today });
            const sub =
              t.date !== today && monthOf(t.date) === month && t.type !== 'split'
                ? { ...v, subtitle: `${v.subtitle} · ${dayMonth(t.date)}` }
                : v;
            return (
              <TransactionRow
                key={t.id}
                view={sub}
                highlight={t.id === highlightId}
                onPress={() => router.push(`/transactions/${t.id}`)}
              />
            );
          })
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  headerText: { flex: 1, gap: 2 },
  gap4: { gap: space[4] },
  gap6: { gap: space[6] },
  gap8: { gap: space[8] },
  gap12: { gap: space[12] },
  pillRow: { flexDirection: 'row', alignItems: 'center', gap: space[8], marginTop: space[4] },
  kpis: {
    flexDirection: 'row',
    borderWidth: 1,
    borderRadius: radius.card,
    paddingVertical: space[16],
    paddingHorizontal: space[4],
  },
  kpi: { flex: 1, gap: space[4], paddingHorizontal: space[12] },
  quick: { flexDirection: 'row', justifyContent: 'space-between', gap: space[8] },
  quickItem: { flex: 1, alignItems: 'center', gap: space[8] },
  quickTile: {
    width: size.quickAction,
    height: size.quickAction,
    borderRadius: radius.quick,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  tiles: { flexDirection: 'row', gap: space[12] },
  tile: { flex: 1, gap: space[6], borderWidth: 1, borderRadius: radius.kpi, padding: space[16] },
  skelRow: { flexDirection: 'row', alignItems: 'center', gap: space[12], paddingVertical: space[10] },
  emptyRecent: { paddingVertical: space[12] },
});
