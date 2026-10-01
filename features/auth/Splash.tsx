import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Logo, Text } from '@/components';
import { usePrefsStore } from '@/store/prefs';
import { useSessionStore } from '@/store/session';
import { space, useColors } from '@/theme';

/** Splash artboard: brand tile, wordmark, tagline and the page indicator. */
export function SplashView() {
  const c = useColors();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.root, { backgroundColor: c.splashBg, paddingBottom: insets.bottom + 30 }]}>
      <View style={styles.spacer} />
      <View style={styles.brand} accessible accessibilityLabel="DHAN">
        <Logo size={104} variant="splash" />
        <Text variant="wordmark" style={[styles.wordmark, { color: c.splashText }]}>
          DHAN
        </Text>
      </View>
      <View style={styles.bottom}>
        <Text variant="tagline" style={{ color: c.splashTagline }}>
          Dhan Hai Toh Done Hai.
        </Text>
        <View style={styles.dots} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
          <View style={[styles.dotActive, { backgroundColor: c.gold }]} />
          <View style={[styles.dot, { backgroundColor: c.splashDotIdle }]} />
          <View style={[styles.dot, { backgroundColor: c.splashDotIdle }]} />
        </View>
      </View>
    </View>
  );
}

/** Launch route: holds the splash briefly, then goes to Onboarding, Log in, App lock or Home (spec §2). */
export function SplashGate() {
  const router = useRouter();
  const sessionReady = useSessionStore((s) => s.hydrated);
  const prefsReady = usePrefsStore((s) => s.hydrated);
  const hydrated = sessionReady && prefsReady;
  useEffect(() => {
    if (!hydrated) return;
    const t = setTimeout(() => {
      const s = useSessionStore.getState();
      const lockOn = usePrefsStore.getState().appLock;
      if (!s.onboarded) router.replace('/onboarding');
      else if (!s.signedIn) router.replace('/login');
      else if (lockOn && s.locked) router.replace('/lock');
      else router.replace('/(tabs)');
    }, 600);
    return () => clearTimeout(t);
  }, [hydrated, router]);
  return <SplashView />;
}

const styles = StyleSheet.create({
  root: { flex: 1, alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: space[32] },
  spacer: { height: 120 },
  brand: { alignItems: 'center', gap: space[22] },
  wordmark: { paddingLeft: space[8] },
  bottom: { alignItems: 'center', gap: space[20] },
  dots: { flexDirection: 'row', gap: space[6] },
  dotActive: { width: 18, height: 4, borderRadius: 2 },
  dot: { width: 6, height: 4, borderRadius: 2 },
});
