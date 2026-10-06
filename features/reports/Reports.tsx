import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  Button,
  Card,
  CategoryBars,
  GroupedBarChart,
  Icon,
  IconTile,
  KpiTile,
  ListCard,
  ListRow,
  RowAmount,
  Screen,
  SectionHeader,
  SegmentedControl,
  Skeleton,
  Text,
  TopBar,
} from '@/components';
import { useAssets, useHistory, useLiabilities } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { iconSize, radius, size, space, useColors } from '@/theme';
import { dayMonth, monthName, monthYear, shiftMonth } from '@/utils/dates';
import { inr, signedPercent } from '@/utils/format';
import { netWorth } from '@/utils/netWorth';
import { compareWithPrevious, sixMonthSeries, topExpenses } from '@/utils/reports';
import { expenseCategoryIds, monthTotals, spendingBreakdown } from '@/utils/summary';

type Period = 'month' | 'quarter' | 'year';

function OfflineError({ onRetry }: { onRetry: () => void }) {
  const c = useColors();
  return (
    <View
      style={[styles.error, { backgroundColor: c.surface, borderColor: c.line }]}
      accessibilityRole="alert"
    >
      <View style={[styles.errorIcon, { backgroundColor: c.expenseSoft }]}>
        <Icon name="alert" size={iconSize.xxl + 2} color="expense" />
      </View>
      <Text variant="profileName" align="center" style={styles.errorTitle}>
        Couldn’t load your reports
      </Text>
      <Text variant="small" color="muted" align="center">
        This needs a connection. Your transactions are safe on this phone.
      </Text>
      <View style={styles.retry}>
        <Button label="Try again" kind="secondary" size="sm" icon="repeat" onPress={onRetry} />
      </View>
    </View>
  );
}

