import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';

import {
  Banner,
  IconButton,
  LetterTile,
  ListCard,
  ListRow,
  Money,
  Screen,
  Skeleton,
  Text,
  TopBar,
} from '@/components';
import { useAccounts, useInsights, useRecurring } from '@/data/queries';
import { space } from '@/theme';
import { dayMonth } from '@/utils/dates';
import { inr, plural } from '@/utils/format';
import { subscriptions } from '@/utils/recurring';

export function SubscriptionsScreen() {
  const recurring = useRecurring();
  const accounts = useAccounts().data ?? [];
  const insights = useInsights();
  const subs = useMemo(() => subscriptions(recurring.data ?? []), [recurring.data]);
  const acct = (id: string) => accounts.find((a) => a.id === id)?.name.replace('Credit Card', 'Card') ?? '';

  return (
    <Screen gap={space[20]}>
      <TopBar
        title="Subscriptions"
        trailing={<IconButton icon="plus" accessibilityLabel="Add subscription" />}
      />
      <View style={styles.gap6}>
        <Text variant="small" color="muted">
          {plural(subs.count, 'subscription', 'subscriptions')}
        </Text>
        <View style={styles.row}>
          {recurring.isPending ? (
            <Skeleton width={160} height={56} />
          ) : (
            <Money amount={subs.monthly} size="hero" />
          )}
          <Text variant="body" color="muted">
            a month
          </Text>
        </View>
        <Text variant="meta" color="muted">{`${inr(subs.yearly)} a year`}</Text>
      </View>
      {insights.data ? <Banner icon="sparkle">{insights.data.subscriptions}</Banner> : null}
      <ListCard>
        {subs.list.map((r) => (
          <ListRow
            key={r.id}
            leading={<LetterTile letter={r.letter ?? r.name.slice(0, 1)} />}
            title={r.name}
            subtitle={`Renews ${dayMonth(r.nextDate)} · ${acct(r.accountId)}`}
            trailing={
              <View style={styles.right}>
                <Text variant="body" weight="semibold" tabular>
                  {inr(r.amount)}
                </Text>
                <Text variant="caption" color="muted">
                  a month
                </Text>
              </View>
            }
          />
        ))}
      </ListCard>
      <Text variant="meta" color="muted">
        DHAN reminds you 2 days before each renewal. Change this in Notifications.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap6: { gap: space[6] },
  row: { flexDirection: 'row', alignItems: 'baseline', gap: space[10] },
  right: { alignItems: 'flex-end', gap: 2 },
});
