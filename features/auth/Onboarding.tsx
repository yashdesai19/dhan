import { useMemo, useRef, useState } from 'react';
import { ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  Button,
  Card,
  ListCard,
  Logo,
  Money,
  Pill,
  ProgressBar,
  ProgressRing,
  SegmentedBar,
  Text,
  TextButton,
  TransactionRow,
} from '@/components';
import { useBudgets, useGoals } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useSessionStore } from '@/store/session';
import { layout, space, useColors } from '@/theme';
import { budgetStatus } from '@/utils/budget';
import { describeTransaction } from '@/utils/describe';
import { inr } from '@/utils/format';
import { goalProgress } from '@/utils/goals';
import { sortNewestFirst, spendingBreakdown } from '@/utils/summary';
import { monthName } from '@/utils/dates';

const PAGES = [
  {
    head: 'Track every rupee',
    body: 'Add an expense in about three seconds. Cash, cards, UPI and wallets, all in one place.',
  },
  {
    head: 'See where it goes',
    body: 'Clear breakdowns show which categories take the most, month after month.',
  },
  {
    head: 'Take control',
    body: 'Budgets, goals and split bills that nudge you before things slip, not after.',
  },
] as const;

function PageVisual({ index }: { index: number }) {
  const { today, month } = useToday();
  const { transactions, categories, accounts } = useMoneyData();
  const budgets = useBudgets().data ?? [];
  const goals = useGoals().data ?? [];

  const content = useMemo(() => {
    if (index === 0) {
      const pick = sortNewestFirst(transactions)
        .filter((t) => t.date === today || t.categoryId === 'salary')
        .slice(0, 3);
      return (
        <>
          <ListCard>
            {pick.map((t) => (
              <TransactionRow key={t.id} view={describeTransaction(t, categories, accounts, { today: '' })} />
            ))}
          </ListCard>
          <View style={styles.center}>
            <Pill label="Saved in 3 taps" tone="primary" />
          </View>
        </>
      );
    }
    if (index === 1) {
      const b = spendingBreakdown(transactions, month, categories);
      return (
        <Card>
          <Text variant="meta" color="muted">
            {monthName(month, true)} spending
          </Text>
          <Money amount={b.total} size="sm" />
          <SegmentedBar slices={b.slices} height={14} legendMode="percent" />
        </Card>
      );
    }
    const status = budgetStatus(
      budgets.find((x) => x.month === month),
      transactions,
      month,
      today,
    );
    const food = status?.categories.find((x) => x.categoryId === 'food');
    const transport = status?.categories.find((x) => x.categoryId === 'transport');
    const trip = goals.find((g) => g.id === 'kerala');
    const tp = trip ? goalProgress(trip, today) : null;
    return (
      <>
        <Card>
          {food ? (
            <>
              <View style={styles.between}>
                <Text variant="small">Food budget</Text>
                <Text variant="small" tabular>
                  <Text variant="small" weight="semibold">
                    {inr(food.spent)}
                  </Text>
                  <Text variant="small" color="muted">{` / ${inr(food.limit)}`}</Text>
                </Text>
              </View>
              <ProgressBar value={food.pct} height={8} />
            </>
          ) : null}
          {transport ? (
            <>
              <View style={styles.between}>
                <Text variant="small">Transport</Text>
                <Text variant="small" color="warnText" tabular>
                  {transport.pct}%
                </Text>
              </View>
              <ProgressBar value={transport.pct} tone="warn" height={8} />
            </>
          ) : null}
        </Card>
        {trip && tp ? (
          <Card>
            <View style={styles.ringRow}>
              <ProgressRing value={tp.pct} size={76} stroke={8} />
              <View style={styles.gap4}>
                <Text variant="section">{trip.name}</Text>
                <Text variant="small" color="muted">
                  {`${inr(tp.saved)} of ${inr(trip.target)} · ${tp.pct}%`}
                </Text>
              </View>
            </View>
          </Card>
        ) : null}
      </>
    );
  }, [index, transactions, categories, accounts, budgets, goals, today, month]);

  return <View style={styles.visual}>{content}</View>;
}

export function OnboardingScreen() {
  const c = useColors();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [page, setPage] = useState(0);
  const pager = useRef<ScrollView>(null);
  const complete = useSessionStore((s) => s.completeOnboarding);

  const goTo = (i: number) => {
    pager.current?.scrollTo({ x: i * width, animated: true });
    setPage(i);
  };
  const finish = (to: '/login' | '/sign-up') => {
    complete();
    router.replace(to);
  };
  const last = page === PAGES.length - 1;
  const p = PAGES[page] ?? PAGES[0];

  return (
    <View
      style={[
        styles.root,
        {
          backgroundColor: c.bg,
          paddingTop: insets.top + space[8],
          paddingBottom: Math.max(insets.bottom, 34),
        },
      ]}
    >
      <View style={[styles.header, { paddingHorizontal: layout.gutterAuth }]}>
        <Logo size={32} radius={9} />
        {!last ? (
          <TextButton label="Skip" color="muted" onPress={() => finish('/login')} />
        ) : (
          <View style={styles.skipSpace} />
        )}
      </View>
      <ScrollView
        ref={pager}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        style={styles.pager}
        onMomentumScrollEnd={(e) =>
          setPage(Math.round(e.nativeEvent.contentOffset.x / e.nativeEvent.layoutMeasurement.width))
        }
        accessibilityLabel={`Onboarding, page ${page + 1} of 3`}
      >
        {PAGES.map((_, i) => (
          <View key={i} style={[styles.page, { width, paddingHorizontal: layout.gutterAuth }]}>
            <PageVisual index={i} />
          </View>
        ))}
      </ScrollView>
      <View style={[styles.copy, { paddingHorizontal: layout.gutterAuth }]}>
        <View style={styles.dots} accessibilityLabel={`Page ${page + 1} of 3`} accessible>
          {PAGES.map((_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                { width: i === page ? 18 : 6, backgroundColor: i === page ? c.primary : c.btnBorder },
              ]}
            />
          ))}
        </View>
        <Text variant="displayXl" accessibilityRole="header">
          {p.head}
        </Text>
        <Text variant="bodyLg" color="muted">
          {p.body}
        </Text>
      </View>
      <View style={[styles.actions, { paddingHorizontal: layout.gutterAuth }]}>
        {last ? (
          <>
            <Button label="Get started" onPress={() => finish('/sign-up')} />
            <View style={styles.center}>
              <TextButton label="I already have an account" onPress={() => finish('/login')} />
            </View>
          </>
        ) : (
          <>
            <Button label="Next" onPress={() => goTo(page + 1)} />
            <View style={styles.skipSpace} />
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, gap: space[28] },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', minHeight: 44 },
  skipSpace: { height: 44 },
  pager: { flexGrow: 1 },
  page: { justifyContent: 'center' },
  visual: { gap: space[12] },
  copy: { gap: space[14] },
  dots: { flexDirection: 'row', gap: space[6] },
  dot: { height: 6, borderRadius: 3 },
  actions: { gap: space[6] },
  center: { alignItems: 'center' },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  ringRow: { flexDirection: 'row', alignItems: 'center', gap: space[16] },
  gap4: { gap: space[4] },
});
