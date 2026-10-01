import { useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';

import {
  Button,
  ChipGroup,
  ListCard,
  ListRow,
  Money,
  Sheet,
  Stepper,
  Text,
  TextField,
  Toggle,
  useSheet,
} from '@/components';
import { useBudgets, useHistory, useRemoveCategoryBudget, useSetCategoryBudget } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { threeMonthAverage } from '@/utils/budget';
import { groupIN, inr } from '@/utils/format';

const PICKABLE = ['food', 'transport', 'shopping', 'bills', 'health', 'fun', 'home', 'gifts'];

function Body({ categoryId, setCategoryId }: { categoryId: string; setCategoryId: (id: string) => void }) {
  const { close } = useSheet();
  const params = useLocalSearchParams<{ category: string; month: string }>();
  const { month: current } = useToday();
  const month = params.month ?? current;
  const isNew = params.category === 'new';
  const money = useMoneyData();
  const budgets = useBudgets();
  const history = useHistory();
  const setBudget = useSetCategoryBudget(month);
  const remove = useRemoveCategoryBudget(month);
  const show = useToastStore((s) => s.show);

  const existing = budgets.data
    ?.find((b) => b.month === month)
    ?.categories.find((c) => c.categoryId === categoryId);
  const avg = useMemo(
    () => threeMonthAverage(history.data ?? [], money.transactions, categoryId, current),
    [history.data, money.transactions, categoryId, current],
  );
  const base = existing?.limit ?? (Math.max(500, Math.round(avg / 500) * 500) || 3000);
  const [limit, setLimit] = useState(existing ? existing.limit + 500 : base);
  const [rollover, setRollover] = useState(existing?.rollover ?? false);
  const [warn, setWarn] = useState((existing?.warnAtPercent ?? 90) === 90);
  const [custom, setCustom] = useState(false);
  const presets = [base, base + 500, base + 1000];
  const free = PICKABLE.filter(
    (id) => !budgets.data?.find((b) => b.month === month)?.categories.some((c) => c.categoryId === id),
  );
  const cat = money.categories.find((c) => c.id === categoryId);

  return (
    <>
      {isNew ? (
        <ChipGroup
          wrap={false}
          bleed={space[20]}
          options={free.map((id) => ({
            value: id,
            label: money.categories.find((c) => c.id === id)?.short ?? id,
          }))}
          selected={[categoryId]}
          onChange={([v]) => v && setCategoryId(v)}
        />
      ) : null}
      <Stepper
        large
        label={`${cat?.short ?? ''} budget`}
        value={limit}
        step={500}
        min={500}
        onChange={(v) => {
          setCustom(false);
          setLimit(v);
        }}
        renderValue={(v) => <Money amount={v} size="hero" />}
      />
      {avg > 0 ? (
        <Text variant="small" color="muted" align="center">
          {`Your 3-month average is ${inr(avg)}`}
        </Text>
      ) : null}
      <ChipGroup
        options={[
          ...presets.map((p) => ({ value: String(p), label: inr(p) })),
          { value: 'custom', label: 'Custom' },
        ]}
        selected={[custom ? 'custom' : String(limit)]}
        onChange={([v]) => {
          if (v === 'custom') setCustom(true);
          else if (v) {
            setCustom(false);
            setLimit(Number(v));
          }
        }}
      />
      {custom ? (
        <TextField
          label="Monthly limit"
          value={`₹${groupIN(limit)}`}
          onChangeText={(v) => setLimit(Number(v.replace(/[^\d]/g, '') || '0'))}
          keyboardType="number-pad"
          autoFocus
        />
      ) : null}
      <ListCard>
        <ListRow
          title="Roll over what’s left"
          subtitle="Unused money carries into next month."
          pad={14}
          trailing={<Toggle value={rollover} onChange={setRollover} accessibilityLabel="Roll over" />}
        />
        <ListRow
          title="Warn me at 90%"
          subtitle="A quiet heads-up before you go over."
          pad={14}
          trailing={<Toggle value={warn} onChange={setWarn} accessibilityLabel="Warn at 90%" />}
        />
      </ListCard>
      <Button
        label="Save budget"
        loading={setBudget.isPending}
        disabled={limit <= 0}
        onPress={() =>
          setBudget.mutate(
            { categoryId, limit, rollover, warnAtPercent: warn ? 90 : 101 },
            {
              onSuccess: () =>
                close(() => show({ message: `${cat?.short ?? ''} budget set to ${inr(limit)}` })),
            },
          )
        }
      />
      {existing ? (
        <View style={styles.center}>
          <Button
            label="Remove this budget"
            kind="ghost"
            size="sm"
            onPress={() =>
              remove.mutate(categoryId, {
                onSuccess: () =>
                  close(() => {
                    router.navigate('/budget');
                    show({ message: `${cat?.short ?? ''} budget removed` });
                  }),
              })
            }
            style={styles.remove}
          />
        </View>
      ) : null}
    </>
  );
}

export function EditBudgetSheet() {
  const { category } = useLocalSearchParams<{ category: string }>();
  const [categoryId, setCategoryId] = useState(category === 'new' || !category ? 'health' : category);
  const { categories } = useMoneyData();
  const name = categories.find((c) => c.id === categoryId)?.short ?? '';
  return (
    <Sheet title={category === 'new' ? 'New budget' : `${name} budget`} label="Edit budget">
      <Body key={categoryId} categoryId={categoryId} setCategoryId={setCategoryId} />
    </Sheet>
  );
}

const styles = StyleSheet.create({
  center: { alignItems: 'center' },
  remove: { alignSelf: 'center' },
});
