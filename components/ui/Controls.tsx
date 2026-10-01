// Selection controls: Chip, ChipGroup, SegmentedControl, Toggle, Checkbox, Stepper.
import { useEffect, type ReactNode } from 'react';
import { ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { Icon } from '@/components/icons/Icon';
import { useMotionDuration, haptics } from '@/hooks/feedback';
import { hitSlop, iconSize, layout, motion, radius, size, space, useColors, useTheme } from '@/theme';
import { light } from '@/theme/colors';
import { Text } from './Text';
import { Touchable } from './Touchable';

// ---------------------------------------------------------------- Chip

export interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  dashed?: boolean;
  accessibilityHint?: string;
}

/** 40 pt, radius 12, 14/500. Selected = chipOn fill (spec §3). */
export function Chip({ label, selected, onPress, dashed }: ChipProps) {
  const c = useColors();
  return (
    <Touchable
      onPress={() => {
        haptics.select();
        onPress?.();
      }}
      hitSlop={hitSlop}
      accessibilityLabel={label}
      accessibilityState={{ selected: !!selected }}
      style={[
        styles.chip,
        dashed
          ? { borderColor: c.faint, borderStyle: 'dashed', backgroundColor: 'transparent' }
          : selected
            ? { backgroundColor: c.chipOnBg, borderColor: c.chipOnBg }
            : { backgroundColor: c.surface, borderColor: c.line },
      ]}
    >
      <Text
        variant="small"
        weight="medium"
        color={dashed ? 'primary' : selected ? 'chipOnText' : 'ink'}
        numberOfLines={1}
      >
        {label}
      </Text>
    </Touchable>
  );
}

export interface ChipOption<T extends string> {
  value: T;
  label: string;
}

interface ChipGroupProps<T extends string> {
  options: readonly ChipOption<T>[];
  selected: readonly T[];
  onChange: (next: T[]) => void;
  multi?: boolean;
  /** Wrap onto lines (Filters) or scroll horizontally edge to edge (Add expense). */
  wrap?: boolean;
  trailing?: { label: string; onPress: () => void };
  bleed?: number;
}

export function ChipGroup<T extends string>({
  options,
  selected,
  onChange,
  multi,
  wrap = true,
  trailing,
  bleed = layout.gutter,
}: ChipGroupProps<T>) {
  const toggle = (v: T) => {
    if (multi) onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);
    else onChange([v]);
  };
  const chips = (
    <>
      {options.map((o) => (
        <Chip
          key={o.value}
          label={o.label}
          selected={selected.includes(o.value)}
          onPress={() => toggle(o.value)}
        />
      ))}
      {trailing ? <Chip label={trailing.label} dashed onPress={trailing.onPress} /> : null}
    </>
  );
  if (wrap)
    return (
      <View style={styles.wrap} accessibilityRole={multi ? undefined : 'radiogroup'}>
        {chips}
      </View>
    );
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      style={{ marginHorizontal: -bleed }}
      contentContainerStyle={[styles.row, { paddingHorizontal: bleed }]}
      keyboardShouldPersistTaps="handled"
    >
      {chips}
    </ScrollView>
  );
}

// ---------------------------------------------------------------- SegmentedControl

interface SegmentedProps<T extends string> {
  options: readonly ChipOption<T>[];
  value: T;
  onChange: (v: T) => void;
  large?: boolean;
  compact?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}

