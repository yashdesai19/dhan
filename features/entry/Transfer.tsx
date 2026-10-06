// Transfer: account A → amount → account B. Never counted as spending (spec §6).
import { useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { router } from 'expo-router';
import { useQueryClient } from '@tanstack/react-query';

import {
  Banner,
  Button,
  Card,
  Icon,
  IconTile,
  Screen,
  SectionLabel,
  StickyFooter,
  Text,
  TextField,
  Touchable,
} from '@/components';
import { useAddTransfer } from '@/data/queries';
import { undo } from '@/data/queries/actions';
import { useMoneyData, useToday } from '@/features/shared/hooks';
import { useReturnTo } from '@/features/shared/nav';
import { useEntryDraftStore } from '@/store/drafts';
import { useHighlightStore, useToastStore } from '@/store/ui';
import { fonts, iconSize, moneySizes, radius, size, space, useColors } from '@/theme';
import type { Account } from '@/types/domain';
import { addDays } from '@/utils/dates';
import { groupIN, inr } from '@/utils/format';
import { dateLabel, EntryHeader, EntryPill, nextAccount, useValidDraftIds } from './EntryParts';

const ICON: Record<Account['type'], 'bank' | 'cash' | 'coin' | 'card' | 'wallet' | 'tag'> = {
  bank: 'bank',
  cash: 'cash',
  savings: 'coin',
  credit: 'card',
  wallet: 'wallet',
  custom: 'tag',
};

function AccountCard({
  label,
  account,
  sub,
  onPress,
}: {
  label: string;
  account?: Account;
  sub: string;
  onPress: () => void;
}) {
  const c = useColors();
  return (
    <Touchable
      onPress={onPress}
      accessibilityLabel={`${label}: ${account?.name ?? ''}, ${sub}`}
      accessibilityHint="Switches to your next account"
      style={[styles.acct, { backgroundColor: c.surface, borderColor: c.line }]}
    >
      <IconTile icon={account ? ICON[account.type] : 'bank'} />
      <View style={styles.grow}>
        <Text variant="micro" weight="semibold" color="muted" style={styles.tracking}>
          {label}
        </Text>
        <Text variant="section">{account?.name ?? 'Choose account'}</Text>
        <Text variant="meta" color="muted" tabular>
          {sub}
        </Text>
      </View>
      <Icon name="chevD" size={iconSize.lg} color="faint" strokeWidth={2} />
    </Touchable>
  );
}

export function TransferScreen() {
  const c = useColors();
  const { today } = useToday();
  const { accounts, categories, loading } = useMoneyData();
  useValidDraftIds(accounts, categories);
  const draft = useEntryDraftStore((s) => s.draft);
  const patch = useEntryDraftStore((s) => s.patch);
  const reset = useEntryDraftStore((s) => s.reset);
  const restore = useEntryDraftStore((s) => s.restore);
  const show = useToastStore((s) => s.show);
  const highlight = useHighlightStore((s) => s.set);
  const returnTo = useReturnTo();
  const qc = useQueryClient();
  const add = useAddTransfer();
  const [noteOpen, setNoteOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const live = accounts.filter((a) => !a.archived);
  const from = live.find((a) => a.id === draft.fromId) ?? live[0];
  const to = live.find((a) => a.id === draft.toId) ?? live.find((a) => a.id !== from?.id);
  const amount = Number(draft.amount.split('.')[0] || '0');
  const empty = amount === 0;

  const submit = () => {
    setError(null);
    // Still loading: keep the draft's accounts rather than dropping the tap
    const fromId = from?.id ?? draft.fromId;
    const toId = to?.id ?? draft.toId;
    if ((!loading && (!from || !to)) || fromId === toId) {
      setError('Transfers require at least two different accounts.');
      return;
    }
    const snapshot = draft;
    add.mutate(
      { amount, fromId, toId, date: draft.date, note: draft.note || undefined },
      {
        onSuccess: (t) => {
          reset();
          highlight(t.id);
          returnTo('/(tabs)');
          show({
            message: `Moved ${inr(t.amount)} from ${from?.name ?? ''} to ${to?.name ?? ''}`,
            actionLabel: 'Undo',
            onAction: () => {
              void undo.createdTransaction(qc, t.id).then(() => {
                restore(snapshot);
                router.push('/add/transfer');
              });
            },
          });
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  return (
    <Screen
      top="stack"
      bottom="footer"
      gap={space[20]}
      keyboard
      overlay={
        <StickyFooter>
          <Button
            label={empty ? 'Enter an amount' : `Move ${inr(amount)}`}
            disabled={empty}
            loading={add.isPending}
            onPress={submit}
          />
        </StickyFooter>
      }
    >
      <EntryHeader kind="transfer" />
      <View style={styles.flow}>
        <AccountCard
          label="FROM"
          account={from}
          sub={`Available ${inr(from?.balance ?? 0)}`}
          onPress={() => {
            const n = nextAccount(accounts, draft.fromId, draft.toId);
            if (n) patch({ fromId: n.id });
          }}
        />
        <View style={styles.mid}>
          <View style={styles.rail}>
            <View style={[styles.railLine, { backgroundColor: c.line }]} />
            <View style={[styles.railIcon, { backgroundColor: c.primarySoft }]}>
              <Icon name="down" size={iconSize.xl} color="primary" strokeWidth={2} />
            </View>
            <View style={[styles.railLine, { backgroundColor: c.line }]} />
          </View>
          <View style={styles.amount}>
            <Text maxScale={1.3} style={{ fontFamily: fonts.serif, fontSize: moneySizes.xs, color: c.faint }}>
              ₹
            </Text>
            <TextInput
              accessibilityLabel="Amount to move"
              value={amount ? groupIN(amount) : ''}
              placeholder="0"
              placeholderTextColor={c.faint}
              onChangeText={(v) => patch({ amount: v.replace(/[^\d]/g, '').slice(0, 9) || '0' })}
              keyboardType="number-pad"
              selectionColor={c.primary}
              style={[styles.amountInput, { color: c.ink }]}
            />
          </View>
          <Touchable
            accessibilityLabel="Swap accounts"
            onPress={() => patch({ fromId: draft.toId, toId: draft.fromId })}
            style={[styles.swap, { borderColor: c.line, backgroundColor: c.surface }]}
          >
            <Icon name="swap" size={iconSize.lg} />
          </Touchable>
        </View>
        <AccountCard
          label="TO"
          account={to}
          sub={`Balance ${inr(to?.balance ?? 0)}`}
          onPress={() => {
            const n = nextAccount(accounts, draft.toId, draft.fromId);
            if (n) patch({ toId: n.id });
          }}
        />
      </View>
      <View style={styles.pills}>
        <EntryPill
          label={dateLabel(draft.date, today)}
          onPress={() => patch({ date: draft.date && draft.date !== today ? undefined : addDays(today, -1) })}
        />
        <EntryPill label={noteOpen ? '− Note' : '+ Note'} onPress={() => setNoteOpen(!noteOpen)} />
      </View>
      {noteOpen ? (
        <TextField label="Note" value={draft.note} onChangeText={(note) => patch({ note })} autoFocus />
      ) : null}
      <Card gap={space[10]}>
        <SectionLabel>After this transfer</SectionLabel>
        {[
          { name: from?.name ?? '', before: from?.balance ?? 0, after: (from?.balance ?? 0) - amount },
          { name: to?.name ?? '', before: to?.balance ?? 0, after: (to?.balance ?? 0) + amount },
        ].map((r) => (
          <View
            key={r.name}
            style={styles.between}
            accessible
            accessibilityLabel={`${r.name} ${inr(r.before)} becomes ${inr(r.after)}`}
          >
            <Text variant="body">{r.name}</Text>
            <Text variant="body" tabular>
              {`${inr(r.before)} → `}
              <Text variant="body" weight="semibold" tabular>
                {inr(r.after)}
              </Text>
            </Text>
          </View>
        ))}
      </Card>
      <Banner icon="info" tone="neutral">
        Transfers aren’t spending. Your budget and reports stay the same.
      </Banner>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  flow: { paddingTop: space[12] },
  acct: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[12],
    padding: space[16],
    borderRadius: radius.card,
    borderWidth: 1,
  },
  grow: { flex: 1, gap: 2 },
  tracking: { letterSpacing: 1 },
  mid: { flexDirection: 'row', alignItems: 'center', gap: space[14], paddingHorizontal: space[8] },
  rail: { width: 40, alignItems: 'center', gap: space[4] },
  railLine: { width: 2, height: 20 },
  railIcon: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  amount: { flex: 1, flexDirection: 'row', alignItems: 'flex-end', gap: space[4] },
  amountInput: {
    flex: 1,
    fontFamily: fonts.serif,
    fontSize: moneySizes.lg,
    padding: 0,
    minHeight: size.touch,
  },
  swap: {
    width: size.iconButton,
    height: size.iconButton,
    borderRadius: size.iconButton / 2,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pills: { flexDirection: 'row', gap: space[8] },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: space[8] },
});
