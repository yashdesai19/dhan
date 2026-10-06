import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Button, ChipGroup, SectionLabel, Sheet, TextButton, TextField, useSheet } from '@/components';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import {
  applyFilters,
  defaultFilters,
  useFiltersStore,
  type DateRange,
  type TxFilters,
} from '@/store/filters';
import { space } from '@/theme';
import type { TxType } from '@/types/domain';
import { groupIN, plural } from '@/utils/format';
import { expenseCategoryIds } from '@/utils/summary';

const RANGES: DateRange[] = ['This month', 'Last month', '3 months', 'Custom'];
const TYPES: { value: TxType; label: string }[] = [
  { value: 'expense', label: 'Expense' },
  { value: 'income', label: 'Income' },
  { value: 'transfer', label: 'Transfer' },
  { value: 'split', label: 'Split' },
];

function Body({ f, setF }: { f: TxFilters; setF: (u: (x: TxFilters) => TxFilters) => void }) {
  const { close } = useSheet();
  const { today } = useToday();
  const money = useMoneyData();
  const stored = useFiltersStore((s) => s.filters);
  const apply = useFiltersStore((s) => s.set);
  const patch = (p: Partial<TxFilters>) => setF((x) => ({ ...x, ...p }));

  const count = useMemo(
    () => applyFilters(money.transactions, { ...f, quick: 'All' }, today).length,
    [money.transactions, f, today],
  );
  const catIds = expenseCategoryIds(money.categories, [
    'Food',
    'Transport',
    'Shopping',
    'Bills',
    'Health',
    'Fun',
  ]);
  const cats = money.categories.filter((c) => catIds.includes(c.id));
  const accts = money.accounts.filter((a) => !a.archived);
  const money$ = (v: string) =>
    v.replace(/[^\d]/g, '') ? `₹${groupIN(Number(v.replace(/[^\d]/g, '')))}` : '';

  return (
    <>
      <View style={styles.group}>
        <SectionLabel>Date</SectionLabel>
        <ChipGroup
          options={RANGES.map((r) => ({ value: r, label: r }))}
          selected={[f.range]}
          onChange={([v]) => v && patch({ range: v })}
        />
      </View>
      <View style={styles.group}>
        <SectionLabel>Type</SectionLabel>
        <ChipGroup multi options={TYPES} selected={f.types} onChange={(types) => patch({ types })} />
      </View>
      <View style={styles.group}>
        <SectionLabel>Category</SectionLabel>
        <ChipGroup
          multi
          options={cats.map((c) => ({ value: c.id, label: c.short }))}
          selected={f.categoryIds}
          onChange={(categoryIds) => patch({ categoryIds })}
        />
      </View>
      <View style={styles.group}>
        <SectionLabel>Account</SectionLabel>
        <ChipGroup
          multi
          options={[
            { value: 'all', label: 'All accounts' },
            ...accts.map((a) => ({
              value: a.id,
              label: a.name.replace(' Credit Card', ' Card').replace(' Wallet', ''),
            })),
          ]}
          selected={f.accountIds.length ? f.accountIds : ['all']}
          onChange={(ids) =>
            patch({ accountIds: ids.at(-1) === 'all' ? [] : ids.filter((x) => x !== 'all') })
          }
        />
      </View>
      <View style={styles.group}>
        <SectionLabel>Amount</SectionLabel>
        <View style={styles.minmax}>
          <View style={styles.grow}>
            <TextField
              label="Min"
              value={f.min}
              onChangeText={(v) => patch({ min: money$(v) })}
              keyboardType="number-pad"
              placeholder="₹0"
            />
          </View>
          <View style={styles.grow}>
            <TextField
              label="Max"
              value={f.max}
              onChangeText={(v) => patch({ max: money$(v) })}
              keyboardType="number-pad"
              placeholder="Any"
            />
          </View>
        </View>
      </View>
      <Button
        label={`Show ${plural(count, 'transaction', 'transactions')}`}
        onPress={() => {
          apply({ ...f, quick: stored.quick });
          close();
        }}
      />
    </>
  );
}

export function FiltersSheet() {
  const stored = useFiltersStore((s) => s.filters);
  const [f, setF] = useState<TxFilters>(stored);
  return (
    <Sheet
      title="Filters"
      label="Filters"
      headerRight={<TextButton label="Reset" color="muted" onPress={() => setF(defaultFilters)} />}
    >
      <Body f={f} setF={setF} />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  group: { gap: space[10] },
  minmax: { flexDirection: 'row', gap: space[10] },
  grow: { flex: 1 },
});
