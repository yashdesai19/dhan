import { useEffect } from 'react';
import { StyleSheet, View, BackHandler } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon, Logo, Text, TextButton, Touchable } from '@/components';
import { haptics } from '@/hooks/feedback';
import { useSessionStore } from '@/store/session';
import { iconSize, moneySizes, space, useColors } from '@/theme';

/** App lock (spec §16). Biometrics are UI only: tapping the Face ID button unlocks. */
export function LockScreen() {
  const c = useColors();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const unlock = useSessionStore((s) => s.unlock);

  // The lock can't be dismissed with the Android back button.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => true);
    return () => sub.remove();
  }, []);

  const onUnlock = () => {
    haptics.success();
    unlock();
    if (router.canGoBack()) router.back();
    else router.replace('/(tabs)');
  };

  return (
    <View
      style={[
        styles.fill,
        {
          backgroundColor: c.bg,
          paddingTop: insets.top + space[48],
          paddingBottom: insets.bottom + space[24],
        },
      ]}
    >
      <View style={styles.top}>
        <Logo size={64} />
        <Text variant="heading" align="center" accessibilityRole="header" style={styles.title}>
          DHAN is locked
        </Text>
        <Text variant="body" color="muted" align="center">
          Unlock to see your money.
        </Text>
      </View>
      <View style={styles.balance} accessibilityLabel="Total balance hidden">
        <Text variant="small" color="muted">
          Total balance
        </Text>
        <Text variant="display" color="faint" style={styles.mask}>
          ₹ ••••••
        </Text>
      </View>
      <View style={styles.spacer} />
      <View style={styles.bottom}>
        <Touchable
          onPress={onUnlock}
          style={[styles.face, { backgroundColor: c.primarySoft }]}
          accessibilityLabel="Unlock with Face ID"
        >
          <Icon name="faceid" size={iconSize.hero} color="primary" />
        </Touchable>
        <Text variant="small" color="muted" style={styles.hint}>
          Tap to unlock with Face ID
        </Text>
        <TextButton label="Use PIN instead" accessibilityHint="PIN entry is not available in this preview" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1, paddingHorizontal: space[24] },
  top: { alignItems: 'center', gap: space[4] },
  title: { paddingTop: space[22] },
  balance: { alignItems: 'center', gap: space[6], paddingTop: space[44] },
  mask: { fontSize: moneySizes.sm, lineHeight: moneySizes.sm + 6, letterSpacing: 4 },
  spacer: { flex: 1 },
  bottom: { alignItems: 'center', gap: space[10] },
  hint: { paddingTop: space[4] },
  face: { width: 88, height: 88, borderRadius: 44, alignItems: 'center', justifyContent: 'center' },
});
