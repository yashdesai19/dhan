import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  DateBadge,
  EmptyState,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Money,
  Pill,
  ProgressBar,
  RowAmount,
  Screen,
  SectionLabel,
  SegmentedControl,
  Skeleton,
  Text,
  TopBar,
} from '@/components';
import { useAccounts, useRecurring } from '@/data/queries';
import { useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import type { Recurring } from '@/types/domain';
import { monthName, relativeDay, shiftMonth } from '@/utils/dates';
import { inr, percent, plural } from '@/utils/format';
import { incomingInMonth, outgoingInMonth, subscriptions, upcomingSplit } from '@/utils/recurring';

type Filter = 'all' | 'bills' | 'emis' | 'income';

export function RecurringScreen() {
  const router = useRouter();
  const { today, month } = useToday();
  const next = shiftMonth(month, 1);
  const recurring = useRecurring();
  const accounts = useAccounts().data ?? [];
  const [filter, setFilter] = useState<Filter>('all');

  const view = useMemo(() => {
    const items = recurring.data ?? [];
    return {
      out: outgoingInMonth(items, next),
      inc: incomingInMonth(items, next),
      split: upcomingSplit(items, today, next),
      subs: subscriptions(items),
    };
  }, [recurring.data, today, next]);

  const acctName = (id: string) => accounts.find((a) => a.id === id)?.name ?? '';
  const sub = (r: Recurring) =>
    r.note ??
    (r.emi
      ? `${r.emi.paid} of ${r.emi.total} paid · ${inr(r.emi.remaining)} left`
      : `${r.kind === 'subscription' ? 'Subscription' : 'Bills'} · ${acctName(r.accountId)}`);
  const show = (r: Recurring) =>
    filter === 'all' || (filter === 'bills' && r.kind === 'bill') || (filter === 'emis' && r.kind === 'emi');
  const row = (r: Recurring) => {
    const soon = relativeDay(r.nextDate, today) === 'Tomorrow';
    const body = (
      <ListRow
        leading={<DateBadge date={r.nextDate} tone={soon ? 'warn' : undefined} />}
        title={r.name}
        subtitle={sub(r)}
        trailing={
          soon ? (
            <View style={styles.right}>
              <RowAmount value={inr(r.amount)} />
              <Pill label="Tomorrow" tone="warn" small />
            </View>
          ) : (
            <RowAmount value={inr(r.amount)} />
          )
        }
        accessibilityLabel={`${r.name}, ${inr(r.amount)}, due ${relativeDay(r.nextDate, today)}`}
      />
    );
    if (!r.emi) return <View key={r.id}>{body}</View>;
    return (
      <View key={r.id} style={styles.emi}>
        {body}
        <ProgressBar
          value={percent(r.emi.paid, r.emi.total)}
          accessibilityLabel={`${r.emi.paid} of ${r.emi.total} EMIs paid`}
        />
      </View>
    );
  };

  const soon = view.split.soon.filter(show);
  const later = view.split.later.filter(show);

  return (
    <Screen gap={space[20]}>
      <TopBar
        title="Recurring"
        trailing={<IconButton icon="plus" accessibilityLabel="Add recurring payment" />}
      />
      <View style={styles.gap6}>
        <Text variant="small" color="muted">{`Going out in ${monthName(next, true)}`}</Text>
        {recurring.isPending ? (
          <Skeleton width={200} height={56} />
        ) : (
          <Money amount={view.out.total} size="hero" />
        )}
        <Text
          variant="meta"
          color="muted"
        >{`${plural(view.out.count, 'payment', 'payments')} · ${inr(view.inc.total)} coming in`}</Text>
      </View>
      <SegmentedControl
        accessibilityLabel="Filter recurring"
        value={filter}
        onChange={setFilter}
        options={[
          { value: 'all', label: 'All' },
          { value: 'bills', label: 'Bills' },
          { value: 'emis', label: 'EMIs' },
          { value: 'income', label: 'Income' },
        ]}
      />
      {filter !== 'income' ? (
        <>
          {soon.length ? (
            <View style={styles.gap10}>
              <SectionLabel>{`Next 7 days · ${inr(soon.reduce((s, r) => s + r.amount, 0))}`}</SectionLabel>
              <ListCard>{soon.map(row)}</ListCard>
            </View>
          ) : null}
          {later.length ? (
            <View style={styles.gap10}>
              <SectionLabel>{`Later in ${monthName(next, true)}`}</SectionLabel>
              <ListCard>{later.map(row)}</ListCard>
            </View>
          ) : null}
          {!soon.length && !later.length ? (
            <EmptyState
              icon="repeat"
              title="Nothing due"
              body="No payments of this type are coming up this month."
            />
          ) : null}
          {filter === 'all' ? (
            <ListCard>
              <ListRow
                leading={<IconTile icon="film" />}
                title="Subscriptions"
                subtitle={`${view.subs.count} active · renew through ${monthName(next, true)}`}
                trailing={<RowAmount value={`${inr(view.subs.monthly)}/mo`} />}
                chevron
                pad={14}
                onPress={() => router.push('/recurring/subscriptions')}
              />
            </ListCard>
          ) : null}
        </>
      ) : null}
      {filter === 'all' || filter === 'income' ? (
        <View style={styles.gap10}>
          <SectionLabel>Recurring income</SectionLabel>
          <ListCard>
            {view.inc.items.map((r) => (
              <ListRow
                key={r.id}
                leading={<DateBadge date={r.nextDate} />}
                title={r.name}
                subtitle={`Into ${acctName(r.accountId)}`}
                trailing={<RowAmount value={inr(r.amount, 'plus')} color="income" />}
              />
            ))}
          </ListCard>
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap6: { gap: space[6] },
  gap10: { gap: space[10] },
  right: { alignItems: 'flex-end', gap: space[4] },
  emi: { gap: space[8], paddingBottom: space[12] },
});
