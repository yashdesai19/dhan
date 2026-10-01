import { useMemo, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Banner,
  ChipGroup,
  EmptyState,
  Icon,
  ListCard,
  Screen,
  SectionHeader,
  SectionLabel,
  Text,
  TextButton,
  Touchable,
  TransactionRow,
} from '@/components';
import { useAddRecentSearch, useRecentSearches } from '@/data/queries';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { fonts, iconSize, radius, size, space, textVariants, useColors } from '@/theme';
import { weekdayDayMonth } from '@/utils/dates';
import { describeTransaction } from '@/utils/describe';
import { inr, percent, plural } from '@/utils/format';
import { categoryTotals, sortNewestFirst } from '@/utils/summary';

export function SearchScreen() {
  const c = useColors();
  const router = useRouter();
  const { today, month } = useToday();
  const money = useMoneyData();
  const recent = useRecentSearches().data ?? [];
  const remember = useAddRecentSearch();
  const [q, setQ] = useState('');

  const results = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!term) return [];
    return sortNewestFirst(
      money.transactions.filter((t) => {
        const cat = money.categories.find((x) => x.id === t.categoryId)?.name ?? '';
        const acct = money.accounts.find((x) => x.id === t.accountId)?.name ?? '';
        return [t.title, t.note ?? '', t.detail ?? '', cat, acct].some((s) => s.toLowerCase().includes(term));
      }),
    );
  }, [q, money.transactions, money.categories, money.accounts]);

  const total = results.reduce((s, t) => s + (t.type === 'expense' ? t.amount : 0), 0);
  const insight = useMemo(() => {
    const first = results[0];
    if (!first || first.type !== 'expense' || !first.categoryId) return null;
    const same = results.every((t) => t.title === first.title && t.categoryId === first.categoryId);
    const catTotal = categoryTotals(money.transactions, month)[first.categoryId] ?? 0;
    if (!same || catTotal === 0) return null;
    const cat = money.categories.find((x) => x.id === first.categoryId);
    return `${first.title} is ${percent(total, catTotal)}% of your ${cat?.short.toLowerCase() ?? ''} spending this month.`;
  }, [results, total, money.transactions, money.categories, month]);

  return (
    <Screen top="tab" gap={space[20]} keyboard>
      <View style={styles.top}>
        <View style={[styles.field, { borderColor: c.primary, backgroundColor: c.surface }]}>
          <Icon name="search" size={iconSize.lg} color="muted" />
          <TextInput
            accessibilityLabel="Search transactions"
            value={q}
            onChangeText={setQ}
            onSubmitEditing={() => remember.mutate(q)}
            placeholder="Search merchants, notes, categories"
            placeholderTextColor={c.faint}
            returnKeyType="search"
            autoFocus
            autoCorrect={false}
            selectionColor={c.primary}
            style={[styles.input, { color: c.ink }]}
          />
          {q ? (
            <Touchable accessibilityLabel="Clear search" onPress={() => setQ('')} style={styles.clear}>
              <View style={[styles.clearDot, { backgroundColor: c.soft }]}>
                <Icon name="close" size={iconSize.xs} color="muted" strokeWidth={2.4} />
              </View>
            </Touchable>
          ) : null}
        </View>
        <TextButton label="Cancel" onPress={() => router.back()} />
      </View>

      {!q ? (
        <View style={styles.gap10}>
          <SectionLabel>Recent</SectionLabel>
          <ChipGroup
            options={recent.map((r) => ({ value: r, label: r }))}
            selected={[]}
            onChange={([v]) => v && setQ(v)}
          />
        </View>
      ) : results.length === 0 ? (
        <EmptyState
          icon="search"
          title={`No results for “${q.trim()}”`}
          body="Try a merchant name, a category like Food, or an account."
        />
      ) : (
        <>
          <View style={styles.between}>
            <SectionHeader title={plural(results.length, 'result', 'results')} />
            {total > 0 ? (
              <Text variant="small" color="muted" tabular>
                {`${inr(total)} total`}
              </Text>
            ) : null}
          </View>
          <ListCard>
            {results.map((t) => {
              const v = describeTransaction(t, money.categories, money.accounts, { today });
              const acct = money.accounts.find((a) => a.id === t.accountId)?.name;
              return (
                <TransactionRow
                  key={t.id}
                  view={{ ...v, subtitle: [weekdayDayMonth(t.date), acct].filter(Boolean).join(' · ') }}
                  onPress={() => {
                    remember.mutate(q);
                    router.push(`/transactions/${t.id}`);
                  }}
                />
              );
            })}
          </ListCard>
          {insight ? <Banner icon="sparkle">{insight}</Banner> : null}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  top: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  field: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[8],
    height: size.touch,
    borderRadius: radius.field,
    borderWidth: 2,
    paddingLeft: space[12],
  },
  input: { flex: 1, fontFamily: fonts.regular, fontSize: textVariants.bodyLg.fontSize, padding: 0 },
  clear: { width: size.touch, height: size.touch, alignItems: 'center', justifyContent: 'center' },
  clearDot: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  gap10: { gap: space[10] },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
});
