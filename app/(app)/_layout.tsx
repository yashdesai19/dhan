import { useEffect, useRef, useState } from 'react';
import { AppState, StyleSheet, View, type AppStateStatus } from 'react-native';
import { Redirect, Stack, useRouter } from 'expo-router';

import { ToastHost } from '@/components';
import { SplashView } from '@/features/auth/Splash';
import { usePrefsStore } from '@/store/prefs';
import { useSessionStore } from '@/store/session';
import { useColors } from '@/theme';

const LOCK_AFTER_MS = { now: 0, '1m': 60_000, '5m': 300_000 } as const;

/** Re-locks after the chosen idle time and hides balances in the app switcher (spec §16). */
function useLockAndPrivacy() {
  const router = useRouter();
  const [inactive, setInactive] = useState(false);
  const leftAt = useRef<number | null>(null);
  useEffect(() => {
    const sub = AppState.addEventListener('change', (s: AppStateStatus) => {
      const prefs = usePrefsStore.getState();
      if (s !== 'active') {
        setInactive(prefs.hideInSwitcher);
        leftAt.current ??= Date.now();
        return;
      }
      setInactive(false);
      const away = leftAt.current ? Date.now() - leftAt.current : 0;
      leftAt.current = null;
      if (prefs.appLock && away >= LOCK_AFTER_MS[prefs.lockAfter] && !useSessionStore.getState().locked) {
        useSessionStore.getState().lock();
        router.push('/lock');
      }
    });
    return () => sub.remove();
  }, [router]);
  return inactive;
}

const modal = {
  presentation: 'fullScreenModal',
  animation: 'slide_from_bottom',
  gestureEnabled: false,
} as const;
const sheet = {
  presentation: 'transparentModal',
  animation: 'none',
  contentStyle: { backgroundColor: 'transparent' },
} as const;

export default function AppLayout() {
  const c = useColors();
  const sessionReady = useSessionStore((s) => s.hydrated);
  const prefsReady = usePrefsStore((s) => s.hydrated);
  const hydrated = sessionReady && prefsReady;
  const signedIn = useSessionStore((s) => s.signedIn);
  const cover = useLockAndPrivacy();
  // Only a cold start or deep link into a locked app redirects. Later locks (resume, "Preview
  // lock screen") push /lock above this stack so it stays mounted and Unlock returns in place.
  const [lockedOnEntry] = useState(() => {
    const s = useSessionStore.getState();
    const p = usePrefsStore.getState();
    return p.appLock && s.locked;
  });

  if (!hydrated) return null;
  if (!signedIn) return <Redirect href="/login" />;
  if (lockedOnEntry) return <Redirect href="/lock" />;

  return (
    <View style={[styles.fill, { backgroundColor: c.bg }]}>
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="add/expense" options={modal} />
        <Stack.Screen name="add/income" options={modal} />
        <Stack.Screen name="add/transfer" options={modal} />
        <Stack.Screen name="add/split" options={modal} />
        <Stack.Screen name="transactions/[id]/edit" options={modal} />
        <Stack.Screen name="accounts/edit" options={modal} />
        <Stack.Screen name="splits/settled" options={{ ...modal, animation: 'fade' }} />
        <Stack.Screen name="add-sheet" options={sheet} />
        <Stack.Screen name="transactions/filters" options={sheet} />
        <Stack.Screen name="transactions/[id]/delete" options={sheet} />
        <Stack.Screen name="budget/[category]/edit" options={sheet} />
        <Stack.Screen name="splits/settle/[personId]" options={sheet} />
        <Stack.Screen name="goals/[id]/add" options={sheet} />
        <Stack.Screen name="sign-out" options={sheet} />
      </Stack>
      <ToastHost />
      {cover ? (
        <View style={StyleSheet.absoluteFill} accessibilityElementsHidden>
          <SplashView />
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({ fill: { flex: 1 } });
