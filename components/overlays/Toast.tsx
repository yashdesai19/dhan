import { useEffect } from 'react';
import { AccessibilityInfo, StyleSheet, View } from 'react-native';
import Animated, { FadeInDown, FadeOutDown } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Icon } from '@/components/icons/Icon';
import { useTabBarHeight } from '@/components/navigation/TabBar';
import { Text } from '@/components/ui/Text';
import { Touchable } from '@/components/ui/Touchable';
import { haptics, useMotionDuration } from '@/hooks/feedback';
import { iconSize, motion, radius, space, useColors, useTheme } from '@/theme';
import { light } from '@/theme/colors';
import { useToastStore } from '@/store/ui';

/** Single global toast with Undo, 5 s (spec §9). Mounted once in the app layout. */
export function ToastHost() {
  const current = useToastStore((s) => s.current);
  const hide = useToastStore((s) => s.hide);
  const c = useColors();
  const { scheme } = useTheme();
  const insets = useSafeAreaInsets();
  const tabBar = useTabBarHeight();
  const d = useMotionDuration(motion.base);

  useEffect(() => {
    if (!current) return;
    haptics.success();
    AccessibilityInfo.announceForAccessibility(current.message);
    const id = current.id;
    const t = setTimeout(() => hide(id), motion.toastHold);
    return () => clearTimeout(t);
  }, [current, hide]);

  if (!current) return null;
  const bottom =
    current.placement === 'tabs'
      ? tabBar + space[20]
      : current.placement === 'footer'
        ? Math.max(insets.bottom, 34) + 86
        : insets.bottom + space[24];

  return (
    <View pointerEvents="box-none" style={StyleSheet.absoluteFill}>
      <Animated.View
        key={current.id}
        entering={FadeInDown.duration(d)}
        exiting={FadeOutDown.duration(d)}
        accessibilityRole="alert"
        accessibilityLiveRegion="polite"
        style={[
          styles.toast,
          {
            bottom,
            backgroundColor: c.toastBg,
            shadowOpacity: scheme === 'dark' ? 0.4 : 0.18,
          },
        ]}
      >
        <Icon
          name="check"
          size={iconSize.xl}
          color={scheme === 'light' ? 'gold' : 'primary'}
          strokeWidth={2}
        />
        <Text variant="small" color="toastText" style={styles.msg}>
          {current.message}
        </Text>
        {current.actionLabel ? (
          <Touchable
            accessibilityLabel={current.actionLabel}
            onPress={() => {
              hide(current.id);
              current.onAction?.();
            }}
            style={styles.action}
          >
            <Text variant="small" weight="semibold" color={scheme === 'light' ? 'gold' : 'primary'}>
              {current.actionLabel}
            </Text>
          </Touchable>
        ) : null}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    left: space[16],
    right: space[16],
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[12],
    borderRadius: radius.toast,
    paddingVertical: space[4],
    paddingLeft: space[16],
    paddingRight: space[8],
    minHeight: 52,
    shadowColor: light.shadowBase,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 8 },
    elevation: 10,
  },
  msg: { flex: 1, paddingVertical: space[10] },
  action: {
    minHeight: 44,
    minWidth: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: space[8],
  },
});