export function ReportsScreen() {
  const router = useRouter();
  const { month } = useToday();
  const money = useMoneyData();
  const history = useHistory();
  const assets = useAssets();
  const liabilities = useLiabilities();
  const [period, setPeriod] = useState<Period>('month');

  const view = useMemo(() => {
    const h = history.data ?? [];
    const t = money.transactions;
    const totals = monthTotals(t, month);
    const breakdown = spendingBreakdown(t, month, money.categories);
    const idOf = (name: string) => expenseCategoryIds(money.categories, [name])[0] ?? name;
    const compare = compareWithPrevious(h, t, month, [
      { id: 'total', label: 'Total spending' },
      { id: idOf('Food'), label: 'Food' },
      { id: idOf('Transport'), label: 'Transport' },
      { id: idOf('Shopping'), label: 'Shopping' },
    ]);
    const nw = netWorth(money.accounts, assets.data ?? [], liabilities.data ?? []);
    const lastNw = h.at(-1)?.netWorth ?? nw.net;
    return {
      totals,
      breakdown,
      compare,
      series: sixMonthSeries(h, t, month),
      top: topExpenses(t, month),
      nw,
      nwChange: nw.net - lastNw,
    };
  }, [history.data, money, month, assets.data, liabilities.data]);

  const offline = history.isError;
  const loading = money.loading || history.isPending;
  const prev = monthName(shiftMonth(month, -1), true);

  return (
    <Screen
      gap={space[18]}
      refresh={{ refreshing: history.isRefetching, onRefresh: () => void history.refetch() }}
    >
      <TopBar title="Reports" />
      {offline ? (
        <Banner icon="wifioff" tone="neutral">
          You’re offline. Anything you add will sync when you’re back.
        </Banner>
      ) : null}
      {!offline ? (
        <SegmentedControl
          accessibilityLabel="Report period"
          value={period}
          onChange={setPeriod}
          options={[
            { value: 'month', label: 'Month' },
            { value: 'quarter', label: 'Quarter' },
            { value: 'year', label: 'Year' },
          ]}
        />
      ) : null}
      {!offline ? (
        <View style={styles.between}>
          <Text variant="body" weight="semibold">
            {monthYear(month)}
          </Text>
          <Text variant="meta" color="muted">{`vs ${prev}`}</Text>
        </View>
      ) : null}
      <View style={styles.grid}>
        <View style={styles.gridRow}>
          <KpiTile label="Earned" value={inr(view.totals.income)} />
          <KpiTile label="Spent" value={inr(view.totals.spent)} />
        </View>
        {!offline ? (
          <View style={styles.gridRow}>
            <KpiTile label="Saved" value={inr(view.totals.net)} tone="income" />
            <KpiTile label="Savings rate" value={`${view.totals.savingsRate}%`} tone="income" />
          </View>
        ) : null}
      </View>
      {offline ? (
        <>
          <Text variant="caption" color="muted">
            Last updated 10:42 am
          </Text>
          <OfflineError onRetry={() => void history.refetch()} />
        </>
      ) : loading ? (
        <Skeleton width="100%" height={220} radius={radius.card} />
      ) : (
        <>
          <Card>
            <View style={styles.between}>
              <Text variant="section">Income vs spending</Text>
              <Text variant="meta" color="muted">
                6 months
              </Text>
            </View>
            <GroupedBarChart data={view.series} />
          </Card>
          <Card>
            <Text variant="section">Spending by category</Text>
            <CategoryBars rows={view.breakdown.slices} />
          </Card>
          <SectionHeader title={`Compared with ${prev}`} />
          <ListCard>
            {view.compare.map((r) => (
              <ListRow
                key={r.id}
                title={r.label}
                subtitle={`${inr(r.previous)} in ${prev}`}
                trailing={
                  <RowAmount value={signedPercent(r.change)} color={r.change <= 0 ? 'income' : 'expense'} />
                }
                accessibilityLabel={`${r.label}, ${r.change <= 0 ? 'down' : 'up'} ${Math.abs(r.change)} percent from ${inr(r.previous)}`}
              />
            ))}
          </ListCard>
          <SectionHeader title="Top expenses" />
          <ListCard>
            {view.top.map((t) => {
              const cat = money.categories.find((x) => x.id === t.categoryId);
              return (
                <ListRow
                  key={t.id}
                  leading={<IconTile icon={cat?.icon ?? 'receipt'} />}
                  title={t.title}
                  subtitle={`${cat?.short ?? ''} · ${dayMonth(t.date)}`}
                  trailing={<RowAmount value={inr(t.amount)} />}
                  onPress={() => router.push(`/transactions/${t.id}`)}
                />
              );
            })}
          </ListCard>
          <Text variant="meta" color="muted">
            Your share of group expenses, like rent and trips, counts as spending once you settle up.
          </Text>
          <ListCard>
            <ListRow
              leading={<IconTile icon="trend" tone="primary" size="lg" />}
              title={`Net worth ${inr(view.nw.net)}`}
              subtitle={`${inr(view.nwChange, 'plus')} since ${prev}`}
              subtitleColor={view.nwChange >= 0 ? 'income' : 'expense'}
              chevron
              pad={14}
              onPress={() => router.push('/reports/net-worth')}
            />
          </ListCard>
          <SectionHeader
            title="Account balances"
            action="Accounts"
            onAction={() => router.push('/accounts')}
          />
          <ListCard>
            {money.accounts
              .filter((a) => !a.archived && a.type !== 'cash' && a.type !== 'wallet')
              .map((a) => (
                <ListRow
                  key={a.id}
                  leading={<IconTile icon={a.type === 'credit' ? 'card' : 'bank'} size="sm" />}
                  title={a.name}
                  pad={10}
                  trailing={<RowAmount value={inr(a.balance)} color={a.balance < 0 ? 'expense' : 'ink'} />}
                />
              ))}
            <ListRow
              leading={<IconTile icon="cash" size="sm" />}
              title="Cash and wallets"
              pad={10}
              trailing={
                <RowAmount
                  value={inr(
                    money.accounts
                      .filter((a) => !a.archived && (a.type === 'cash' || a.type === 'wallet'))
                      .reduce((s, a) => s + a.balance, 0),
                  )}
                />
              }
            />
          </ListCard>
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  grid: { gap: space[10] },
  gridRow: { flexDirection: 'row', gap: space[10] },
  error: {
    alignItems: 'center',
    gap: space[10],
    paddingVertical: space[28],
    paddingHorizontal: space[16],
    borderWidth: 1,
    borderRadius: radius.card,
  },
  errorIcon: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center' },
  errorTitle: { paddingTop: space[4] },
  retry: { alignSelf: 'stretch', paddingTop: space[8], minHeight: size.buttonSm },
});
