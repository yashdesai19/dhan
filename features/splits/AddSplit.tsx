// Split expense with all five methods: Equal, Exact, Percent, Shares, Item-wise (spec §14).
import { useEffect, useMemo, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import {
  AvatarStack,
  Banner,
  Button,
  CheckboxBox,
  Divider,
  ListCard,
  Screen,
  SectionLabel,
  SegmentedControl,
  SelectRow,
  Stepper,
  StickyFooter,
  Text,
  TextButton,
  TextField,
  TopBar,
  Touchable,
} from '@/components';
import { useAddGroupExpense } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { useReturnTo } from '@/features/shared/nav';
import { useSplitDraftStore } from '@/store/drafts';
import { useToastStore } from '@/store/ui';
import { fonts, moneySizes, radius, size, space, textVariants, useColors } from '@/theme';
import type { ID, SplitMethod } from '@/types/domain';
import { groupIN, inr } from '@/utils/format';
import { computeShares, sumShares } from '@/utils/splits';
import { ME, useSplits } from './useSplits';

const METHODS: { value: SplitMethod; label: string }[] = [
  { value: 'equal', label: 'Equal' },
  { value: 'exact', label: 'Exact' },
  { value: 'percent', label: 'Percent' },
  { value: 'shares', label: 'Shares' },
  { value: 'itemwise', label: 'Item-wise' },
];

function MemberHead({ initials, name }: { initials: string; name: string }) {
  const c = useColors();
  return (
    <>
      <View style={[styles.mini, { backgroundColor: c.soft }]}>
        <Text variant="caption" weight="semibold">
          {initials}
        </Text>
      </View>
      <Text variant="body" weight="medium" style={styles.grow}>
        {name}
      </Text>
    </>
  );
}

function SmallInput({
  value,
  onChange,
  label,
  suffix,
  prefix,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  suffix?: string;
  prefix?: string;
}) {
  const c = useColors();
  return (
    <View style={[styles.smallInput, { borderColor: c.line, backgroundColor: c.surface }]}>
      {prefix ? (
        <Text variant="body" color="muted">
          {prefix}
        </Text>
      ) : null}
      <TextInput
        accessibilityLabel={label}
        value={value}
        onChangeText={onChange}
        keyboardType="number-pad"
        selectionColor={c.primary}
        style={[styles.smallInputText, { color: c.ink }]}
      />
      {suffix ? (
        <Text variant="body" color="muted">
          {suffix}
        </Text>
      ) : null}
    </View>
  );
}

export function AddSplitScreen() {
  const c = useColors();
  const params = useLocalSearchParams<{ amount: string; title: string; groupId: string }>();
  const s = useSplits();
  const draft = useSplitDraftStore((x) => x.draft);
  const patch = useSplitDraftStore((x) => x.patch);
  const reset = useSplitDraftStore((x) => x.reset);
  const restore = useSplitDraftStore((x) => x.restore);
  const add = useAddGroupExpense();
  const show = useToastStore((x) => x.show);
  const returnTo = useReturnTo();
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.amount || params.title || params.groupId) {
      reset({
        ...(params.amount ? { amount: params.amount } : null),
        ...(params.title ? { title: params.title } : null),
        ...(params.groupId ? { groupId: params.groupId } : null),
      });
    }
    // Initialise once from the route params.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const group = s.groups.find((g) => g.id === draft.groupId) ?? s.groups[0];
  const memberIds: ID[] = group?.memberIds ?? [ME];
  const amount = Number(draft.amount.replace(/[^\d]/g, '') || '0');

  const shares = useMemo(
    () =>
      computeShares(draft.method, {
        amount,
        memberIds,
        included: draft.included,
        exact: Object.fromEntries(memberIds.map((id) => [id, Number(draft.exact[id] ?? '0')])),
        percent: Object.fromEntries(memberIds.map((id) => [id, Number(draft.percent[id] ?? '0')])),
        shares: draft.shares,
        items: draft.items,
      }),
    [draft, amount, memberIds],
  );
  const assigned = sumShares(shares);
  const ok = amount > 0 && assigned === amount;
  const nIncluded = memberIds.filter((id) => shares[id] && (shares[id] ?? 0) > 0).length;
  const name = (id: ID) => (id === ME ? 'You' : s.person(id).name);

  const save = () => {
    setError(null);
    if (!group) return;
    const snapshot = draft;
    add.mutate(
      {
        groupId: group.id,
        title: draft.title.trim() || 'Split expense',
        amount,
        paidBy: draft.paidBy,
        method: draft.method,
        shares,
      },
      {
        onSuccess: (ge) => {
          reset();
          returnTo('/(tabs)');
          router.push(`/splits/${group.id}`);
          const others = memberIds.filter((id) => id !== ME && (shares[id] ?? 0) > 0).map(name);
          show({
            message: `Split saved · ${others.length > 1 ? `${others.slice(0, -1).join(', ')} and ${others.at(-1)}` : (others[0] ?? 'group')} notified`,
            actionLabel: 'Undo',
            placement: 'footer',
            onAction: () => {
              void undo.groupExpense(qc, ge.id).then(() => {
                restore(snapshot);
                router.push('/add/split');
              });
            },
          });
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  const cyclePayer = () => {
    const i = memberIds.indexOf(draft.paidBy);
    patch({ paidBy: memberIds[(i + 1) % memberIds.length] ?? ME });
  };
  const cycleGroup = () => {
    const i = s.groups.findIndex((g) => g.id === draft.groupId);
    const next = s.groups[(i + 1) % Math.max(1, s.groups.length)];
    if (next) patch({ groupId: next.id });
  };

  const panel = (() => {
    switch (draft.method) {
      case 'equal':
        return memberIds.map((id) => {
          const on = draft.included[id] ?? true;
          return (
            <Touchable
              key={id}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: on }}
              accessibilityLabel={`${name(id)}, ${inr(shares[id] ?? 0)}`}
              onPress={() => patch({ included: { ...draft.included, [id]: !on } })}
              style={styles.memberRow}
            >
              <CheckboxBox checked={on} />
              <MemberHead initials={s.person(id).initials} name={name(id)} />
              <Text variant="body" weight="semibold" tabular color={on ? 'ink' : 'muted'}>
                {inr(shares[id] ?? 0)}
              </Text>
            </Touchable>
          );
        });
      case 'exact':
        return memberIds.map((id) => (
          <View key={id} style={styles.memberRow}>
            <MemberHead initials={s.person(id).initials} name={name(id)} />
            <SmallInput
              prefix="₹"
              label={`Amount for ${name(id)}`}
              value={draft.exact[id] ?? ''}
              onChange={(v) => patch({ exact: { ...draft.exact, [id]: v.replace(/[^\d]/g, '') } })}
            />
          </View>
        ));
      case 'percent':
        return memberIds.map((id) => (
          <View key={id} style={styles.memberRow}>
            <MemberHead initials={s.person(id).initials} name={name(id)} />
            <SmallInput
              suffix="%"
              label={`Percent for ${name(id)}`}
              value={draft.percent[id] ?? ''}
              onChange={(v) =>
                patch({ percent: { ...draft.percent, [id]: v.replace(/[^\d]/g, '').slice(0, 3) } })
              }
            />
            <Text variant="small" color="muted" tabular style={styles.amountCol}>
              {inr(shares[id] ?? 0)}
            </Text>
          </View>
        ));
      case 'shares':
        return memberIds.map((id) => (
          <View key={id} style={styles.memberRow}>
            <MemberHead initials={s.person(id).initials} name={name(id)} />
            <Stepper
              label={`shares for ${name(id)}`}
              value={draft.shares[id] ?? 0}
              onChange={(v) => patch({ shares: { ...draft.shares, [id]: v } })}
            />
            <Text variant="small" color="muted" tabular style={styles.amountCol}>
              {inr(shares[id] ?? 0)}
            </Text>
          </View>
        ));
      case 'itemwise':
        return (
          <View>
            {draft.items.map((it, i) => (
              <View key={it.id}>
                {i > 0 ? <Divider /> : null}
                <View style={styles.item}>
                  <View style={styles.between}>
                    <Text variant="body" weight="medium">
                      {it.title}
                    </Text>
                    <Text variant="body" weight="semibold" tabular>
                      {inr(it.amount)}
                    </Text>
                  </View>
                  <View style={styles.itemPeople}>
                    <AvatarStack
                      size="xs"
                      people={it.memberIds.map((id) => ({
                        initials: s.person(id).initials,
                        tone: s.person(id).avatarTone,
                      }))}
                    />
                    <Text variant="meta" color="muted">
                      {it.memberIds.length === memberIds.length
                        ? `All ${it.memberIds.length} · ${inr(Math.round(it.amount / it.memberIds.length))} each`
                        : `${it.memberIds.map(name).join(' and ')} · ${inr(Math.round(it.amount / it.memberIds.length))} each`}
                    </Text>
                  </View>
                </View>
              </View>
            ))}
            <TextButton
              label="+ Add item"
              size="sm"
              accessibilityHint="Adding items is not available in this preview"
            />
          </View>
        );
    }
  })();

  return (
    <Screen
      bottom="footer"
      gap={space[18]}
      keyboard
      overlay={
        <StickyFooter>
          <Button
            label={nIncluded === 0 && draft.method === 'equal' ? 'Pick at least one person' : 'Save split'}
            disabled={!ok}
            loading={add.isPending}
            onPress={save}
          />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title="Split expense" />
      <View style={styles.amount}>
        <Text maxScale={1.3} style={{ fontFamily: fonts.serif, fontSize: moneySizes.xs, color: c.faint }}>
          ₹
        </Text>
        <TextInput
          accessibilityLabel="Total amount"
          value={amount ? groupIN(amount) : ''}
          placeholder="0"
          placeholderTextColor={c.faint}
          onChangeText={(v) => patch({ amount: v.replace(/[^\d]/g, '').slice(0, 9) })}
          keyboardType="number-pad"
          selectionColor={c.primary}
          style={[styles.amountInput, { color: c.ink }]}
        />
      </View>
      <TextField
        label="What was it for?"
        value={draft.title}
        onChangeText={(title) => patch({ title })}
        placeholder="Beach villa · 2 nights"
      />
      <ListCard>
        <SelectRow label="Paid by" value={name(draft.paidBy)} icon="user" onPress={cyclePayer} />
        <SelectRow label="Group" value={group?.name ?? ''} icon="users" onPress={cycleGroup} />
      </ListCard>
      <View style={styles.gap10}>
        <SectionLabel>Split</SectionLabel>
        <SegmentedControl
          compact
          accessibilityLabel="Split method"
          value={draft.method}
          onChange={(method) => patch({ method })}
          options={METHODS}
        />
      </View>
      <View style={[styles.panel, { backgroundColor: c.surface, borderColor: c.line }]}>{panel}</View>
      <Text
        variant="small"
        weight="semibold"
        tabular
        align="center"
        color={ok ? 'income' : 'expense'}
        accessibilityLiveRegion="polite"
      >
        {`${inr(assigned)} of ${inr(amount)} assigned${ok ? ' ✓' : ''}`}
      </Text>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  amount: { flexDirection: 'row', justifyContent: 'center', alignItems: 'flex-end', gap: space[4] },
  amountInput: {
    fontFamily: fonts.serif,
    fontSize: moneySizes.lg,
    minWidth: 120,
    padding: 0,
    minHeight: size.touch,
    textAlign: 'center',
  },
  gap10: { gap: space[10] },
  panel: {
    borderWidth: 1,
    borderRadius: radius.card,
    paddingVertical: space[6],
    paddingHorizontal: space[16],
  },
  memberRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[12],
    paddingVertical: space[8],
    minHeight: 52,
  },
  mini: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  grow: { flex: 1 },
  smallInput: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[4],
    height: size.touch,
    borderRadius: radius.chip,
    borderWidth: 1,
    paddingHorizontal: space[12],
    minWidth: 80,
  },
  smallInputText: {
    fontFamily: fonts.semibold,
    fontSize: textVariants.body.fontSize,
    minWidth: 40,
    textAlign: 'right',
    padding: 0,
  },
  amountCol: { width: 70, textAlign: 'right' },
  item: { gap: space[8], paddingVertical: space[12] },
  itemPeople: { flexDirection: 'row', alignItems: 'center', gap: space[8] },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
});
