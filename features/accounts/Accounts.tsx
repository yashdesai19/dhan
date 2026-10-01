import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Icon,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Money,
  ProgressBar,
  RowAmount,
  Screen,
  SectionLabel,
  Skeleton,
  Text,
  TopBar,
  Touchable,
  type IconName,
} from '@/components';
import { useMoneyData } from '@/features/shared/hooks';
import { iconSize, radius, space, useColors, type ColorName } from '@/theme';
import type { Account } from '@/types/domain';
import { dayMonth } from '@/utils/dates';
import { inr, percent, plural } from '@/utils/format';
import { netBalance } from '@/utils/summary';

export const ACCOUNT_ICON: Record<Account['type'], IconName> = {
  bank: 'bank',
  savings: 'coin',
  cash: 'cash',
  wallet: 'wallet',
  credit: 'card',
  custom: 'tag',
};

export function accountSubtitle(a: Account): string {
  if (a.type === 'credit')
    return [a.dueDate ? `Due ${dayMonth(a.dueDate)}` : '', `limit ${inr(a.creditLimit ?? 0)}`]
      .filter(Boolean)
      .join(' · ');
  return a.last4 ? `${a.subtitle} · ending ${a.last4}` : a.subtitle;
}

export function AccountsScreen() {
  const c = useColors();
  const router = useRouter();
  const { accounts, loading } = useMoneyData();
  const [showArchived, setShowArchived] = useState(false);

  const view = useMemo(() => {
    const live = accounts.filter((a) => !a.archived);
    const banks = live.filter((a) => a.type === 'bank' || a.type === 'savings');
    const cash = live.filter((a) => a.type === 'cash' || a.type === 'wallet' || a.type === 'custom');
    const credit = live.filter((a) => a.type === 'credit');
    const positive = [...banks, ...cash].reduce((s, a) => s + Math.max(0, a.balance), 0);
    const cashTotal = cash.reduce((s, a) => s + Math.max(0, a.balance), 0);
    const tokens: ColorName[] = ['chart1', 'chart3', 'chart4', 'chart5'];
    const segments = [
      ...banks.map((a, i) => ({
        id: a.id,
        value: Math.max(0, a.balance),
        color: tokens[i % tokens.length] ?? 'chart1',
      })),
      { id: 'cash', value: cashTotal, color: 'chart2' as ColorName },
    ].filter((s) => s.value > 0);
    return {
      balance: netBalance(accounts),
      banks,
      cash,
      credit,
      segments,
      positive,
      bankShare: percent(positive - cashTotal, positive),
      cashShare: percent(cashTotal, positive),
      archived: accounts.filter((a) => a.archived),
    };
  }, [accounts]);

  const row = (a: Account) => (
    <ListRow
      key={a.id}
      leading={<IconTile icon={ACCOUNT_ICON[a.type]} tone={a.type === 'credit' ? 'expense' : 'neutral'} />}
      title={a.name}
      subtitle={accountSubtitle(a)}
      trailing={<RowAmount value={inr(a.balance)} color={a.balance < 0 ? 'expense' : 'ink'} />}
      chevron
      onPress={() => router.push(`/accounts/${a.id}`)}
    />
  );

  return (
    <Screen gap={space[22]}>
      <TopBar
        title="Accounts"
        trailing={
          <IconButton
            icon="plus"
            accessibilityLabel="Add account"
            onPress={() => router.push('/accounts/edit')}
          />
        }
      />
      <View style={styles.gap8}>
        <Text variant="small" color="muted">
          {`Net balance · ${plural(view.balance.count, 'account', 'accounts')}`}
        </Text>
        {loading ? <Skeleton width={220} height={56} /> : <Money amount={view.balance.total} size="hero" />}
        <View
          style={styles.comp}
          accessible
          accessibilityLabel={`Bank ${view.bankShare} percent, cash and wallets ${view.cashShare} percent`}
        >
          {view.segments.map((s) => (
            <View
              key={s.id}
              style={{ flex: s.value, height: 8, borderRadius: 3, backgroundColor: c[s.color] }}
            />
          ))}
        </View>
        <View style={styles.legend}>
          <Text variant="caption" color="muted">{`● Bank ${view.bankShare}%`}</Text>
          <Text variant="caption" color="muted">{`● Cash and wallets ${view.cashShare}%`}</Text>
        </View>
      </View>
      {view.banks.length ? (
        <View style={styles.gap10}>
          <SectionLabel>Bank</SectionLabel>
          <ListCard>{view.banks.map(row)}</ListCard>
        </View>
      ) : null}
      {view.cash.length ? (
        <View style={styles.gap10}>
          <SectionLabel>Cash and wallets</SectionLabel>
          <ListCard>{view.cash.map(row)}</ListCard>
        </View>
      ) : null}
      {view.credit.length ? (
        <View style={styles.gap10}>
          <SectionLabel>Credit</SectionLabel>
          <ListCard>
            {view.credit.map((a) => {
              const used = percent(Math.max(0, -a.balance), a.creditLimit ?? 1);
              return (
                <View key={a.id} style={styles.creditRow}>
                  {row(a)}
                  <ProgressBar
                    value={used}
                    tone="expense"
                    accessibilityLabel={`${used} percent of your limit used`}
                  />
                  <Text variant="meta" color="muted">
                    {`${used}% of your limit used`}
                  </Text>
                </View>
              );
            })}
          </ListCard>
        </View>
      ) : null}
      {view.archived.length ? (
        <View style={styles.gap10}>
          <Touchable
            onPress={() => setShowArchived(!showArchived)}
            accessibilityLabel={`Archived accounts, ${view.archived.length}`}
            accessibilityState={{ expanded: showArchived }}
            style={styles.archived}
          >
            <Icon name="archive" size={iconSize.md} color="muted" />
            <Text variant="small" weight="medium" color="muted">
              {`Archived accounts (${view.archived.length})`}
            </Text>
          </Touchable>
          {showArchived ? (
            <ListCard>
              {view.archived.map((a) => (
                <ListRow
                  key={a.id}
                  leading={<IconTile icon={ACCOUNT_ICON[a.type]} />}
                  title={a.name}
                  subtitle="Archived · not in totals"
                  trailing={<RowAmount value={inr(a.balance)} color="muted" />}
                />
              ))}
            </ListCard>
          ) : null}
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap8: { gap: space[8] },
  gap10: { gap: space[10] },
  comp: {
    flexDirection: 'row',
    gap: 3,
    height: 8,
    marginTop: space[8],
    borderRadius: radius.skeleton,
    overflow: 'hidden',
  },
  legend: { flexDirection: 'row', gap: space[14] },
  creditRow: { gap: space[10], paddingBottom: space[12] },
  archived: { flexDirection: 'row', alignItems: 'center', gap: space[8], alignSelf: 'center', minHeight: 44 },
});
