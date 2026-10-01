// Display components: tiles, avatars, badges, pills, progress, banners, empty state, skeleton.
import { useEffect, type ReactNode } from 'react';
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  useAnimatedProps,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';

import { Icon, type IconName } from '@/components/icons/Icon';
import { useMotionDuration } from '@/hooks/feedback';
import {
  avatarSize,
  fonts,
  iconSize,
  layout,
  motion,
  radius,
  size,
  space,
  tileSize,
  useColors,
  type ColorName,
  type TileSize,
} from '@/theme';
import type { AvatarTone } from '@/types/domain';
import { badge } from '@/utils/dates';
import { Text } from './Text';

// ---------------------------------------------------------------- IconTile / LetterTile

export type Tone = 'neutral' | 'income' | 'expense' | 'warn' | 'primary' | 'surface';

export function toneColors(tone: Tone): { bg: ColorName; fg: ColorName } {
  switch (tone) {
    case 'income':
      return { bg: 'incomeSoft', fg: 'income' };
    case 'expense':
      return { bg: 'expenseSoft', fg: 'expense' };
    case 'warn':
      return { bg: 'warnSoft', fg: 'warnText' };
    case 'primary':
      return { bg: 'primarySoft', fg: 'primary' };
    case 'surface':
      return { bg: 'surface', fg: 'ink' };
    default:
      return { bg: 'soft', fg: 'ink' };
  }
}

interface TileProps {
  icon: IconName;
  size?: TileSize;
  tone?: Tone;
}

/** 36 / 42 / 48 / 60 rounded squares with a category or action icon. */
export function IconTile({ icon, size: sz = 'md', tone = 'neutral' }: TileProps) {
  const c = useColors();
  const t = tileSize[sz];
  const col = toneColors(tone);
  return (
    <View
      style={[
        styles.tile,
        { width: t.box, height: t.box, borderRadius: t.radius, backgroundColor: c[col.bg] },
      ]}
    >
      <Icon name={icon} size={t.icon} color={col.fg} />
    </View>
  );
}

export function LetterTile({ letter, size: sz = 'md' }: { letter: string; size?: TileSize }) {
  const c = useColors();
  const t = tileSize[sz];
  return (
    <View
      style={[styles.tile, { width: t.box, height: t.box, borderRadius: t.radius, backgroundColor: c.soft }]}
    >
      <Text variant="section" weight="semibold">
        {letter}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- Avatar

const AVATAR: Record<AvatarTone, { bg: ColorName; fg: ColorName }> = {
  primary: { bg: 'primary', fg: 'onPrimary' },
  blue: { bg: 'blueSoft', fg: 'blueInk' },
  green: { bg: 'primarySoft', fg: 'primary' },
  sand: { bg: 'sandSoft', fg: 'sandInk' },
};

interface AvatarProps {
  initials: string;
  tone?: AvatarTone;
  size?: keyof typeof avatarSize;
  ring?: boolean;
  overlap?: boolean;
  /** Home greeting uses the soft primary avatar. */
  soft?: boolean;
}

export function Avatar({ initials, tone = 'primary', size: sz = 'xl', ring, overlap, soft }: AvatarProps) {
  const c = useColors();
  const s = avatarSize[sz];
  const col = soft ? { bg: 'primarySoft' as ColorName, fg: 'primary' as ColorName } : AVATAR[tone];
  const fs = s <= 32 ? 11 : s <= 44 ? 14 : s <= 56 ? 18 : 28;
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[
        styles.tile,
        { width: s, height: s, borderRadius: s / 2, backgroundColor: c[col.bg] },
        ring ? { borderWidth: 2, borderColor: c.surface } : null,
        overlap ? { marginLeft: -8 } : null,
      ]}
    >
      <Text maxScale={1.2} style={{ fontFamily: fonts.semibold, fontSize: fs, color: c[col.fg] }}>
        {initials}
      </Text>
    </View>
  );
}

export function AvatarStack({
  people,
  size: sz = 'sm',
}: {
  people: { initials: string; tone: AvatarTone }[];
  size?: keyof typeof avatarSize;
}) {
  return (
    <View style={styles.row} accessible accessibilityLabel={`${people.length} members`}>
      {people.map((p, i) => (
        <Avatar key={p.initials} initials={p.initials} tone={p.tone} size={sz} ring overlap={i > 0} />
      ))}
    </View>
  );
}

// ---------------------------------------------------------------- DateBadge

