import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import {
  IconTile,
  ListCard,
  ListRow,
  Screen,
  SectionLabel,
  SegmentedControl,
  SelectRow,
  Text,
  Toggle,
  TopBar,
} from '@/components';
import { usePrefsStore, type ThemePref } from '@/store/prefs';
import { space } from '@/theme';

function ToggleRow({
  title,
  body,
  value,
  onChange,
}: {
  title: string;
  body: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <View style={styles.toggleRow}>
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

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <View style={styles.gap10}>
      <SectionLabel>{label}</SectionLabel>
      <ListCard>{children}</ListCard>
    </View>
  );
}

export function SettingsScreen() {
  const router = useRouter();
  const p = usePrefsStore();

  return (
    <Screen gap={space[20]}>
      <TopBar title="Settings" />
      <Group label="Security">
        <ListRow
          leading={<IconTile icon="lock" size="sm" />}
          title="Security and app lock"
          subtitle={p.appLock ? 'Face ID is on' : 'App lock is off'}
          chevron
          onPress={() => router.push('/settings/security')}
        />
      </Group>
      <Group label="Appearance">
        <View style={styles.block}>
          <Text variant="body" weight="medium">
            Theme
          </Text>
          <SegmentedControl<ThemePref>
            accessibilityLabel="Theme"
            value={p.theme}
            onChange={(v) => p.set('theme', v)}
            options={[
              { value: 'system', label: 'System' },
              { value: 'light', label: 'Light' },
              { value: 'dark', label: 'Dark' },
            ]}
          />
        </View>
        <ToggleRow
          title="Hide balances on open"
          body="Tap the balance to reveal it."
          value={p.hideBalances}
          onChange={(v) => p.set('hideBalances', v)}
        />
      </Group>
      <Group label="Region">
        <SelectRow label="Currency" value="₹ Indian Rupee" />
        <SelectRow label="Number format" value="1,00,000" />
        <SelectRow label="Week starts on" value="Monday" />
      </Group>
      <Group label="Money">
        <ToggleRow
          title="Budget alerts"
          body="Heads-up at 90% of any budget."
          value={p.budgetAlerts}
          onChange={(v) => p.set('budgetAlerts', v)}
        />
        <ToggleRow
          title="Weekly summary"
          body="Every Sunday evening."
          value={p.weeklySummary}
          onChange={(v) => p.set('weeklySummary', v)}
        />
        <SelectRow label="Month starts on" value="1st" />
      </Group>
      <Group label="Data">
        <ListRow
          leading={<IconTile icon="download" size="sm" />}
          title="Export data"
          subtitle="CSV or PDF, any date range"
          chevron
          accessibilityHint="Not available in this preview"
        />
        <ListRow
          leading={<IconTile icon="tag" size="sm" />}
          title="Categories"
          chevron
          onPress={() => router.push('/categories')}
        />
      </Group>
      <Group label="Legal">
        <ListRow title="Privacy policy" chevron pad={14} />
        <ListRow title="Terms of use" chevron pad={14} />
      </Group>
      <Text variant="caption" color="muted" align="center">
        DHAN 1.0.0 (build 42)
      </Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  gap10: { gap: space[10] },
  grow: { flex: 1, gap: 2 },
  block: { gap: space[10], paddingVertical: space[14] },
  toggleRow: { flexDirection: 'row', alignItems: 'center', gap: space[12], paddingVertical: space[14] },
});