/** Track fill, radius 14, 4 pt padding; active segment = surface + small shadow. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  large,
  compact,
  style,
  accessibilityLabel,
}: SegmentedProps<T>) {
  const { colors: c, scheme } = useTheme();
  return (
    <View
      accessibilityRole="tablist"
      accessibilityLabel={accessibilityLabel}
      style={[
        styles.segTrack,
        { backgroundColor: c.track, height: large ? size.segmentLg : size.segment },
        style,
      ]}
    >
      {options.map((o) => {
        const on = o.value === value;
        return (
          <Touchable
            key={o.value}
            feedback="none"
            accessibilityRole="tab"
            accessibilityLabel={o.label}
            accessibilityState={{ selected: on }}
            onPress={() => {
              if (!on) haptics.select();
              onChange(o.value);
            }}
            style={[
              styles.seg,
              on
                ? {
                    backgroundColor: c.surface,
                    shadowColor: c.shadowBase,
                    shadowOpacity: scheme === 'dark' ? 0.4 : 0.08,
                    shadowRadius: 2,
                    shadowOffset: { width: 0, height: 1 },
                    elevation: 1,
                  }
                : null,
            ]}
          >
            <Text
              variant={compact ? 'caption' : 'small'}
              weight="semibold"
              color={on ? 'ink' : 'muted'}
              numberOfLines={1}
            >
              {o.label}
            </Text>
          </Touchable>
        );
      })}
    </View>
  );
}

// ---------------------------------------------------------------- Toggle

interface ToggleProps {
  value: boolean;
  onChange: (v: boolean) => void;
  accessibilityLabel: string;
}

/** 51 × 31 switch, 27 knob, 44 pt hit height. */
export function Toggle({ value, onChange, accessibilityLabel }: ToggleProps) {
  const c = useColors();
  const duration = useMotionDuration(motion.base);
  const x = useSharedValue(value ? 22 : 2);
  useEffect(() => {
    x.value = withTiming(value ? 22 : 2, { duration });
  }, [value, duration, x]);
  const knobStyle = useAnimatedStyle(() => ({ transform: [{ translateX: x.value }] }));
  const knob = value ? c.knobOn : c.knobOff;
  return (
    <Touchable
      feedback="none"
      accessibilityRole="switch"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{ checked: value }}
      onPress={() => {
        haptics.select();
        onChange(!value);
      }}
      style={styles.toggleHit}
    >
      <View style={[styles.toggleTrack, { backgroundColor: value ? c.primary : c.btnBorder }]}>
        <Animated.View style={[styles.knob, { backgroundColor: knob }, knobStyle]} />
      </View>
    </Touchable>
  );
}

// ---------------------------------------------------------------- Checkbox

interface CheckboxProps {
  checked: boolean;
  onChange?: (v: boolean) => void;
  size?: number;
  radius?: number;
}

export function CheckboxBox({ checked, size: s = 24, radius: r = 8 }: CheckboxProps) {
  const c = useColors();
  return (
    <View
      style={[
        styles.box,
        {
          width: s,
          height: s,
          borderRadius: r,
          borderColor: checked ? c.primary : c.line,
          backgroundColor: checked ? c.primary : 'transparent',
        },
      ]}
    >
      {checked ? <Icon name="check" size={iconSize.sm} color="onPrimary" strokeWidth={3} /> : null}
    </View>
  );
}

// ---------------------------------------------------------------- Stepper

interface StepperProps {
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
  label: string;
  /** 40 circles (split shares) or 52 circles (Edit budget). */
  large?: boolean;
  renderValue?: (v: number) => ReactNode;
}

export function Stepper({ value, onChange, step = 1, min = 0, label, large, renderValue }: StepperProps) {
  const c = useColors();
  const d = large ? 52 : 40;
  const btn = [
    styles.stepBtn,
    { width: d, height: d, borderRadius: d / 2, backgroundColor: c.surface, borderColor: c.line },
  ];
  return (
    <View
      style={[styles.stepper, large ? styles.stepperLarge : null]}
      accessibilityRole="adjustable"
      accessibilityLabel={label}
      accessibilityValue={{ now: value }}
    >
      <Touchable
        hitSlop={hitSlop}
        accessibilityLabel={`Decrease ${label}`}
        onPress={() => onChange(Math.max(min, value - step))}
        style={btn}
      >
        <Icon name="minus" size={large ? iconSize.xxl : iconSize.md} strokeWidth={2} />
      </Touchable>
      {renderValue ? (
        renderValue(value)
      ) : (
        <Text variant="section" tabular style={styles.stepValue}>
          {value}
        </Text>
      )}
      <Touchable
        hitSlop={hitSlop}
        accessibilityLabel={`Increase ${label}`}
        onPress={() => onChange(value + step)}
        style={btn}
      >
        <Icon name="plus" size={large ? iconSize.xxl : iconSize.md} strokeWidth={2} />
      </Touchable>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    height: size.chip,
    paddingHorizontal: space[14],
    borderRadius: radius.chip,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    flexShrink: 0,
  },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space[8] },
  row: { flexDirection: 'row', gap: space[8] },
  segTrack: { flexDirection: 'row', borderRadius: radius.track, padding: space[4] },
  seg: {
    flex: 1,
    borderRadius: radius.segment,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: space[2],
  },
  toggleHit: { width: size.toggleW, height: size.touch, justifyContent: 'center', flexShrink: 0 },
  toggleTrack: { width: size.toggleW, height: size.toggleH, borderRadius: 16, justifyContent: 'center' },
  knob: {
    width: size.toggleKnob,
    height: size.toggleKnob,
    borderRadius: 14,
    shadowColor: light.shadowBase,
    shadowOpacity: 0.2,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  box: { borderWidth: 2, alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: space[10] },
  stepperLarge: { justifyContent: 'space-between', alignSelf: 'stretch', paddingVertical: space[6] },
  stepBtn: { borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  stepValue: { minWidth: 20, textAlign: 'center' },
});
