import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  Avatar,
  AvatarStack,
  Button,
  Card,
  ListCard,
  ListRow,
  Money,
  Pill,
  Screen,
  SectionHeader,
  SectionLabel,
  Skeleton,
  SmallButton,
  StickyFooter,
  Text,
  TopBar,
  Touchable,
} from '@/components';
import { radius, space, useColors, type ColorName } from '@/theme';
import type { GroupExpense } from '@/types/domain';
import { inr, plural } from '@/utils/format';
import { ME, useSplits } from './useSplits';

const SEG: ColorName[] = ['primary', 'blueSoft', 'primarySoft', 'sandSoft'];
const SEG_TEXT: ColorName[] = ['onPrimary', 'blueInk', 'primary', 'sandInk'];

function LatestExpense({
  e,
  memberIds,
  name,
}: {
  e: GroupExpense;
  memberIds: string[];
  name: (id: string) => string;
}) {
  const c = useColors();
  const payer = e.paidBy === ME ? 'You paid' : `${name(e.paidBy)} paid`;
  const ways = Object.values(e.shares).filter((v) => v > 0).length;
  const equal = e.method === 'equal';
  return (
    <Card tone="inset">
      <View style={styles.between}>
        <Text variant="body" weight="medium">
          {e.title}
        </Text>
        <Text variant="body" weight="semibold" tabular>
          {inr(e.amount)}
        </Text>
      </View>
      <Text variant="meta" color="muted">
        {`${payer} · split ${equal ? 'equally' : 'by amount'}, ${ways} ways`}
      </Text>
      <View style={styles.segs} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        {memberIds.map((id, i) => (
          <View
            key={id}
            style={[
              styles.seg,
              {
                flex: Math.max(1, e.shares[id] ?? 0),
                backgroundColor: c[SEG[i % SEG.length] ?? 'soft'],
                borderTopLeftRadius: i === 0 ? 8 : 3,
                borderBottomLeftRadius: i === 0 ? 8 : 3,
                borderTopRightRadius: i === memberIds.length - 1 ? 8 : 3,
                borderBottomRightRadius: i === memberIds.length - 1 ? 8 : 3,
              },
            ]}
          >
            <Text variant="micro" weight="semibold" color={SEG_TEXT[i % SEG_TEXT.length] ?? 'ink'}>
              {id === ME ? 'You' : name(id)}
            </Text>
          </View>
        ))}
      </View>
      <View style={styles.gap6}>
        {memberIds
          .filter((id) => id !== ME && e.paidBy === ME && (e.shares[id] ?? 0) > 0)
          .map((id) => (
            <View key={id} style={styles.between}>
              <Text variant="small">{`${name(id)} owes you`}</Text>
              <Text variant="small" weight="semibold" tabular>
                {inr(e.shares[id] ?? 0)}
              </Text>
            </View>
          ))}
        <View style={styles.between}>
          <Text variant="small" color="muted">
            Your share
          </Text>
          <Text variant="small" color="muted" tabular>
            {inr(e.shares[ME] ?? 0)}
          </Text>
        </View>
      </View>
    </Card>
  );
}

