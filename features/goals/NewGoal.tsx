import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';

import { Banner, Button, ChipGroup, Screen, SectionLabel, StickyFooter, TextField, TopBar } from '@/components';
import { useCreateGoal } from '@/data/queries';
import { useToday } from '@/features/shared/hooks';
import { useToastStore } from '@/store/ui';
import { space } from '@/theme';
import { groupIN } from '@/utils/format';

const HORIZONS = [
  { value: '3', label: '3 months' },
  { value: '6', label: '6 months' },
  { value: '12', label: '1 year' },
  { value: '24', label: '2 years' },
] as const;
const ICONS = [
  { value: 'target', label: 'General' },
  { value: 'laptop', label: 'Gadget' },
  { value: 'plane', label: 'Travel' },
  { value: 'home', label: 'Home' },
  { value: 'car', label: 'Vehicle' },
  { value: 'shield', label: 'Safety net' },
] as const;

/** The same day N months on (clipped to the month's last day). */
function monthsAhead(today: string, months: number): string {
  const [y, m, d] = today.split('-').map(Number) as [number, number, number];
  const index = m - 1 + months;
  const year = y + Math.floor(index / 12);
  const month = (index % 12) + 1;
  const last = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `${year}-${String(month).padStart(2, '0')}-${String(Math.min(d, last)).padStart(2, '0')}`;
}

export function NewGoalScreen() {
  const router = useRouter();
  const { today } = useToday();
  const create = useCreateGoal();
  const show = useToastStore((s) => s.show);
  const [name, setName] = useState('');
  const [target, setTarget] = useState('');
  const [horizon, setHorizon] = useState<(typeof HORIZONS)[number]['value']>('12');
  const [icon, setIcon] = useState<(typeof ICONS)[number]['value']>('target');
  const [error, setError] = useState<string | null>(null);

  const save = () => {
    setError(null);
    create.mutate(
      {
        name,
        target: Number(target.replace(/[^\d]/g, '') || '0'),
        targetDate: monthsAhead(today, Number(horizon)),
        icon,
      },
      {
        onSuccess: () => {
          router.back();
          show({ message: `${name.trim()} added`, placement: 'bottom' });
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  return (
    <Screen
      bottom="footer"
      gap={space[20]}
      keyboard
      overlay={
        <StickyFooter>
          <Button
            label="Create goal"
            onPress={save}
            loading={create.isPending}
            disabled={!name.trim() || !target.replace(/[^\d]/g, '')}
          />
        </StickyFooter>
      }
    >
      <TopBar variant="modal" title="New goal" />
      <TextField label="What are you saving for?" value={name} onChangeText={setName} placeholder="New laptop" />
      <TextField
        label="Target amount"
        value={target}
        onChangeText={(v) =>
          setTarget(v.replace(/[^\d]/g, '') ? `₹${groupIN(Number(v.replace(/[^\d]/g, '')))}` : '')
        }
        keyboardType="number-pad"
        placeholder="₹0"
      />
      <View style={styles.gap10}>
        <SectionLabel>Reach it in</SectionLabel>
        <ChipGroup options={[...HORIZONS]} selected={[horizon]} onChange={([v]) => v && setHorizon(v)} />
      </View>
      <View style={styles.gap10}>
        <SectionLabel>Kind of goal</SectionLabel>
        <ChipGroup options={[...ICONS]} selected={[icon]} onChange={([v]) => v && setIcon(v)} />
      </View>
      {error ? (
        <Banner icon="alert" tone="error">
          {error}
        </Banner>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({ gap10: { gap: space[10] } });
