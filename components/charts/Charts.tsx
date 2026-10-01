// The five DHAN charts, drawn with react-native-svg and plain Views (spec §3).
// Each has a one-sentence accessibility summary (spec §18).
import { useEffect, useState } from 'react';
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Polygon, Polyline } from 'react-native-svg';

import { Text } from '@/components/ui/Text';
import { useMotionDuration } from '@/hooks/feedback';
import { motion, space, useColors } from '@/theme';
import type { ChartToken } from '@/types/domain';
import { inr } from '@/utils/format';

// ---------------------------------------------------------------- SegmentedBar

export interface Slice {
  id: string;
  label: string;
  amount: number;
  share: number;
  token: ChartToken;
}

/** 12 pt bar of category segments with 3 gap, legend grid below (Home, Onboarding 2). */
export function SegmentedBar({
  slices,
  legend = 4,
  height = 12,
  legendMode = 'amount',
}: {
  slices: Slice[];
  legend?: number;
  height?: number;
  legendMode?: 'amount' | 'percent';
}) {
  const c = useColors();
  const summary = slices.map((s) => `${s.label} ${inr(s.amount)}`).join(', ');
  return (
    <View style={styles.gap14}>
      <View
        style={[styles.segRow, { height }]}
        accessible
        accessibilityLabel={`Spending by category: ${summary}`}
      >
        {slices.map((s, i) => (
          <View
            key={s.id}
            style={{
              flex: s.share,
              backgroundColor: c[s.token],
              borderTopLeftRadius: i === 0 ? height / 2 : 2,
              borderBottomLeftRadius: i === 0 ? height / 2 : 2,
              borderTopRightRadius: i === slices.length - 1 ? height / 2 : 2,
              borderBottomRightRadius: i === slices.length - 1 ? height / 2 : 2,
            }}
          />
        ))}
      </View>
      {legend > 0 ? (
        <View style={styles.legendGrid}>
          {slices.slice(0, legend).map((s) => (
            <View
              key={s.id}
              style={styles.legendItem}
              accessibilityElementsHidden
              importantForAccessibility="no-hide-descendants"
            >
              <View style={[styles.dot, { backgroundColor: c[s.token] }]} />
              <Text
                variant={legendMode === 'amount' ? 'meta' : 'small'}
                style={styles.grow}
                numberOfLines={1}
              >
                {s.label}
              </Text>
              <Text variant={legendMode === 'amount' ? 'meta' : 'small'} color="muted" tabular>
                {legendMode === 'amount' ? inr(s.amount) : `${Math.round(s.share)}%`}
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------- GroupedBarChart

function GrowBar({
  height,
  color,
  delay,
  width,
}: {
  height: number;
  color: string;
  delay: number;
  width?: number;
}) {
  const duration = useMotionDuration(motion.chart);
  const h = useSharedValue(duration === 0 ? height : 0);
  useEffect(() => {
    h.value = withDelay(
      duration === 0 ? 0 : delay,
      withTiming(height, { duration, easing: Easing.out(Easing.cubic) }),
    );
  }, [height, duration, delay, h]);
  const st = useAnimatedStyle(() => ({ height: h.value }));
  return (
    <Animated.View
      style={[
        width === undefined ? { flex: 1 } : { width },
        {
          backgroundColor: color,
          borderTopLeftRadius: 4,
          borderTopRightRadius: 4,
          borderBottomLeftRadius: 2,
          borderBottomRightRadius: 2,
        },
        st,
      ]}
    />
  );
}

export interface MonthBars {
  label: string;
  income: number;
  spent: number;
}

/** Paired income and spending bars per month, current month highlighted (Reports). */
export function GroupedBarChart({ data, height = 130 }: { data: MonthBars[]; height?: number }) {
  const c = useColors();
  const max = Math.max(1, ...data.map((d) => Math.max(d.income, d.spent))) * 1.05;
  const last = data.length - 1;
  const first = data[0];
  const end = data.at(-1);
  const label =
    first && end
      ? `Income and spending by month. Spending went from ${inr(first.spent)} in ${first.label} to ${inr(end.spent)} in ${end.label}.`
      : '';
  return (
    <View style={styles.gap14} accessible accessibilityLabel={label}>
      <View style={styles.barsRow}>
        {data.map((d, i) => (
          <View key={d.label} style={styles.barCol}>
            <View style={[styles.barPair, { height }]}>
              <GrowBar
                width={12}
                height={(d.income / max) * height}
                color={i === last ? c.primary : c.chart4}
                delay={i * motion.chartStagger}
              />
              <GrowBar
                width={12}
                height={(d.spent / max) * height}
                color={c.chart2}
                delay={i * motion.chartStagger + 15}
              />
            </View>
            <Text
              variant="micro"
              color={i === last ? 'ink' : 'muted'}
              weight={i === last ? 'semibold' : 'regular'}
            >
              {d.label}
            </Text>
          </View>
        ))}
      </View>
      <View style={styles.keyRow}>
        <View style={styles.legendItem}>
          <View style={[styles.keySwatch, { backgroundColor: c.primary }]} />
          <Text variant="caption" color="muted">
            Income
          </Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.keySwatch, { backgroundColor: c.chart2 }]} />
          <Text variant="caption" color="muted">
            Spending
          </Text>
        </View>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- CategoryBars

export interface CategoryBarRow {
  id: string;
  label: string;
  amount: number;
  share: number;
  token: ChartToken;
}

function WidthBar({ pct, color }: { pct: number; color: string }) {
  const c = useColors();
  const duration = useMotionDuration(motion.chart);
  const w = useSharedValue(duration === 0 ? pct : 0);
  useEffect(() => {
    w.value = withTiming(pct, { duration, easing: Easing.out(Easing.cubic) });
  }, [pct, duration, w]);
  const st = useAnimatedStyle(() => ({ width: `${w.value}%` }));
  return (
    <View style={{ height: 8, borderRadius: 4, backgroundColor: c.track, overflow: 'hidden' }}>
      <Animated.View style={[{ height: 8, borderRadius: 4, backgroundColor: color }, st]} />
    </View>
  );
}

/** Horizontal bar per category, scaled to the largest (Reports). */
export function CategoryBars({ rows }: { rows: CategoryBarRow[] }) {
  const c = useColors();
  const top = Math.max(1, ...rows.map((r) => r.amount));
  return (
    <View style={styles.gap14}>
      {rows.map((r) => (
        <View
          key={r.id}
          style={styles.gap6}
          accessible
          accessibilityLabel={`${r.label}, ${inr(r.amount)}, ${Math.round(r.share)} percent`}
        >
          <View style={styles.between}>
            <Text variant="small">{r.label}</Text>
            <Text variant="small" tabular>
              <Text variant="small" weight="semibold" tabular>
                {inr(r.amount)}
              </Text>
              <Text variant="small" color="muted">{` · ${Math.round(r.share)}%`}</Text>
            </Text>
          </View>
          <WidthBar pct={(r.amount / top) * 100} color={c[r.token]} />
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------- DailyBars

/** 30 thin bars; the highlighted day (today) in warning colour (Category budget). */
export function DailyBars({
  values,
  highlight,
  height = 92,
  labels,
}: {
  values: number[];
  highlight: number;
  height?: number;
  labels: [string, string, string];
}) {
  const c = useColors();
  const max = Math.max(1, ...values);
  const spent = values.filter((v) => v > 0).length;
  return (
    <View style={styles.gap8}>
      <View
        style={[styles.dailyRow, { height }]}
        accessible
        accessibilityLabel={`Daily spending: ${spent} days with spending this month`}
      >
        {values.map((v, i) => (
          <GrowBar
            key={i}
            height={Math.max(3, Math.round((v / max) * (height - 2)))}
            color={i === highlight ? c.warn : v ? c.chart3 : c.track}
            delay={i * 8}
          />
        ))}
      </View>
      <View style={styles.between}>
        {labels.map((l) => (
          <Text key={l} variant="micro" color="muted" weight="regular">
            {l}
          </Text>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------- AreaLineChart

/** Line with soft fill and an end dot (Net worth). */
export function AreaLineChart({
  values,
  labels,
  height = 130,
}: {
  values: number[];
  labels: string[];
  height?: number;
}) {
  const c = useColors();
  const [w, setW] = useState(0);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = Math.max(1, hi - lo);
  const pad = 8;
  const pts = values.map((v, i) => {
    const x = pad + (i * (w - pad * 2)) / Math.max(1, values.length - 1);
    const y = pad + (1 - (v - lo) / span) * (height - pad * 2);
    return { x, y };
  });
  const line = pts.map((p) => `${p.x},${p.y}`).join(' ');
  const end = pts.at(-1);
  const first = values[0] ?? 0;
  const lastV = values.at(-1) ?? 0;
  return (
    <View style={styles.gap8}>
      <View
        style={{ height }}
        onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}
        accessible
        accessibilityLabel={`Net worth grew from ${inr(first)} in ${labels[0] ?? ''} to ${inr(lastV)} in ${labels.at(-1) ?? ''}`}
      >
        {w > 0 ? (
          <Svg width={w} height={height}>
            <Polygon points={`${pad},${height} ${line} ${w - pad},${height}`} fill={c.primarySoft} />
            <Polyline
              points={line}
              fill="none"
              stroke={c.primary}
              strokeWidth={2.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {end ? (
              <Circle cx={end.x} cy={end.y} r={5} fill={c.primary} stroke={c.surface} strokeWidth={2} />
            ) : null}
          </Svg>
        ) : null}
      </View>
      <View style={styles.between}>
        {labels.map((l) => (
          <Text key={l} variant="micro" color="muted" weight="regular">
            {l}
          </Text>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  gap14: { gap: space[14] },
  gap8: { gap: space[8] },
  gap6: { gap: space[6] },
  grow: { flex: 1 },
  segRow: { flexDirection: 'row', gap: 3 },
  legendGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: space[10], columnGap: space[16] },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: space[8], width: '46%', flexGrow: 1 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  barsRow: { flexDirection: 'row', gap: space[6], alignItems: 'flex-end' },
  barCol: { flex: 1, alignItems: 'center', gap: space[6] },
  barPair: { flexDirection: 'row', alignItems: 'flex-end', gap: 3 },
  keyRow: { flexDirection: 'row', gap: space[16] },
  keySwatch: { width: 10, height: 10, borderRadius: 3 },
  between: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: space[8] },
  dailyRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 3 },
});
