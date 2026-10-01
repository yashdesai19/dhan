import { useMemo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter, type Href } from 'expo-router';

import {
  Avatar,
  Icon,
  IconTile,
  ListCard,
  ListRow,
  Pill,
  Screen,
  SectionLabel,
  Text,
  Touchable,
} from '@/components';
import type { IconName } from '@/components/icons/paths';
import { useNotifications, useUser } from '@/data/queries';
import { useSplits } from '@/features/splits/useSplits';
import { useMoneyData } from '@/features/shared/hooks';
import { iconSize, radius, space, useColors } from '@/theme';
import { inr } from '@/utils/format';

interface Item {
  icon: IconName;
  title: string;
  subtitle?: string;
  href?: Href;
  trailing?: ReactNode;
}

function Section({ label, items }: { label: string; items: Item[] }) {
  const router = useRouter();
  return (
    <View style={styles.gap10}>
      <SectionLabel>{label}</SectionLabel>
      <ListCard>
        {items.map((i) => (
          <ListRow
            key={i.title}
            leading={<IconTile icon={i.icon} size="sm" />}
            title={i.title}
            subtitle={i.subtitle}
            trailing={i.trailing}
            chevron
            onPress={i.href ? () => router.push(i.href as Href) : undefined}
            accessibilityHint={i.href ? undefined : 'Not available in this preview'}
          />
        ))}
      </ListCard>
    </View>
  );
}

export function MoreScreen() {
  const c = useColors();
  const router = useRouter();
  const user = useUser().data;
  const money = useMoneyData();
  const splits = useSplits();
  const unread = (useNotifications().data ?? []).filter((n) => n.unread).length;
  const accounts = useMemo(() => money.accounts.filter((a) => !a.archived).length, [money.accounts]);
  const net = splits.overall.net;

  return (
    <Screen top="tab" bottom="tabs" gap={space[20]}>
      <Text variant="title" accessibilityRole="header">
        More
      </Text>
      <Touchable
        onPress={() => router.push('/profile')}
        style={styles.profile}
        accessibilityLabel={`${user?.name ?? 'Profile'}, ${user?.email ?? ''}. Edit profile`}
      >
        <Avatar initials={user?.initials ?? ''} size="profile" />
        <View style={styles.grow}>
          <Text variant="profileName">{user?.name ?? ''}</Text>
          <Text variant="small" color="muted">
            {user?.email ?? ''}
          </Text>
        </View>
        <Icon name="chevR" size={iconSize.lg} color="faint" strokeWidth={2} />
      </Touchable>
      <Touchable
        onPress={() => router.push('/assistant')}
        style={[styles.ai, { backgroundColor: c.primarySoft }]}
        accessibilityLabel="Ask DHAN AI"
      >
        <Icon name="sparkle" size={iconSize.xxl} color="primary" />
        <View style={styles.grow}>
          <Text variant="body" weight="semibold">
            Ask DHAN AI
          </Text>
          <Text variant="meta" color="muted">
            “How much did I save this month?”
          </Text>
        </View>
        <Icon name="chevR" size={iconSize.lg} color="faint" strokeWidth={2} />
      </Touchable>
      <Section
        label="Money"
        items={[
          {
            icon: 'bank',
            title: 'Accounts',
            href: '/accounts',
            trailing: (
              <Text variant="small" color="muted">
                {String(accounts)}
              </Text>
            ),
          },
          { icon: 'tag', title: 'Categories', href: '/categories' },
          {
            icon: 'users',
            title: 'Splits and groups',
            href: '/splits',
            trailing: net ? (
              <Pill label={inr(Math.abs(net))} tone={net > 0 ? 'income' : 'expense'} small />
            ) : undefined,
          },
          { icon: 'target', title: 'Goals', href: '/goals' },
          { icon: 'repeat', title: 'Recurring and subscriptions', href: '/recurring' },
          { icon: 'chart', title: 'Reports and net worth', href: '/reports' },
        ]}
      />
      <Section
        label="Preferences"
        items={[
          {
            icon: 'bell',
            title: 'Notifications',
            href: '/notifications',
            trailing: unread ? <Pill label={String(unread)} tone="solid" small /> : undefined,
          },
          { icon: 'shield', title: 'Settings', subtitle: 'Security, theme, export', href: '/settings' },
        ]}
      />
      <Section
        label="Support"
        items={[
          { icon: 'help', title: 'Help centre' },
          { icon: 'lock', title: 'Privacy' },
          { icon: 'doc', title: 'Terms of use' },
        ]}
      />
      <ListCard>
        <ListRow
          leading={<IconTile icon="logout" size="sm" tone="expense" />}
          title="Sign out"
          onPress={() => router.push('/sign-out')}
          accessibilityHint="Asks for confirmation"
        />
      </ListCard>
      <Text variant="caption" color="muted" align="center">
        DHAN 1.0.0 · Dhan Hai Toh Done Hai.
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap10: { gap: space[10] },
  grow: { flex: 1, gap: 2 },
  profile: { flexDirection: 'row', alignItems: 'center', gap: space[14] },
  ai: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[12],
    borderRadius: radius.quick,
    paddingVertical: space[14],
    paddingHorizontal: space[16],
  },
});
