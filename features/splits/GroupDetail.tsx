import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';

import {
  Avatar,
  AvatarStack,
  Button,
  EmptyState,
  IconButton,
  IconTile,
  ListCard,
  ListRow,
  Money,
  RowAmount,
  Screen,
  SectionHeader,
  SegmentedControl,
  SmallButton,
  StickyFooter,
  Text,
  TopBar,
} from '@/components';
import { space } from '@/theme';
import { inr, plural } from '@/utils/format';
import { myShareOf } from '@/utils/splits';
import { ME, useSplits } from './useSplits';

type Tab = 'expenses' | 'balances' | 'members';

export function GroupDetailScreen() {
  const router = useRouter();
  const { groupId } = useLocalSearchParams<{ groupId: string }>();
  const s = useSplits();
  const [tab, setTab] = useState<Tab>('balances');
  const g = s.groups.find((x) => x.id === groupId);

  if (!g) {
    return (
      <Screen>
        <TopBar title="Group" />
        {s.loading ? null : (
          <EmptyState icon="users" title="Group not found" body="It may have been removed." />
        )}
      </Screen>
    );
  }

  const pos = s.groupPos(g.id);
  const ex = s.expenses.filter((e) => e.groupId === g.id).sort((a, b) => b.date.localeCompare(a.date));
  const total = ex.reduce((sum, e) => sum + e.amount, 0);
  const members = g.memberIds.map(s.person);

  const expenses = (
    <ListCard>
      {ex.map((e) => {
        const mine = myShareOf(e, ME);
        const payer = e.paidBy === ME ? 'You' : s.person(e.paidBy).name;
        return (
          <ListRow
            key={e.id}
            leading={<IconTile icon={e.icon} />}
            title={e.title}
            subtitle={`${payer} paid ${inr(e.amount)}`}
            trailing={
              mine.kind === 'none' ? (
                <RowAmount value="not involved" color="muted" weight="medium" />
              ) : (
                <View style={styles.right}>
                  <Text variant="caption" color="muted">
                    {mine.kind === 'lent' ? 'you lent' : 'you borrowed'}
                  </Text>
                  <Text
                    variant="body"
                    weight="semibold"
                    tabular
                    color={mine.kind === 'lent' ? 'income' : 'expense'}
                  >
                    {inr(mine.amount)}
                  </Text>
                </View>
              )
            }
          />
        );
      })}
    </ListCard>
  );

  return (
    <Screen
      bottom="footer"
      gap={space[18]}
      overlay={
        <StickyFooter>
          <Button
            label="Add group expense"
            icon="plus"
            onPress={() => router.push({ pathname: '/add/split', params: { groupId: g.id } })}
          />
        </StickyFooter>
      }
    >
      <TopBar title={g.name} trailing={<IconButton icon="dots" accessibilityLabel="Group options" />} />
      <View style={styles.meta}>
        <AvatarStack size="md" people={members.map((m) => ({ initials: m.initials, tone: m.avatarTone }))} />
        <Text variant="small" color="muted" style={styles.grow}>
          {`${plural(g.memberIds.length, 'member', 'members')} · ${plural(ex.length, 'expense', 'expenses')} · ${inr(total)} total`}
        </Text>
      </View>
      <View style={styles.gap4}>
        <Text variant="small" color="muted">
          {pos.net >= 0 ? 'In this group, you get back' : 'In this group, you owe'}
        </Text>
        <Money amount={Math.abs(pos.net)} size="md" color={pos.net >= 0 ? 'income' : 'expense'} />
      </View>
      <SegmentedControl
        accessibilityLabel="Group view"
        value={tab}
        onChange={setTab}
        options={[
          { value: 'expenses', label: 'Expenses' },
          { value: 'balances', label: 'Balances' },
          { value: 'members', label: 'Members' },
        ]}
      />
      {tab === 'members' ? (
        <ListCard>
          {members.map((m) => (
            <ListRow
              key={m.id}
              leading={<Avatar initials={m.initials} tone={m.avatarTone} />}
              title={m.id === ME ? 'You' : m.name}
              subtitle={m.id === ME ? 'Group creator' : 'Member'}
            />
          ))}
        </ListCard>
      ) : tab === 'expenses' ? (
        expenses
      ) : (
        <>
          <ListCard>
            {Object.entries(pos.byPerson).map(([id, v]) => {
              const p = s.person(id);
              return (
                <ListRow
                  key={id}
                  leading={<Avatar initials={p.initials} tone={p.avatarTone} />}
                  title={p.name}
                  subtitle={v >= 0 ? 'owes you' : 'you owe'}
                  onPress={() => router.push(`/splits/settle/${id}`)}
                  accessibilityHint={v >= 0 ? 'Record a payment from them' : 'Settle up'}
                  trailing={
                    <View style={styles.balance}>
                      <RowAmount value={inr(Math.abs(v))} color={v >= 0 ? 'income' : 'expense'} />
                      {v >= 0 ? (
                        <SmallButton
                          label="Remind"
                          accessibilityHint="Reminders are not available in this preview"
                        />
                      ) : (
                        <SmallButton
                          label="Settle"
                          kind="primary"
                          onPress={() => router.push(`/splits/settle/${id}`)}
                        />
                      )}
                    </View>
                  }
                />
              );
            })}
          </ListCard>
          <Text variant="meta" color="muted">
            Balances are simplified so everyone makes the fewest payments.
          </Text>
          <SectionHeader title="Expenses" />
          {expenses}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  meta: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1 },
  gap4: { gap: space[4] },
  right: { alignItems: 'flex-end', gap: 2 },
  balance: { flexDirection: 'row', alignItems: 'center', gap: space[10] },
});
