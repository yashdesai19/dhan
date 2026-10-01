import { StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';

import { Icon, type IconName } from '@/components/icons/Icon';
import { Text } from '@/components/ui/Text';
import { Touchable } from '@/components/ui/Touchable';
import { haptics } from '@/hooks/feedback';
import { iconSize, motion, radius, size, space, useColors, useTheme } from '@/theme';

const TABS: Record<string, { label: string; icon: IconName }> = {
  index: { label: 'Home', icon: 'home' },
  activity: { label: 'Activity', icon: 'list' },
  budget: { label: 'Budget', icon: 'pie' },
  more: { label: 'More', icon: 'grid' },
};
const ORDER = ['index', 'activity', 'add', 'budget', 'more'];

/** Height of the bar above the home indicator; toasts sit 20 pt above it. */
export function useTabBarHeight(): number {
  const insets = useSafeAreaInsets();
  return space[8] + size.tabBar + Math.max(insets.bottom, space[8]);
}

function AddButton() {
  const c = useColors();
  const { scheme } = useTheme();
  const router = useRouter();
  const scale = useSharedValue(1);
  const st = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <View style={styles.addSlot}>
      <Animated.View style={st}>
        <Touchable
          feedback="none"
          accessibilityLabel="Add transaction"
          accessibilityHint="Opens add expense, income, transfer or split"
          onPress={() => {
            haptics.light();
            scale.value = withTiming(0.94, { duration: motion.fast }, () => {
              scale.value = withSpring(1, { damping: 12, stiffness: 260 });
            });
            router.push('/add-sheet');
          }}
          style={[
            styles.fab,
            {
              backgroundColor: c.primary,
              shadowColor: scheme === 'dark' ? c.shadowBase : c.primary,
              shadowOpacity: scheme === 'dark' ? 0.5 : 0.28,
            },
          ]}
        >
          <Icon name="plus" size={iconSize.fab} color="onPrimary" strokeWidth={2.2} />
        </Touchable>
      </Animated.View>
    </View>
  );
}

/** Home · Activity · Add · Budget · More, 92 pt with the raised centre Add (spec §3). */
export function TabBar({ state, navigation }: BottomTabBarProps) {
  const c = useColors();
  const insets = useSafeAreaInsets();
  const active = state.routes[state.index]?.name;
  return (
    <View
      accessibilityRole="tablist"
      style={[
        styles.bar,
        { backgroundColor: c.nav, borderTopColor: c.line, paddingBottom: Math.max(insets.bottom, space[8]) },
      ]}
    >
      {ORDER.map((name) => {
        if (name === 'add') return <AddButton key="add" />;
        const tab = TABS[name];
        const route = state.routes.find((r: { name: string; key: string }) => r.name === name);
        if (!tab || !route) return null;
        const on = active === name;
        return (
          <Touchable
            key={name}
            feedback="none"
            accessibilityRole="tab"
            accessibilityLabel={tab.label}
            accessibilityState={{ selected: on }}
            onPress={() => {
              const e = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
              if (!on && !e.defaultPrevented) {
                haptics.select();
                navigation.navigate(name);
              }
            }}
            style={styles.tab}
          >
            <Icon
              name={tab.icon}
              size={iconSize.tab}
              color={on ? 'primary' : 'muted'}
              strokeWidth={on ? 1.9 : 1.75}
            />
            <Text
              variant="micro"
              weight={on ? 'semibold' : 'medium'}
              color={on ? 'primary' : 'muted'}
              maxScale={1.2}
            >
              {tab.label}
            </Text>
          </Touchable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: space[8],
    paddingHorizontal: space[12],
    borderTopWidth: 1,
  },
  tab: { flex: 1, height: size.tabBar, alignItems: 'center', justifyContent: 'center', gap: space[4] },
  addSlot: { flex: 1, alignItems: 'center', height: size.tabBar },
  fab: {
    width: size.fab,
    height: size.fab,
    marginTop: -size.fabLift + (size.tabBar - size.fab) / 2,
    borderRadius: radius.fab,
    alignItems: 'center',
    justifyContent: 'center',
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 8,
  },
});
