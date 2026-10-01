import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Banner,
  Card,
  DailyBars,
  EmptyState,
  IconButton,
  ListCard,
  Money,
  ProgressBar,
  Screen,
  SectionHeader,
  Text,
  TopBar,
  TransactionRow,
} from '@/components';
import { useBudgets, useHistory } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import { budgetStatus, categoryHistory, projectedSpend } from '@/utils/budget';
import { daysInMonth, dayMonth, monthName, parts, weekdayDayMonth } from '@/utils/dates';
import { describeTransaction } from '@/utils/describe';
import { inr } from '@/utils/format';
import { inMonth, sortNewestFirst } from '@/utils/summary';

export function CategoryBudgetScreen() {
  const router = useRouter();
  const { category } = useLocalSearchParams<{ category: string }>();
  const { today, month } = useToday();
  const money = useMoneyData();
  const budgets = useBudgets();
  const history = useHistory();
  const cat = money.categories.find((c) => c.id === category);

  const view = useMemo(() => {
    const status = budgetStatus(
      budgets.data?.find((b) => b.month === month),
      money.transactions,
      month,
      today,
    );
    const s = status?.categories.find((c) => c.categoryId === category);
    const txs = sortNewestFirst(
      inMonth(money.transactions, month).filter((t) => t.type === 'expense' && t.categoryId === category),
    );
    const days = Array.from({ length: daysInMonth(month) }, () => 0);
    for (const t of txs) {
      const d = parts(t.date).d - 1;
      days[d] = (days[d] ?? 0) + t.amount;
    }
    const hist = categoryHistory(history.data ?? [], money.transactions, category ?? '', month);
    const projected = s ? projectedSpend(s.spent, month, today) : 0;
    return { status, s, txs, days, hist, projected };
  }, [budgets.data, money.transactions, history.data, month, today, category]);

  if (!cat || !view.s) {
    return (
      <Screen>
        <TopBar title={cat?.short ?? 'Budget'} />
        {money.loading ? null : (
          <EmptyState
            icon="pie"
            title="No budget for this category"
            body="Set a monthly limit and DHAN will warn you before you go over."
          />
        )}
      </Screen>
    );
  }

  const { s, status, projected } = view;
  const over = projected - s.limit;
  const tone = s.tone === 'over' ? 'expense' : s.tone === 'warn' ? 'warn' : 'primary';
  const last = `${daysInMonth(month)} ${monthName(month)}`;

  return (
    <Screen gap={space[20]}>
      <TopBar
        title={cat.short}
        trailing={
          <IconButton
            icon="edit"
            accessibilityLabel="Edit budget"
            onPress={() => router.push(`/budget/${cat.id}/edit`)}
          />
        }
      />
      <View style={styles.gap12}>
        <View style={styles.leftRow}>
          <Money amount={Math.max(0, s.left)} size="hero" />
          <Text variant="body" color="muted">{`left of ${inr(s.limit)}`}</Text>
        </View>
        <ProgressBar value={s.pct} tone={tone} height={10} accessibilityLabel={`${s.pct} percent used`} />
        <View style={styles.between}>
          <Text variant="meta" color="muted" tabular>{`${inr(s.spent)} spent`}</Text>
          <Text variant="meta" color="muted" tabular>{`${s.pct}%`}</Text>
        </View>
      </View>
      {over > 0 && s.tone !== 'over' ? (
        <Banner icon="alert" tone="warn">
          {`At your usual pace you’ll go about ${inr(Math.round(over / 50) * 50)} over by ${last}. Try metro or pool rides this week.`}
        </Banner>
      ) : s.tone !== 'ok' ? (
        <Banner icon="alert" tone="warn">
          {s.tone === 'over'
            ? `You’re ${inr(-s.left)} over your ${cat.short} budget this month.`
            : `${cat.short} is at ${s.pct}%. ${inr(s.left)} left for ${status && status.daysLeft > 1 ? `the next ${status.daysLeft} days` : 'the rest of the month'}.`}
        </Banner>
      ) : null}
      <Card>
        <View style={styles.between}>
          <Text variant="section">Daily spending</Text>
          <Text variant="meta" color="muted">
            {monthName(month)}
          </Text>
        </View>
        <DailyBars
          values={view.days}
          highlight={parts(today).d - 1}
          labels={[`1 ${monthName(month)}`, `15 ${monthName(month)}`, last]}
        />
      </Card>
      <Card gap={space[8]}>
        <View style={styles.hist}>
          {view.hist.map((h) => (
            <View
              key={h.month}
              style={styles.histCol}
              accessible
              accessibilityLabel={`${monthName(h.month, true)} ${inr(h.spent)}`}
            >
              <Text variant="caption" color="muted">
                {monthName(h.month, true)}
              </Text>
              <Text variant="body" weight="semibold" tabular color={h.spent > s.limit ? 'expense' : 'ink'}>
                {inr(h.spent)}
              </Text>
            </View>
          ))}
        </View>
      </Card>
      <SectionHeader title="Where it went" />
      {view.txs.length ? (
        <ListCard>
          {view.txs.map((t) => {
            const v = describeTransaction(t, money.categories, money.accounts, { today });
            const acct = money.accounts.find((a) => a.id === t.accountId)?.name;
            return (
              <TransactionRow
                key={t.id}
                view={{ ...v, subtitle: [weekdayDayMonth(t.date), acct].filter(Boolean).join(' · ') }}
                onPress={() => router.push(`/transactions/${t.id}`)}
              />
            );
          })}
        </ListCard>
      ) : (
        <Text
          variant="small"
          color="muted"
        >{`No ${cat.short.toLowerCase()} spending since ${dayMonth(`${month}-01`)}.`}</Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap12: { gap: space[12] },
  leftRow: { flexDirection: 'row', alignItems: 'baseline', gap: space[10], flexWrap: 'wrap' },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  hist: { flexDirection: 'row', gap: space[8] },
  histCol: { flex: 1, gap: space[4] },
});
