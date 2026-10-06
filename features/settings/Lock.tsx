import { useCallback, useEffect, useRef, useState } from 'react';
import { BackHandler, Platform, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import * as LocalAuthentication from 'expo-local-authentication';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon, Logo, Text, TextButton, Touchable } from '@/components';
import { haptics } from '@/hooks/feedback';
import { useSessionStore } from '@/store/session';
import { iconSize, moneySizes, space, useColors } from '@/theme';

const BIOMETRIC = Platform.OS === 'ios' ? 'Face ID' : 'fingerprint';

/**
 * Asks the phone to confirm it's the owner: fingerprint or Face ID, with the phone's own PIN,
 * pattern or password as the fallback. A phone with no screen lock has nothing to check against.
 */
async function confirmOwner(): Promise<boolean> {
  const level = await LocalAuthentication.getEnrolledLevelAsync();
  if (level === LocalAuthentication.SecurityLevel.NONE) return true;
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Unlock DHAN',
    cancelLabel: 'Cancel',
    disableDeviceFallback: false,
  });
  return result.success;
}

/** App lock (spec §16): opens only after the phone confirms its owner. */
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

  const [failed, setFailed] = useState(false);
  const busy = useRef(false);
  const onUnlock = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      if (!(await confirmOwner())) {
        setFailed(true);
        return;
      }
      haptics.success();
      unlock();
      if (router.canGoBack()) router.back();
      else router.replace('/(tabs)');
    } finally {
      busy.current = false;
    }
  }, [router, unlock]);

  // Ask straight away, as banking apps do
  useEffect(() => {
    void onUnlock();
  }, [onUnlock]);

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
          onPress={() => void onUnlock()}
          style={[styles.face, { backgroundColor: c.primarySoft }]}
          accessibilityLabel={`Unlock with ${BIOMETRIC}`}
        >
          <Icon name="faceid" size={iconSize.hero} color="primary" />
        </Touchable>
        <Text variant="small" color={failed ? 'expense' : 'muted'} style={styles.hint}>
          {failed ? 'Not unlocked. Tap to try again.' : `Tap to unlock with ${BIOMETRIC}`}
        </Text>
        <TextButton
          label="Use phone PIN instead"
          onPress={() => void onUnlock()}
          accessibilityHint="Unlock with your phone's PIN, pattern or password"
        />
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
