import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Button,
  Card,
  EmptyState,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Money,
  Pill,
  ProgressBar,
  Screen,
  Text,
  TopBar,
  type IconName,
} from '@/components';
import { useBudgets } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import { budgetStatus } from '@/utils/budget';
import { time12, weekdayDayMonth } from '@/utils/dates';
import { describeTransaction } from '@/utils/describe';
import { inr, plural } from '@/utils/format';

function Row({
  icon,
  label,
  value,
  muted,
}: {
  icon: IconName;
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <ListRow
      leading={<IconTile icon={icon} size="sm" />}
      title={label}
      trailing={
        <Text
          variant="body"
          weight="medium"
          color={muted ? 'muted' : 'ink'}
          numberOfLines={1}
          style={styles.value}
        >
          {value}
        </Text>
      }
      accessibilityLabel={`${label}, ${value}`}
    />
  );
}

export function TransactionDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { today, month } = useToday();
  const money = useMoneyData();
  const budgets = useBudgets();
  const t = money.transactions.find((x) => x.id === id);

  if (!money.loading && !t) {
    return (
      <Screen>
        <TopBar />
        <EmptyState
          icon="receipt"
          title="This transaction is gone"
          body="It may have been deleted. Your balances are up to date."
        />
      </Screen>
    );
  }
  if (!t)
    return (
      <Screen>
        <TopBar />
      </Screen>
    );

  const v = describeTransaction(t, money.categories, money.accounts, { today });
  const cat = money.categories.find((c) => c.id === t.categoryId);
  const acct = money.accounts.find((a) => a.id === t.accountId);
  const to = money.accounts.find((a) => a.id === t.toAccountId);
  const status = budgetStatus(
    budgets.data?.find((b) => b.month === month),
    money.transactions,
    month,
    today,
  );
  const catBudget =
    t.type === 'expense' ? status?.categories.find((c) => c.categoryId === t.categoryId) : undefined;
  const typeLabel = { expense: 'Expense', income: 'Income', transfer: 'Transfer', split: 'Split' }[t.type];
  const typeTone = t.type === 'expense' ? 'expense' : t.type === 'income' ? 'income' : 'neutral';
  const editable = t.type === 'expense' || t.type === 'income';

  return (
    <Screen gap={space[20]}>
      <TopBar
        trailing={
          editable ? (
            <IconButton
              icon="edit"
              accessibilityLabel="Edit transaction"
              onPress={() => router.push(`/transactions/${t.id}/edit`)}
            />
          ) : undefined
        }
      />
      <View style={styles.hero} accessible accessibilityLabel={v.a11y}>
        <IconTile
          icon={v.icon}
          size="xl"
          tone={v.tone === 'income' ? 'income' : v.tone === 'primary' ? 'primary' : 'neutral'}
        />
        <Text variant="profileName" weight="medium" style={styles.heroTitle}>
          {t.title}
        </Text>
        <Money
          amount={t.amount}
          size="hero60"
          sign={t.type === 'expense' ? 'minus' : t.type === 'income' ? 'plus' : 'none'}
          color={t.type === 'income' ? 'income' : 'ink'}
        />
        <View style={styles.pills}>
          {cat ? <Pill label={cat.short} /> : null}
          <Pill label={typeLabel} tone={typeTone} />
        </View>
      </View>
      <ListCard>
        {t.type === 'transfer' ? (
          <Row icon="bank" label="From" value={acct?.name ?? ''} />
        ) : (
          <Row icon="bank" label="Account" value={acct?.name ?? ''} />
        )}
        {t.type === 'transfer' ? <Row icon="cash" label="To" value={to?.name ?? ''} /> : null}
        <Row
          icon="calendar"
          label="Date"
          value={`${weekdayDayMonth(t.date)}${t.time ? `, ${time12(t.time)}` : ''}`}
        />
        {t.type === 'split' && t.lentAmount ? (
          <Row icon="users" label="You lent" value={inr(t.lentAmount)} />
        ) : null}
        <Row
          icon="repeat"
          label="Repeats"
          value={t.repeats === 'monthly' ? 'Monthly' : 'Never'}
          muted={t.repeats !== 'monthly'}
        />
        <Row icon="note" label="Note" value={t.note || t.detail || 'None'} muted={!t.note && !t.detail} />
        <ListRow
          leading={<IconTile icon="camera" size="sm" />}
          title="Receipt"
          trailing={
            <Text
              variant="body"
              weight="semibold"
              color="primary"
              accessibilityHint="Not available in this preview"
            >
              Add photo
            </Text>
          }
        />
      </ListCard>
      {catBudget && cat ? (
        <Card gap={space[10]}>
          <View style={styles.between}>
            <Text variant="small">{`${cat.short} this month`}</Text>
            <Text variant="small" tabular>
              <Text variant="small" weight="semibold">
                {inr(catBudget.spent)}
              </Text>
              <Text variant="small" color="muted">{` / ${inr(catBudget.limit)}`}</Text>
            </Text>
          </View>
          <ProgressBar
            value={catBudget.pct}
            tone={catBudget.tone === 'ok' ? 'primary' : catBudget.tone === 'warn' ? 'warn' : 'expense'}
          />
          <Text variant="meta" color="muted">
            {catBudget.left >= 0
              ? `${inr(catBudget.left)} left for ${status && status.daysLeft === 1 ? 'the rest of the month' : `the next ${plural(status?.daysLeft ?? 0, 'day', 'days')}`}`
              : `${inr(-catBudget.left)} over this month`}
          </Text>
        </Card>
      ) : null}
      {t.type === 'expense' ? (
        <View style={styles.actions}>
          <Button
            label="Split this"
            kind="secondary"
            size="md"
            icon="users"
            grow
            onPress={() =>
              router.push({ pathname: '/add/split', params: { amount: String(t.amount), title: t.title } })
            }
          />
          <Button
            label="Delete"
            kind="secondary"
            size="md"
            icon="trash"
            grow
            onPress={() => router.push(`/transactions/${t.id}/delete`)}
          />
        </View>
      ) : editable ? (
        <Button
          label="Delete"
          kind="secondary"
          size="md"
          icon="trash"
          onPress={() => router.push(`/transactions/${t.id}/delete`)}
        />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: space[10], paddingTop: space[4], paddingBottom: space[6] },
  heroTitle: { paddingTop: space[4] },
  pills: { flexDirection: 'row', gap: space[8] },
  value: { maxWidth: '60%', textAlign: 'right' },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  actions: { flexDirection: 'row', gap: space[10] },
});
