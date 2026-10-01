import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter, type Href } from 'expo-router';

import {
  IconTile,
  ListCard,
  Screen,
  SectionLabel,
  Skeleton,
  Text,
  TextButton,
  Toggle,
  TopBar,
  Touchable,
} from '@/components';
import { useMarkAllRead, useNotifications } from '@/data/queries';
import { usePrefsStore, type Prefs } from '@/store/prefs';
import { radius, space, useColors } from '@/theme';
import type { AppNotification } from '@/types/domain';

const NotificationRow = memo(function NotificationRow({
  n,
  onPress,
}: {
  n: AppNotification;
  onPress: () => void;
}) {
  const c = useColors();
  return (
    <Touchable
      onPress={onPress}
      style={styles.row}
      accessibilityLabel={`${n.unread ? 'Unread. ' : ''}${n.title}. ${n.body}. ${n.at}`}
    >
      <IconTile icon={n.icon} tone={n.tone} />
      <View style={styles.body}>
        <Text variant="body" weight={n.unread ? 'semibold' : 'medium'}>
          {n.title}
        </Text>
        <Text variant="meta" color="muted">
          {n.body}
        </Text>
        <Text variant="caption" color="muted">
          {n.at}
        </Text>
      </View>
      <View style={[styles.dot, n.unread ? { backgroundColor: c.primary } : null]} />
    </Touchable>
  );
});

const SEND: { key: keyof Prefs['notify']; title: string; body: string }[] = [
  { key: 'bills', title: 'Bill and EMI reminders', body: '1 day before' },
  { key: 'budget', title: 'Budget alerts', body: 'At 90% and when you go over' },
  { key: 'splits', title: 'Split activity', body: 'New expenses and payments' },
  { key: 'ai', title: 'AI insights', body: 'A useful tip, at most once a week' },
];

export function NotificationsScreen() {
  const router = useRouter();
  const list = useNotifications();
  const markAll = useMarkAllRead();
  const notify = usePrefsStore((s) => s.notify);
  const setNotify = usePrefsStore((s) => s.setNotify);
  const items = list.data ?? [];
  const anyUnread = items.some((n) => n.unread);

  const section = (key: AppNotification['section'], label: string) => {
    const rows = items.filter((n) => n.section === key);
    if (!rows.length) return null;
    return (
      <View style={styles.section}>
        <SectionLabel>{label}</SectionLabel>
        <ListCard>
          {rows.map((n) => (
            <NotificationRow key={n.id} n={n} onPress={() => router.push(n.route as Href)} />
          ))}
        </ListCard>
      </View>
    );
  };

  return (
    <Screen gap={space[20]}>
      <TopBar
        title="Notifications"
        trailing={
          <TextButton
            label="Mark all read"
            onPress={() => markAll.mutate()}
            disabled={!anyUnread || markAll.isPending}
          />
        }
      />
      {list.isPending ? <Skeleton width="100%" height={180} radius={radius.card} /> : null}
      {section('today', 'Today')}
      {section('earlier', 'Earlier')}
      <View style={styles.gap10}>
        <SectionLabel>Send me</SectionLabel>
        <ListCard>
          {SEND.map((s) => (
            <View key={s.key}>
              <View style={styles.toggleRow}>
                <View style={styles.grow}>
                  <Text variant="body" weight="medium">
                    {s.title}
                  </Text>
                  <Text variant="meta" color="muted">
                    {s.body}
                  </Text>
                </View>
                <Toggle
                  value={notify[s.key]}
                  onChange={(v) => setNotify(s.key, v)}
                  accessibilityLabel={s.title}
                />
              </View>
            </View>
          ))}
        </ListCard>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap10: { gap: space[10] },
  grow: { flex: 1, gap: 2 },
  body: { flex: 1, gap: 3 },
  section: { gap: space[6] },
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: space[12], paddingVertical: space[14] },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: space[6] },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: space[12], paddingVertical: space[12] },
});
