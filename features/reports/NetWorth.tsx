import { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';

import {
  AreaLineChart,
  Card,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Money,
  Pill,
  RowAmount,
  Screen,
  SectionLabel,
  Skeleton,
  Text,
  TopBar,
} from '@/components';
import { useAssets, useHistory, useLiabilities } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import { monthName, shiftMonth } from '@/utils/dates';
import { inr } from '@/utils/format';
import { netWorth, netWorthSeries } from '@/utils/netWorth';

export function NetWorthScreen() {
  const { month } = useToday();
  const money = useMoneyData();
  const assets = useAssets();
  const liabilities = useLiabilities();
  const history = useHistory();

  const view = useMemo(() => {
    const nw = netWorth(money.accounts, assets.data ?? [], liabilities.data ?? []);
    const series = netWorthSeries(history.data ?? [], { month, value: nw.net });
    const prev = series.at(-2)?.value ?? nw.net;
    return { nw, series, change: nw.net - prev };
  }, [money.accounts, assets.data, liabilities.data, history.data, month]);

  const loading = money.loading || assets.isPending || liabilities.isPending;
  return (
    <Screen gap={space[18]}>
      <TopBar
        title="Net worth"
        trailing={<IconButton icon="plus" accessibilityLabel="Add asset or loan" />}
      />
      <View style={styles.gap8}>
        <Text variant="small" color="muted">
          What you own minus what you owe
        </Text>
        {loading ? <Skeleton width={220} height={56} /> : <Money amount={view.nw.net} size="hero" />}
        <Pill
          label={`${inr(view.change, 'plus')} since ${monthName(shiftMonth(month, -1), true)}`}
          tone={view.change >= 0 ? 'income' : 'expense'}
        />
      </View>
      {history.data ? (
        <Card gap={space[8]}>
          <AreaLineChart
            values={view.series.map((p) => p.value)}
            labels={view.series.map((p) => monthName(p.month))}
          />
        </Card>
      ) : null}
      <SectionLabel
        right={
          <Text variant="body" weight="semibold" tabular>
            {inr(view.nw.totalAssets)}
          </Text>
        }
      >
        Assets
      </SectionLabel>
      <ListCard>
        {view.nw.assets.map((r) => (
          <ListRow
            key={r.id}
            leading={<IconTile icon={r.icon} />}
            title={r.name}
            subtitle={r.note}
            trailing={<RowAmount value={inr(r.value)} />}
          />
        ))}
      </ListCard>
      <SectionLabel
        right={
          <Text variant="body" weight="semibold" tabular color="expense">
            {inr(view.nw.totalLiabilities)}
          </Text>
        }
      >
        Loans and cards
      </SectionLabel>
      <ListCard>
        {view.nw.liabilities.map((r) => (
          <ListRow
            key={r.id}
            leading={<IconTile icon={r.icon} tone="expense" />}
            title={r.name}
            subtitle={r.note}
            trailing={<RowAmount value={inr(r.value)} />}
          />
        ))}
      </ListCard>
      <Text variant="meta" color="muted">
        Investments and gold are updated by you, not synced. Tap any item to update its value.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({ gap8: { gap: space[8] } });
