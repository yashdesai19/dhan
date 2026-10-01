import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  IconTile,
  ListCard,
  ListRow,
  Pill,
  Screen,
  SectionLabel,
  SegmentedControl,
  SmallButton,
  Text,
  TextButton,
  Toggle,
  TopBar,
} from '@/components';
import { useDevices } from '@/data/queries';
import { haptics } from '@/hooks/feedback';
import { usePrefsStore, type LockAfter } from '@/store/prefs';
import { useSessionStore } from '@/store/session';
import { space } from '@/theme';

function ToggleRow({
  title,
  body,
  value,
  onChange,
  icon,
}: {
  title: string;
  body: string;
  value: boolean;
  onChange: (v: boolean) => void;
  icon?: boolean;
}) {
  return (
    <View style={styles.row}>
      {icon ? <IconTile icon="faceid" tone="primary" /> : null}
      <View style={styles.grow}>
        <Text variant="body" weight="medium">
          {title}
        </Text>
        <Text variant="meta" color="muted">
          {body}
        </Text>
      </View>
      <Toggle value={value} onChange={onChange} accessibilityLabel={title} />
    </View>
  );
}

export function SecurityScreen() {
  const router = useRouter();
  const p = usePrefsStore();
  const devices = useDevices().data ?? [];
  const lock = useSessionStore((s) => s.lock);
  const unlock = useSessionStore((s) => s.unlock);

  return (
    <Screen gap={space[20]}>
      <TopBar title="Security" />
      <View style={styles.gap10}>
        <SectionLabel>App lock</SectionLabel>
        <ListCard>
          <ToggleRow
            icon
            title="App lock"
            body="Face ID or fingerprint to open DHAN"
            value={p.appLock}
            onChange={(v) => {
              // The session starts locked; turning the lock on shouldn't lock this session.
              if (v) unlock();
              p.set('appLock', v);
            }}
          />
          {p.appLock ? (
            <>
              <View style={styles.block}>
                <Text variant="body" weight="medium">
                  Lock after
                </Text>
                <SegmentedControl<LockAfter>
                  compact
                  accessibilityLabel="Lock after"
                  value={p.lockAfter}
                  onChange={(v) => p.set('lockAfter', v)}
                  options={[
                    { value: 'now', label: 'Right away' },
                    { value: '1m', label: '1 min' },
                    { value: '5m', label: '5 min' },
                  ]}
                />
              </View>
            </>
          ) : null}
          <ToggleRow
            title="Hide balances in app switcher"
            body="Blurs DHAN in recent apps."
            value={p.hideInSwitcher}
            onChange={(v) => p.set('hideInSwitcher', v)}
          />
        </ListCard>
      </View>
      <View style={styles.gap10}>
        <SectionLabel>Account</SectionLabel>
        <ListCard>
          <ListRow
            leading={<IconTile icon="key" size="sm" />}
            title="Change PIN"
            chevron
            accessibilityHint="Not available in this preview"
          />
          <ListRow
            leading={<IconTile icon="lock" size="sm" />}
            title="Change password"
            chevron
            accessibilityHint="Not available in this preview"
          />
          <ListRow
            leading={<IconTile icon="shield" size="sm" />}
            title="Two-step sign-in"
            trailing={
              <Text variant="small" color="muted">
                On
              </Text>
            }
            chevron
          />
        </ListCard>
      </View>
      <View style={styles.gap10}>
        <SectionLabel>Signed-in devices</SectionLabel>
        <ListCard>
          {devices.map((d) => (
            <ListRow
              key={d.id}
              leading={<IconTile icon="phone" size="sm" />}
              title={d.name}
              subtitle={d.lastUsed}
              trailing={
                d.current ? (
                  <Pill label="Active" tone="income" small />
                ) : (
                  <SmallButton
                    label="Sign out"
                    accessibilityHint={`Signs out ${d.name}. Not available in this preview`}
                  />
                )
              }
            />
          ))}
        </ListCard>
      </View>
      <Text variant="meta" color="muted" align="center">
        DHAN never asks for your bank passwords or UPI PIN.
      </Text>
      <View style={styles.center}>
        <TextButton
          label="Preview lock screen"
          onPress={() => {
            haptics.light();
            lock();
            router.push('/lock');
          }}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap10: { gap: space[10] },
  grow: { flex: 1, gap: 2 },
  row: { flexDirection: 'row', alignItems: 'center', gap: space[12], paddingVertical: space[14] },
  block: { gap: space[10], paddingVertical: space[14] },
  center: { alignItems: 'center' },
});
