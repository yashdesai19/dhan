import { useState, type ReactNode } from 'react';
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';

import { layout, space, useColors } from '@/theme';

/** Pinned footer with a fade from transparent to the background (spec §3). */
export function StickyFooter({ children }: { children: ReactNode }) {
  const c = useColors();
  const insets = useSafeAreaInsets();
  const [box, setBox] = useState({ w: 0, h: 0 });
  return (
    <View
      pointerEvents="box-none"
      onLayout={(e: LayoutChangeEvent) =>
        setBox({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })
      }
      style={[
        styles.footer,
        {
          paddingBottom: Math.max(insets.bottom, layout.stickyPad.bottom),
          paddingTop: layout.stickyPad.top,
          paddingHorizontal: layout.stickyPad.side,
        },
      ]}
    >
      {box.w > 0 ? (
        <View style={StyleSheet.absoluteFill} pointerEvents="none">
          <Svg width={box.w} height={box.h}>
            <Defs>
              <LinearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor={c.bg} stopOpacity={0} />
                <Stop offset="0.28" stopColor={c.bg} stopOpacity={1} />
              </LinearGradient>
            </Defs>
            <Rect width={box.w} height={box.h} fill="url(#fade)" />
          </Svg>
        </View>
      ) : null}
      <View style={styles.content}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  footer: { position: 'absolute', left: 0, right: 0, bottom: 0 },
  content: { gap: space[10] },
});