export function DateBadge({ date, tone }: { date: string; tone?: 'warn' }) {
  const c = useColors();
  const b = badge(date);
  return (
    <View
      style={[styles.dateBadge, { backgroundColor: tone === 'warn' ? c.warnSoft : c.soft }]}
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      <Text
        variant="section"
        weight="semibold"
        color={tone === 'warn' ? 'warnText' : 'ink'}
        style={styles.badgeDay}
      >
        {b.day}
      </Text>
      <Text variant="badgeMonth" color={tone === 'warn' ? 'warnText' : 'ink'}>
        {b.mon}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- KpiTile, Pill

export function KpiTile({ label, value, tone }: { label: string; value: string; tone?: 'income' }) {
  const c = useColors();
  return (
    <View
      style={[styles.kpi, { backgroundColor: c.surface, borderColor: c.line }]}
      accessible
      accessibilityLabel={`${label}, ${value}`}
    >
      <Text variant="caption" color="muted">
        {label}
      </Text>
      <Text
        variant="sheetTitle"
        tabular
        color={tone === 'income' ? 'income' : 'ink'}
        numberOfLines={1}
        maxScale={1.3}
      >
        {value}
      </Text>
    </View>
  );
}

interface PillProps {
  label: string;
  tone?: Tone | 'solid';
  small?: boolean;
}

export function Pill({ label, tone = 'neutral', small }: PillProps) {
  const c = useColors();
  const col =
    tone === 'solid' ? { bg: 'primary' as ColorName, fg: 'onPrimary' as ColorName } : toneColors(tone);
  return (
    <View style={[styles.pill, { backgroundColor: c[col.bg] }, small ? styles.pillSmall : null]}>
      <Text variant={small ? 'micro' : 'meta'} weight="semibold" color={col.fg} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- Progress

interface ProgressBarProps {
  value: number;
  tone?: 'primary' | 'warn' | 'expense';
  height?: 6 | 8 | 10 | 12;
  accessibilityLabel?: string;
}

/** Fills from 0 on first view, 500 ms ease-out (spec §9). */
export function ProgressBar({ value, tone = 'primary', height = 6, accessibilityLabel }: ProgressBarProps) {
  const c = useColors();
  const pct = Math.max(0, Math.min(100, value));
  const duration = useMotionDuration(motion.progress);
  const w = useSharedValue(duration === 0 ? pct : 0);
  useEffect(() => {
    w.value = withTiming(pct, { duration, easing: Easing.out(Easing.cubic) });
  }, [pct, duration, w]);
  const fill = useAnimatedStyle(() => ({ width: `${w.value}%` }));
  const color = tone === 'warn' ? c.warn : tone === 'expense' ? c.expense : c.primary;
  return (
    <View
      accessible={!!accessibilityLabel}
      accessibilityRole="progressbar"
      accessibilityLabel={accessibilityLabel}
      accessibilityValue={{ min: 0, max: 100, now: Math.round(value) }}
      style={{ height, borderRadius: height / 2, backgroundColor: c.track, overflow: 'hidden' }}
    >
      <Animated.View style={[{ height, borderRadius: height / 2, backgroundColor: color }, fill]} />
    </View>
  );
}

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

interface RingProps {
  value: number;
  size?: number;
  stroke?: number;
  children?: ReactNode;
  accessibilityLabel?: string;
}

/** 200 ring, 16 stroke, round cap from 12 o’clock; centre content passed as children. */
export function ProgressRing({ value, size: s = 200, stroke = 16, children, accessibilityLabel }: RingProps) {
  const c = useColors();
  const r = (s - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const duration = useMotionDuration(motion.progress);
  const p = useSharedValue(duration === 0 ? pct : 0);
  useEffect(() => {
    p.value = withTiming(pct, { duration, easing: Easing.out(Easing.cubic) });
  }, [pct, duration, p]);
  const animatedProps = useAnimatedProps<{ strokeDashoffset: number }>(() => ({
    strokeDashoffset: circ * (1 - p.value / 100),
  }));
  return (
    <View
      style={{ width: s, height: s }}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={accessibilityLabel}
      accessibilityValue={{ min: 0, max: 100, now: Math.round(value) }}
    >
      <Svg width={s} height={s} viewBox={`0 0 ${s} ${s}`}>
        <Circle cx={s / 2} cy={s / 2} r={r} fill="none" stroke={c.track} strokeWidth={stroke} />
        <AnimatedCircle
          cx={s / 2}
          cy={s / 2}
          r={r}
          fill="none"
          stroke={c.primary}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circ} ${circ}`}
          transform={`rotate(-90 ${s / 2} ${s / 2})`}
          animatedProps={animatedProps}
        />
      </Svg>
      <View style={[StyleSheet.absoluteFill, styles.center]}>{children}</View>
    </View>
  );
}

// ---------------------------------------------------------------- Section headers

export function SectionHeader({
  title,
  action,
  onAction,
}: {
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <View style={styles.sectionHeader}>
      <Text variant="section" accessibilityRole="header">
        {title}
      </Text>
      {action ? (
        <Text
          variant="small"
          weight="medium"
          color="primary"
          onPress={onAction}
          accessibilityRole="link"
          style={styles.sectionAction}
        >
          {action}
        </Text>
      ) : null}
    </View>
  );
}

export function SectionLabel({ children, right }: { children: string; right?: ReactNode }) {
  return (
    <View style={styles.sectionHeader}>
      <Text variant="label" color="muted" accessibilityRole="header">
        {children}
      </Text>
      {right}
    </View>
  );
}

// ---------------------------------------------------------------- Banner

export type BannerTone = 'primary' | 'warn' | 'error' | 'neutral';

export function Banner({
  icon,
  children,
  tone = 'primary',
}: {
  icon: IconName;
  children: ReactNode;
  tone?: BannerTone;
}) {
  const c = useColors();
  const map: Record<BannerTone, { bg: ColorName; fg: ColorName; text: ColorName }> = {
    primary: { bg: 'primarySoft', fg: 'primary', text: 'ink' },
    warn: { bg: 'warnSoft', fg: 'warnText', text: 'warnInk' },
    error: { bg: 'expenseSoft', fg: 'expense', text: 'ink' },
    neutral: { bg: 'soft', fg: 'muted', text: 'ink' },
  };
  const m = map[tone];
  return (
    <View
      style={[styles.banner, { backgroundColor: c[m.bg] }]}
      accessible
      accessibilityRole={tone === 'error' || tone === 'warn' ? 'alert' : 'text'}
    >
      <View style={styles.bannerIcon}>
        <Icon name={icon} size={iconSize.lg} color={m.fg} strokeWidth={1.9} />
      </View>
      <Text variant="small" color={m.text} style={styles.bannerText}>
        {children}
      </Text>
    </View>
  );
}

// ---------------------------------------------------------------- EmptyState

export function EmptyState({
  icon,
  title,
  body,
  children,
}: {
  icon: IconName;
  title: string;
  body: string;
  children?: ReactNode;
}) {
  const c = useColors();
  return (
    <View style={styles.empty}>
      <View style={[styles.emptyIcon, { backgroundColor: c.primarySoft }]}>
        <Icon name={icon} size={iconSize.empty} color="primary" strokeWidth={1.6} />
      </View>
      <Text variant="sheetTitle" align="center" style={styles.emptyTitle} accessibilityRole="header">
        {title}
      </Text>
      <Text variant="body" color="muted" align="center" style={styles.emptyBody}>
        {body}
      </Text>
      {children ? <View style={styles.emptyActions}>{children}</View> : null}
    </View>
  );
}

// ---------------------------------------------------------------- Skeleton

export function Skeleton({
  width,
  height,
  radius: r = radius.skeleton,
  style,
}: {
  width: number | `${number}%`;
  height: number;
  radius?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const c = useColors();
  const duration = useMotionDuration(600);
  const o = useSharedValue(1);
  useEffect(() => {
    if (duration === 0) return;
    o.value = withRepeat(withSequence(withTiming(0.6, { duration }), withTiming(1, { duration })), -1, false);
  }, [duration, o]);
  const pulse = useAnimatedStyle(() => ({ opacity: o.value }));
  return (
    <Animated.View
      style={[{ width, height, borderRadius: r, backgroundColor: c.skeleton, flexShrink: 0 }, pulse, style]}
    />
  );
}

const styles = StyleSheet.create({
  tile: { alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  row: { flexDirection: 'row' },
  center: { alignItems: 'center', justifyContent: 'center', gap: space[4] },
  dateBadge: {
    width: size.dateBadgeW,
    height: size.dateBadgeH,
    borderRadius: radius.chip,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  badgeDay: { lineHeight: 18 },
  kpi: {
    flex: 1,
    borderWidth: 1,
    borderRadius: radius.kpi,
    paddingVertical: space[14],
    paddingHorizontal: space[16],
    gap: space[4],
  },
  pill: {
    borderRadius: radius.pill,
    paddingVertical: space[4],
    paddingHorizontal: space[10],
    alignSelf: 'flex-start',
    flexShrink: 0,
  },
  pillSmall: { paddingVertical: 2, paddingHorizontal: space[8] },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    gap: space[8],
  },
  sectionAction: { paddingVertical: space[12], marginVertical: -space[12] },
  banner: {
    flexDirection: 'row',
    gap: space[12],
    alignItems: 'flex-start',
    borderRadius: radius.banner,
    paddingVertical: space[14],
    paddingHorizontal: space[16],
  },
  bannerIcon: { paddingTop: 1 },
  bannerText: { flex: 1 },
  empty: { alignItems: 'center', gap: space[12], paddingVertical: space[24], paddingHorizontal: space[12] },
  emptyIcon: {
    width: size.emptyIcon,
    height: size.emptyIcon,
    borderRadius: size.emptyIcon / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyTitle: { paddingTop: space[6] },
  emptyBody: { maxWidth: layout.maxEmptyBody },
  emptyActions: { alignSelf: 'stretch', gap: space[10], paddingTop: space[10] },
});
