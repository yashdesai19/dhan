import { useMemo, useState } from 'react';
import { StyleSheet } from 'react-native';

import {
  Button,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Screen,
  SegmentedControl,
  Text,
  TopBar,
} from '@/components';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { space } from '@/theme';
import type { CategoryKind } from '@/types/domain';
import { inr } from '@/utils/format';
import { inMonth } from '@/utils/summary';

export function CategoriesScreen() {
  const { month } = useToday();
  const money = useMoneyData();
  const [kind, setKind] = useState<CategoryKind>('expense');

  const rows = useMemo(() => {
    const txs = inMonth(money.transactions, month).filter((t) => t.type === kind);
    return money.categories
      .filter((c) => c.kind === kind)
      .map((c) => {
        const mine = txs.filter((t) => t.categoryId === c.id);
        return { c, count: mine.length, total: mine.reduce((s, t) => s + t.amount, 0) };
      });
  }, [money.transactions, money.categories, month, kind]);

  return (
    <Screen gap={space[18]}>
      <TopBar title="Categories" trailing={<IconButton icon="plus" accessibilityLabel="Add category" />} />
      <SegmentedControl
        accessibilityLabel="Category type"
        value={kind}
        onChange={setKind}
        options={[
          { value: 'expense', label: 'Expense' },
          { value: 'income', label: 'Income' },
        ]}
      />
      <ListCard>
        {rows.map(({ c, count, total }) => (
          <ListRow
            key={c.id}
            leading={<IconTile icon={c.icon} />}
            title={c.name}
            subtitle={count ? `${count} this month · ${inr(total)}` : 'None this month'}
            chevron
            accessibilityHint="Editing categories is not available in this preview"
          />
        ))}
      </ListCard>
      <Button
        label="+ Custom category"
        kind="dashed"
        size="md"
        accessibilityHint="Not available in this preview"
      />
      <Text variant="meta" color="muted" style={styles.note}>
        Deleting a category moves its transactions to “Other”. Nothing is lost.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({ note: { textAlign: 'center' } });
