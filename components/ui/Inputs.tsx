// TextField, Keypad, AmountDisplay.
import { memo, useEffect, useState, type ReactNode } from 'react';
import { StyleSheet, TextInput, View, type KeyboardTypeOptions, type TextInputProps } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

import { useMotionDuration, haptics } from '@/hooks/feedback';
import { fonts, moneySizes, radius, size, space, textVariants, type ColorName, useColors } from '@/theme';
import { formatAmountInput } from '@/utils/format';
import { Text } from './Text';
import { Touchable } from './Touchable';

// ---------------------------------------------------------------- TextField

export interface TextFieldProps extends Omit<TextInputProps, 'style'> {
  label: string;
  error?: string | null;
  hint?: string;
  trailing?: ReactNode;
  /** Forces the 2 pt focus ring (used by drawn states). */
  focused?: boolean;
  keyboardType?: KeyboardTypeOptions;
}

/** Label above, 52 pt box, radius 14; focus 2 pt primary; error 2 pt expense + message (spec §3). */
export function TextField({
  label,
  error,
  hint,
  trailing,
  focused: forced,
  onFocus,
  onBlur,
  ...input
}: TextFieldProps) {
  const c = useColors();
  const [focused, setFocused] = useState(false);
  const active = forced ?? focused;
  const border = error ? c.expense : active ? c.primary : c.line;
  const bw = error || active ? 2 : 1;
  return (
    <View style={styles.field}>
      <Text variant="meta" weight="medium" color="muted">
        {label}
      </Text>
      <View
        style={[
          styles.box,
          {
            borderColor: border,
            borderWidth: bw,
            backgroundColor: c.surface,
            paddingHorizontal: space[14] - (bw - 1),
          },
        ]}
      >
        <TextInput
          {...input}
          accessibilityLabel={label}
          accessibilityHint={error ?? hint}
          placeholderTextColor={c.faint}
          selectionColor={c.primary}
          cursorColor={c.primary}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          style={[styles.input, { color: c.ink }]}
        />
        {trailing}
      </View>
      {error ? (
        <Text variant="meta" color="expense" accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : hint ? (
        <Text variant="meta" color="muted">
          {hint}
        </Text>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------- Keypad

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', 'del'] as const;
export type KeypadKey = (typeof KEYS)[number];

function KeypadBase({ onKey }: { onKey: (k: KeypadKey) => void }) {
  const c = useColors();
  return (
    <View style={styles.keypad}>
      {KEYS.map((k) => (
        <Touchable
          key={k}
          accessibilityRole="keyboardkey"
          accessibilityLabel={k === 'del' ? 'Delete' : k === '.' ? 'Decimal point' : k}
          onPress={() => {
            haptics.select();
            onKey(k);
          }}
          feedback="none"
          style={styles.key}
          pressedStyle={{ backgroundColor: c.track }}
        >
          <Text variant="key" tabular>
            {k === 'del' ? '⌫' : k}
          </Text>
        </Touchable>
      ))}
    </View>
  );
}

/** 3 × 4 grid, 56 pt keys, 6 gap, 24/500 digits: 1–9 . 0 ⌫ (spec §3). */
export const Keypad = memo(KeypadBase);

// ---------------------------------------------------------------- AmountDisplay

interface AmountDisplayProps {
  value: string;
  tone?: 'default' | 'income';
  size?: 'xl' | 'lg';
  caret?: boolean;
  accessibilityLabel?: string;
}

/** ₹ prefix (serif, faint; income uses +₹ in income colour), serif value, 2 × 56 primary caret. */
export function AmountDisplay({
  value,
  tone = 'default',
  size: sz = 'xl',
  caret = true,
  accessibilityLabel,
}: AmountDisplayProps) {
  const c = useColors();
  const fs = moneySizes[sz];
  const prefixSize = sz === 'xl' ? 40 : 34;
  const color: ColorName = tone === 'income' ? 'income' : 'ink';
  const blink = useSharedValue(1);
  const duration = useMotionDuration(500);
  useEffect(() => {
    if (!caret || duration === 0) return;
    blink.value = withRepeat(
      withSequence(withTiming(0, { duration }), withTiming(1, { duration })),
      -1,
      false,
    );
  }, [caret, duration, blink]);
  const caretStyle = useAnimatedStyle(() => ({ opacity: blink.value }));
  return (
    <View
      style={styles.amountRow}
      accessible
      accessibilityRole="text"
      accessibilityLabel={accessibilityLabel ?? `${tone === 'income' ? 'Plus ' : ''}${value} rupees`}
      accessibilityLiveRegion="polite"
    >
      <Text
        maxScale={1.3}
        style={{
          fontFamily: fonts.serif,
          fontSize: prefixSize,
          lineHeight: prefixSize * 1.1,
          color: tone === 'income' ? c.income : c.faint,
        }}
      >
        {tone === 'income' ? '+₹' : '₹'}
      </Text>
      <Text
        maxScale={1.3}
        numberOfLines={1}
        tabular
        style={{
          fontFamily: fonts.serif,
          fontSize: fs,
          lineHeight: fs * 1.05,
          color: c[color],
          letterSpacing: -0.5,
        }}
      >
        {formatAmountInput(value)}
      </Text>
      {caret ? (
        <Animated.View
          style={[styles.caret, { height: sz === 'xl' ? 56 : 48, backgroundColor: c.primary }, caretStyle]}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: space[8] },
  box: {
    height: size.field,
    borderRadius: radius.field,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[8],
  },
  input: {
    flex: 1,
    fontFamily: fonts.regular,
    fontSize: textVariants.bodyLg.fontSize,
    minHeight: size.touch,
    paddingVertical: 0,
  },
  keypad: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  key: {
    width: '32%',
    flexGrow: 1,
    height: size.key,
    borderRadius: radius.field,
    alignItems: 'center',
    justifyContent: 'center',
  },
  amountRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'center',
    gap: space[4],
    maxWidth: '100%',
  },
  caret: { width: 2, marginLeft: space[4], alignSelf: 'center', borderRadius: 1 },
});
