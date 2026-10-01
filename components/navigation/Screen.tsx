import type { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { layout, space, useColors } from '@/theme';

export type TopInset = 'stack' | 'tab' | 'home' | 'none';

const TOP: Record<TopInset, number> = {
  stack: layout.topStack,
  tab: layout.topTab,
  home: layout.topHome,
  none: layout.canvasStatusArea,
};

/** Canvas offsets include a 47 pt status area; below the real safe area we apply the remainder. */
export function useTopPadding(kind: TopInset): number {
  const insets = useSafeAreaInsets();
  return insets.top + Math.max(space[8], TOP[kind] - layout.canvasStatusArea);
}

export interface ScreenProps {
  children?: ReactNode;
  top?: TopInset;
  /** Room below content: tab roots (24), a sticky footer (120), else 40 + home indicator. */
  bottom?: 'tabs' | 'footer' | 'none';
  gap?: number;
  gutter?: number;
  scroll?: boolean;
  refresh?: { refreshing: boolean; onRefresh: () => void };
  /** Pinned to the bottom (StickyFooter, tab bar, input bar). */
  overlay?: ReactNode;
  keyboard?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  testID?: string;
}

/** Scrollable screen body with safe-area insets and the canvas gutters (spec §4, §16–17). */
export function Screen({
  children,
  top = 'stack',
  bottom = 'none',
  gap = layout.sectionGap,
  gutter = layout.gutter,
  scroll = true,
  refresh,
  overlay,
  keyboard,
  contentStyle,
  testID,
}: ScreenProps) {
  const c = useColors();
  const insets = useSafeAreaInsets();
  const paddingTop = useTopPadding(top);
  // The tab bar takes its own layout space; a sticky footer floats, so content clears it (120).
  const paddingBottom =
    bottom === 'tabs'
      ? space[24]
      : bottom === 'footer'
        ? layout.bottomScrollPad + Math.max(0, insets.bottom - 34)
        : space[40] + insets.bottom;
  const content = [{ paddingTop, paddingBottom, paddingHorizontal: gutter, gap }, contentStyle];
  const body = scroll ? (
    <ScrollView
      testID={testID}
      style={styles.fill}
      contentContainerStyle={content}
      showsVerticalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      keyboardDismissMode="interactive"
      refreshControl={
        refresh ? (
          <RefreshControl
            refreshing={refresh.refreshing}
            onRefresh={refresh.onRefresh}
            tintColor={c.muted}
            colors={[c.primary]}
          />
        ) : undefined
      }
    >
      {children}
    </ScrollView>
  ) : (
    <View testID={testID} style={[styles.fill, content]}>
      {children}
    </View>
  );
  const inner = (
    <View style={[styles.fill, { backgroundColor: c.bg }]}>
      {body}
      {overlay}
    </View>
  );
  if (!keyboard) return inner;
  return (
    <KeyboardAvoidingView style={styles.fill} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      {inner}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({ fill: { flex: 1 } });
