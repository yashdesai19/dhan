import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import { Icon, IconButton, SegmentedControl, Text, Touchable, type IconName } from '@/components';
import { hitSlop, iconSize, radius, size, space, useColors } from '@/theme';
import type { Account } from '@/types/domain';

export type EntryKind = 'expense' | 'income' | 'transfer';

const ROUTES: Record<EntryKind, string> = {
  expense: '/add/expense',
  income: '/add/income',
  transfer: '/add/transfer',
};

/** Close button + Expense / Income / Transfer switcher (router.replace, never stacks; spec §2). */
export function EntryHeader({ kind }: { kind: EntryKind }) {
  const router = useRouter();
  return (
    <View style={styles.header}>
      <IconButton icon="close" accessibilityLabel="Close" onPress={() => router.back()} />
      <SegmentedControl
        large
        style={styles.grow}
        accessibilityLabel="Entry type"
        value={kind}
        onChange={(k) => {
          if (k !== kind) router.replace(ROUTES[k]);
        }}
        options={[
          { value: 'expense', label: 'Expense' },
          { value: 'income', label: 'Income' },
          { value: 'transfer', label: 'Transfer' },
        ]}
      />
      <View style={styles.spacer} />
    </View>
  );
}

/** 40 pt bordered pill: account, date, note (Add expense, Add income, Transfer). */
export function EntryPill({
  label,
  icon,
  chevron,
  onPress,
  accessibilityHint,
}: {
  label: string;
  icon?: IconName;
  chevron?: boolean;
  onPress?: () => void;
  accessibilityHint?: string;
}) {
  const c = useColors();
  return (
    <Touchable
      onPress={onPress}
      hitSlop={hitSlop}
      accessibilityLabel={label}
      accessibilityHint={accessibilityHint}
      style={[styles.pill, { backgroundColor: c.surface, borderColor: c.line }]}
    >
      {icon ? <Icon name={icon} size={iconSize.md} color="primary" strokeWidth={1.8} /> : null}
      <Text variant="meta" weight="medium">
        {label}
      </Text>
      {chevron ? <Icon name="chevD" size={iconSize.sm} color="muted" strokeWidth={2} /> : null}
    </Touchable>
  );
}

/** Picks the next account in the list (no extra picker UI on the canvas). */
export function nextAccount(
  accounts: readonly Account[],
  currentId: string,
  skip?: string,
): Account | undefined {
  const list = accounts.filter((a) => !a.archived && a.id !== skip);
  const i = list.findIndex((a) => a.id === currentId);
  return list[(i + 1) % Math.max(1, list.length)];
}

export function dateLabel(date: string | undefined, today: string): string {
  return !date || date === today ? 'Today' : 'Yesterday';
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1 },
  spacer: { width: size.iconButton },
  pill: {
    height: size.small,
    paddingHorizontal: space[12],
    borderRadius: radius.chip,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[6],
  },
});
