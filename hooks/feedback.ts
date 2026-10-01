import * as Haptics from 'expo-haptics';
import { useReducedMotion } from 'react-native-reanimated';

/** Haptics used across the app (spec §9). Failures are ignored (simulators, older devices). */
export const haptics = {
  light: () => {
    try {
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)?.catch?.(() => undefined);
    } catch {}
  },
  success: () => {
    try {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)?.catch?.(() => undefined);
    } catch {}
  },
  warning: () => {
    try {
      void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning)?.catch?.(() => undefined);
    } catch {}
  },
  select: () => {
    try {
      void Haptics.selectionAsync()?.catch?.(() => undefined);
    } catch {}
  },
};

/** Duration helper: instant when the OS asks for reduced motion. */
export function useMotionDuration(ms: number): number {
  const reduced = typeof useReducedMotion === 'function' ? useReducedMotion() : false;
  return reduced ? 0 : ms;
}
