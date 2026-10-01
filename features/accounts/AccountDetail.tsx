import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import {
  Button,
  EmptyState,
  IconButton,
  KpiTile,
  ListCard,
  Money,
  Screen,
  SectionHeader,
  Text,
  TopBar,
  TransactionRow,
} from '@/components';
import { useArchiveAccount } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useFiltersStore } from '@/store/filters';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { weekdayDayMonth } from '@/utils/dates';
import { describeTransaction } from '@/utils/describe';
import { inr } from '@/utils/format';
import { accountActivity, sortNewestFirst } from '@/utils/summary';
import { accountSubtitle } from './Accounts';

export function AccountDetailScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { today, month } = useToday();
  const money = useMoneyData();
  const archive = useArchiveAccount();
  const show = useToastStore((s) => s.show);
  const account = money.accounts.find((a) => a.id === id);

  const view = useMemo(() => {
    const kpis = accountActivity(money.transactions, id ?? '', month);
    const recent = sortNewestFirst(
      money.transactions.filter((t) => t.accountId === id || t.toAccountId === id),
    ).slice(0, 5);
    return { kpis, recent };
  }, [money.transactions, id, month]);

  if (!account) {
    return (
      <Screen>
        <TopBar title="Account" />
        {money.loading ? null : (
          <EmptyState icon="bank" title="Account not found" body="It may have been removed." />
        )}
      </Screen>
    );
  }

  return (
    <Screen gap={space[20]}>
      <TopBar
        title={account.name}
        trailing={
          <IconButton
            icon="dots"
            accessibilityLabel="More options"
            onPress={() => router.push({ pathname: '/accounts/edit', params: { id: account.id } })}
          />
        }
      />
      <View style={styles.gap6}>
        <Text variant="small" color="muted">
          {accountSubtitle(account)}
        </Text>
        <Money amount={account.balance} size="hero" color={account.balance < 0 ? 'expense' : 'ink'} />
      </View>
      <View style={styles.kpis}>
        <KpiTile label="In" value={inr(view.kpis.in)} tone="income" />
        <KpiTile label="Out" value={inr(view.kpis.out)} />
        <KpiTile label="Moved" value={inr(view.kpis.moved)} />
      </View>
      <View style={styles.actions}>
        <Button
          label="Transfer"
          kind="secondary"
          size="sm"
          icon="transfer"
          grow
          onPress={() => router.push('/add/transfer')}
        />
        <Button
          label="Edit"
          kind="secondary"
          size="sm"
          icon="edit"
          grow
          onPress={() => router.push({ pathname: '/accounts/edit', params: { id: account.id } })}
        />
        <Button
          label="Archive"
          kind="secondary"
          size="sm"
          icon="archive"
          grow
          loading={archive.isPending}
          onPress={() =>
            archive.mutate(account.id, {
              onSuccess: () => {
                router.back();
                show({
                  message: `${account.name} archived`,
                  actionLabel: 'Undo',
                  placement: 'bottom',
                  onAction: () => void undo.archivedAccount(qc, account),
                });
              },
            })
          }
        />
      </View>
      <SectionHeader
        title="Recent activity"
        action="See all"
        onAction={() => {
          useFiltersStore.getState().set({ accountIds: [account.id], quick: 'All' });
          router.navigate('/activity');
        }}
      />
      {view.recent.length ? (
        <ListCard>
          {view.recent.map((t) => {
            const v = describeTransaction(t, money.categories, money.accounts, {
              today,
              quietTransfers: true,
            });
            const title =
              t.type === 'transfer'
                ? t.accountId === account.id
                  ? `To ${money.accounts.find((a) => a.id === t.toAccountId)?.name ?? ''}`
                  : `From ${money.accounts.find((a) => a.id === t.accountId)?.name ?? ''}`
                : t.title;
            return (
              <TransactionRow
                key={t.id}
                view={{
                  ...v,
                  title,
                  subtitle: `${weekdayDayMonth(t.date)}${t.type === 'transfer' ? ' · transfer' : ''}`,
                }}
                onPress={() => router.push(`/transactions/${t.id}`)}
              />
            );
          })}
        </ListCard>
      ) : (
        <Text variant="small" color="muted">
          No activity in this account yet.
        </Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap6: { gap: space[6] },
  kpis: { flexDirection: 'row', gap: space[10] },
  actions: { flexDirection: 'row', gap: space[10] },
});
