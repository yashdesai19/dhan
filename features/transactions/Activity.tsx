// Activity tab: quick filters, day groups, empty and filtered-empty states (Transactions artboards).
import { memo, useCallback, useMemo } from 'react';
import { RefreshControl, ScrollView, SectionList, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Button,
  Chip,
  EmptyState,
  Icon,
  IconButton,
  Screen,
  Skeleton,
  Text,
  TopBar,
  Touchable,
  TransactionRow,
} from '@/components';
import { useTopPadding } from '@/components/navigation/Screen';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useFiltersStore, applyFilters, defaultFilters, type QuickFilter } from '@/store/filters';
import { useHighlightStore } from '@/store/ui';
import { iconSize, layout, radius, space, useColors } from '@/theme';
import type { Transaction } from '@/types/domain';
import { dayHeading, monthYear } from '@/utils/dates';
import { describeTransaction, type TxView } from '@/utils/describe';
import { inr } from '@/utils/format';
import { groupByDay, monthTotals } from '@/utils/summary';

const QUICK: QuickFilter[] = ['All', 'Expenses', 'Income', 'Transfers', 'Splits'];

type Item = { t: Transaction; v: TxView };
type Section = { title: string; data: Item[] };

const Row = memo(function Row({
  t,
  v,
  highlight,
  onOpen,
}: {
  t: Transaction;
  v: TxView;
  highlight: boolean;
  onOpen: (id: string) => void;
}) {
  return <TransactionRow view={v} highlight={highlight} onPress={() => onOpen(t.id)} />;
});

export function ActivityLoading() {
  return (
    <Screen top="tab" bottom="tabs" scroll={false}>
      <Skeleton width={120} height={26} />
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <View key={i} style={styles.skelRow}>
          <Skeleton width={42} height={42} radius={radius.tile} />
          <View style={styles.grow}>
            <Skeleton width="55%" height={12} />
            <Skeleton width="35%" height={10} style={styles.skelGap} />
          </View>
          <Skeleton width={56} height={12} />
        </View>
      ))}
    </Screen>
  );
}

export function ActivityScreen() {
  const c = useColors();
  const router = useRouter();
  const { today, month } = useToday();
  const money = useMoneyData();
  const filters = useFiltersStore((s) => s.filters);
  const setFilters = useFiltersStore((s) => s.set);
  const highlightId = useHighlightStore((s) => s.id);
  const paddingTop = useTopPadding('tab');

  const sheetActive =
    filters.range !== defaultFilters.range ||
    filters.types.length > 0 ||
    filters.categoryIds.length > 0 ||
    filters.accountIds.length > 0 ||
    !!filters.min ||
    !!filters.max;

  const { sections, totals } = useMemo(() => {
    const list = applyFilters(money.transactions, filters, today);
    const groups = groupByDay(list);
    return {
      totals: monthTotals(money.transactions, month),
      sections: groups.map<Section>((g) => ({
        title: dayHeading(g.date, today),
        data: g.items.map((t) => ({
          t,
          v: describeTransaction(t, money.categories, money.accounts, { today }),
        })),
      })),
    };
  }, [money.transactions, money.categories, money.accounts, filters, today, month]);

  const open = useCallback((id: string) => router.push(`/transactions/${id}`), [router]);

  if (money.loading) return <ActivityLoading />;

  if (money.transactions.length === 0) {
    return (
      <Screen top="tab" bottom="tabs" scroll={false}>
        <TopBar variant="tab" title="Activity" />
        <View style={styles.emptyFill}>
          <EmptyState
            icon="list"
            title="No transactions yet"
            body="Add your first expense. It takes about three seconds, and DHAN starts learning where your money goes."
          >
            <Button label="Add an expense" onPress={() => router.push('/add/expense')} />
            <Button
              label="Add income instead"
              kind="ghost"
              size="sm"
              onPress={() => router.push('/add/income')}
            />
          </EmptyState>
        </View>
      </Screen>
    );
  }

  const header = (
    <View style={[styles.header, { paddingTop }]}>
      <TopBar
        variant="tab"
        title="Activity"
        trailing={
          <View style={styles.actions}>
            <IconButton
              icon="search"
              accessibilityLabel="Search transactions"
              onPress={() => router.push('/transactions/search')}
            />
            <IconButton
              icon="filter"
              accessibilityLabel={sheetActive ? 'Filters, active' : 'Filters'}
              badge={sheetActive}
              onPress={() => router.push('/transactions/filters')}
            />
          </View>
        }
      />
      <View style={styles.between}>
        <Touchable
          onPress={() => router.push('/transactions/filters')}
          accessibilityLabel={`${monthYear(month)}, change date range`}
          style={styles.month}
        >
          <Text variant="body" weight="semibold">
            {filters.range === 'This month' ? monthYear(month) : filters.range}
          </Text>
          <Icon name="chevD" size={iconSize.md} strokeWidth={2} />
        </Touchable>
        <Text variant="meta" color="muted" tabular>
          {`Spent ${inr(totals.spent)} · Earned ${inr(totals.income)}`}
        </Text>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.bleed}
        contentContainerStyle={styles.chips}
      >
        {QUICK.map((q) => (
          <Chip key={q} label={q} selected={filters.quick === q} onPress={() => setFilters({ quick: q })} />
        ))}
      </ScrollView>
    </View>
  );

  return (
    <View style={[styles.fill, { backgroundColor: c.bg }]}>
      <SectionList<Item, Section>
        sections={sections}
        keyExtractor={(item) => item.t.id}
        stickySectionHeadersEnabled={false}
        initialNumToRender={14}
        ListHeaderComponent={header}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={money.refreshing}
            onRefresh={() => void money.refetch()}
            tintColor={c.muted}
            colors={[c.primary]}
          />
        }
        renderSectionHeader={({ section }) => (
          <Text variant="meta" weight="semibold" color="muted" style={styles.day} accessibilityRole="header">
            {section.title}
          </Text>
        )}
        renderItem={({ item }) => (
          <Row t={item.t} v={item.v} highlight={item.t.id === highlightId} onOpen={open} />
        )}
        ListEmptyComponent={
          <EmptyState
            icon="search"
            title="Nothing here this month"
            body="No transactions match this filter. Try another month or clear the filter."
          >
            <Button
              label="Clear filters"
              kind="secondary"
              size="sm"
              onPress={() => useFiltersStore.getState().reset()}
            />
          </EmptyState>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  list: { paddingHorizontal: layout.gutter, paddingBottom: space[24] },
  header: { gap: space[18], paddingBottom: space[4] },
  actions: { flexDirection: 'row', gap: space[8] },
  between: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: space[8],
    flexWrap: 'wrap',
  },
  month: { flexDirection: 'row', alignItems: 'center', gap: space[6], minHeight: 44 },
  bleed: { marginHorizontal: -layout.gutter },
  chips: { flexDirection: 'row', gap: space[8], paddingHorizontal: layout.gutter },
  day: { paddingTop: space[18], paddingBottom: space[4] },
  emptyFill: { flex: 1, justifyContent: 'center' },
  skelRow: { flexDirection: 'row', alignItems: 'center', gap: space[12], paddingVertical: space[10] },
  grow: { flex: 1 },
  skelGap: { marginTop: space[8] },
});