export function SplitsScreen() {
  const router = useRouter();
  const s = useSplits();
  const owe = Object.entries(s.overall.byPerson).filter(([, v]) => v < 0);
  const owed = Object.entries(s.overall.byPerson).filter(([, v]) => v > 0);
  const net = s.overall.net;

  return (
    <Screen
      bottom="footer"
      gap={space[22]}
      overlay={
        <StickyFooter>
          <Button label="Add split expense" onPress={() => router.push('/add/split')} />
        </StickyFooter>
      }
    >
      <TopBar
        title="Splits"
        trailing={
          <SmallButton
            label="New group"
            accessibilityHint="Creating groups is not available in this preview"
          />
        }
      />
      <View style={styles.gap4}>
        <Text variant="small" color="muted">
          {net >= 0 ? 'Overall, you’re owed' : 'Overall, you owe'}
        </Text>
        {s.loading ? (
          <Skeleton width={160} height={52} />
        ) : (
          <Money amount={Math.abs(net)} size="md" color={net >= 0 ? 'income' : 'expense'} />
        )}
      </View>
      {owe.length || owed.length ? (
        <ListCard>
          {owe.length ? (
            <View>
              <View style={styles.label}>
                <SectionLabel>You owe</SectionLabel>
              </View>
              {owe.map(([id, v]) => {
                const p = s.person(id);
                return (
                  <ListRow
                    key={id}
                    leading={<Avatar initials={p.initials} tone={p.avatarTone} />}
                    title={p.name}
                    subtitle={`you owe ${inr(-v)}`}
                    subtitleColor="expense"
                    pad={10}
                    trailing={
                      <SmallButton
                        label="Settle up"
                        kind="primary"
                        onPress={() => router.push(`/splits/settle/${id}`)}
                      />
                    }
                  />
                );
              })}
            </View>
          ) : null}
          {owed.length ? (
            <View>
              <View style={styles.label}>
                <SectionLabel>You’re owed</SectionLabel>
              </View>
              {owed.map(([id, v]) => {
                const p = s.person(id);
                return (
                  <ListRow
                    key={id}
                    leading={<Avatar initials={p.initials} tone={p.avatarTone} />}
                    title={p.name}
                    subtitle={`owes you ${inr(v)}`}
                    subtitleColor="income"
                    pad={10}
                    trailing={
                      <SmallButton
                        label="Remind"
                        accessibilityHint="Reminders are not available in this preview"
                      />
                    }
                  />
                );
              })}
            </View>
          ) : null}
        </ListCard>
      ) : (
        <Card>
          <Text variant="body">You’re all square with everyone.</Text>
        </Card>
      )}

      <View style={styles.gap12}>
        <SectionHeader title="Groups" />
        {s.groups.map((g) => {
          const gp = s.groupPos(g.id);
          const ex = s.expenses.filter((e) => e.groupId === g.id);
          const latest = [...ex].sort((a, b) => b.amount - a.amount)[0];
          const members = g.memberIds.map(s.person);
          if (g.about) {
            return (
              <Touchable
                key={g.id}
                onPress={() => router.push(`/splits/${g.id}`)}
                accessibilityLabel={`${g.name}, ${plural(g.memberIds.length, 'member', 'members')}`}
              >
                <Card padding={space[16]}>
                  <View style={styles.groupRow}>
                    <View style={styles.grow}>
                      <Text variant="section">{g.name}</Text>
                      <Text
                        variant="meta"
                        color="muted"
                      >{`${plural(g.memberIds.length, 'member', 'members')} · ${g.about}`}</Text>
                    </View>
                    {gp.net === 0 ? (
                      <Pill label="All settled" />
                    ) : (
                      <Pill
                        label={gp.net < 0 ? `You owe ${inr(-gp.net)}` : `Owed ${inr(gp.net)}`}
                        tone={gp.net < 0 ? 'expense' : 'income'}
                      />
                    )}
                  </View>
                </Card>
              </Touchable>
            );
          }
          return (
            <Touchable
              key={g.id}
              onPress={() => router.push(`/splits/${g.id}`)}
              accessibilityLabel={`${g.name}, ${plural(ex.length, 'expense', 'expenses')}`}
            >
              <Card padding={space[16]} gap={space[16]}>
                <View style={styles.groupRow}>
                  <View style={styles.grow}>
                    <Text variant="greeting">{g.name}</Text>
                    <Text
                      variant="meta"
                      color="muted"
                    >{`${plural(g.memberIds.length, 'member', 'members')} · ${plural(ex.length, 'expense', 'expenses')}`}</Text>
                  </View>
                  <AvatarStack people={members.map((m) => ({ initials: m.initials, tone: m.avatarTone }))} />
                </View>
                {latest ? (
                  <LatestExpense e={latest} memberIds={g.memberIds} name={(id) => s.person(id).name} />
                ) : null}
              </Card>
            </Touchable>
          );
        })}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap4: { gap: space[4] },
  gap6: { gap: space[6] },
  gap12: { gap: space[12] },
  label: { paddingTop: space[12], paddingBottom: space[4] },
  groupRow: { flexDirection: 'row', alignItems: 'center', gap: space[12] },
  grow: { flex: 1, gap: 2 },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: space[8] },
  segs: { flexDirection: 'row', gap: 3 },
  seg: { height: 30, alignItems: 'center', justifyContent: 'center', borderRadius: radius.chip },
});
