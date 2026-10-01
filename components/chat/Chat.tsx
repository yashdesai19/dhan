import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  FadeIn,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { Icon } from '@/components/icons/Icon';
import { Text } from '@/components/ui/Text';
import { useMotionDuration } from '@/hooks/feedback';
import { iconSize, layout, radius, space, useColors } from '@/theme';

function AiAvatar() {
  const c = useColors();
  return (
    <View style={[styles.avatar, { backgroundColor: c.primarySoft }]}>
      <Icon name="sparkle" size={iconSize.md} color="primary" />
    </View>
  );
}

export function ChatBubble({
  role,
  text,
  stats = [],
}: {
  role: 'user' | 'ai';
  text: string;
  stats?: { label: string; value: string }[];
}) {
  const c = useColors();
  const d = useMotionDuration(200);
  if (role === 'user') {
    return (
      <View style={styles.userRow}>
        <View style={[styles.userBubble, { backgroundColor: c.primary }]}>
          <Text variant="body" color="onPrimary">
            {text}
          </Text>
        </View>
      </View>
    );
  }
  return (
    <Animated.View
      entering={FadeIn.duration(d)}
      style={styles.aiRow}
      accessible
      accessibilityLabel={`DHAN AI: ${text}`}
    >
      <AiAvatar />
      <View style={styles.aiBody}>
        <Text variant="body" style={styles.aiText}>
          {text}
        </Text>
        {stats.length ? (
          <View style={styles.stats}>
            {stats.map((s) => (
              <View key={s.label} style={[styles.stat, { backgroundColor: c.surface, borderColor: c.line }]}>
                <Text variant="micro" color="muted" weight="regular">
                  {s.label}
                </Text>
                <Text variant="body" weight="semibold" tabular numberOfLines={1}>
                  {s.value}
                </Text>
              </View>
            ))}
          </View>
        ) : null}
      </View>
    </Animated.View>
  );
}

function Dot({ delay, color }: { delay: number; color: string }) {
  const d = useMotionDuration(300);
  const o = useSharedValue(0.4);
  useEffect(() => {
    if (d === 0) return;
    o.value = withDelay(
      delay,
      withRepeat(withSequence(withTiming(1, { duration: d }), withTiming(0.4, { duration: d })), -1, false),
    );
  }, [d, delay, o]);
  const st = useAnimatedStyle(() => ({ opacity: o.value }));
  return <Animated.View style={[styles.dot, { backgroundColor: color }, st]} />;
}

export function TypingIndicator() {
  const c = useColors();
  return (
    <View style={styles.typingRow}>
      <AiAvatar />
      <View
        accessibilityRole="progressbar"
        accessibilityLabel="DHAN AI is thinking"
        accessibilityLiveRegion="polite"
        style={[styles.typing, { backgroundColor: c.surface, borderColor: c.line }]}
      >
        <Dot delay={0} color={c.faint} />
        <Dot delay={150} color={c.muted} />
        <Dot delay={300} color={c.faint} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  userRow: { flexDirection: 'row', justifyContent: 'flex-end' },
  userBubble: {
    maxWidth: layout.chatUserMax,
    paddingVertical: space[12],
    paddingHorizontal: space[16],
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderBottomRightRadius: 6,
    borderBottomLeftRadius: 20,
  },
  aiRow: { flexDirection: 'row', gap: space[10], alignItems: 'flex-start' },
  aiBody: { flex: 1, maxWidth: layout.chatAiMax, gap: space[10] },
  aiText: { lineHeight: 22 },
  stats: { flexDirection: 'row', gap: space[8] },
  stat: { flex: 1, borderWidth: 1, borderRadius: radius.tile, padding: space[10], gap: 2 },
  typingRow: { flexDirection: 'row', gap: space[10], alignItems: 'center' },
  typing: {
    flexDirection: 'row',
    gap: 5,
    paddingVertical: space[14],
    paddingHorizontal: space[16],
    borderRadius: 18,
    borderWidth: 1,
  },
  dot: { width: 7, height: 7, borderRadius: 4 },
});
