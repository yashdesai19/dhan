import { memo, type ReactNode } from 'react';
import {
  Text as RNText,
  StyleSheet,
  type AccessibilityProps,
  type StyleProp,
  type TextStyle,
} from 'react-native';

import {
  moneySizes,
  textVariants,
  useColors,
  weightFamily,
  type ColorName,
  type MoneySize,
  type TextVariant,
  type Weight,
} from '@/theme';
import { fonts } from '@/theme/typography';
import { inr, type Sign } from '@/utils/format';

export interface TextProps extends AccessibilityProps {
  variant?: TextVariant;
  weight?: Weight;
  color?: ColorName;
  tabular?: boolean;
  align?: 'left' | 'center' | 'right';
  numberOfLines?: number;
  /** Caps Dynamic Type growth (spec §16). */
  maxScale?: number;
  style?: StyleProp<TextStyle>;
  children?: ReactNode;
  testID?: string;
  onPress?: () => void;
}

function TextBase({
  variant = 'body',
  weight,
  color = 'ink',
  tabular,
  align,
  numberOfLines,
  maxScale = 1.8,
  style,
  children,
  ...rest
}: TextProps) {
  const c = useColors();
  const v = textVariants[variant];
  return (
    <RNText
      {...rest}
      numberOfLines={numberOfLines}
      maxFontSizeMultiplier={maxScale}
      style={[
        v,
        weight ? { fontFamily: weightFamily[weight] } : null,
        { color: c[color] },
        tabular ? styles.tabular : null,
        align ? { textAlign: align } : null,
        style,
      ]}
    >
      {children}
    </RNText>
  );
}

export const Text = memo(TextBase);

export interface MoneyProps extends AccessibilityProps {
  amount: number;
  size?: MoneySize;
  sign?: Sign;
  color?: ColorName;
  style?: StyleProp<TextStyle>;
  numberOfLines?: number;
}

/** Instrument Serif money: line height 1, −0.5 tracking, tabular figures (spec §4). */
function MoneyBase({ amount, size = 'hero', sign = 'auto', color = 'ink', style, ...rest }: MoneyProps) {
  const c = useColors();
  const fs = moneySizes[size];
  return (
    <RNText
      accessibilityLabel={rest.accessibilityLabel}
      maxFontSizeMultiplier={1.3}
      adjustsFontSizeToFit
      numberOfLines={rest.numberOfLines ?? 1}
      style={[styles.money, { fontSize: fs, lineHeight: fs * 1.08, color: c[color] }, style]}
    >
      {inr(amount, sign)}
    </RNText>
  );
}

export const Money = memo(MoneyBase);

const styles = StyleSheet.create({
  tabular: { fontVariant: ['tabular-nums'] },
  money: {
    fontFamily: fonts.serif,
    letterSpacing: -0.5,
    fontVariant: ['tabular-nums'],
    includeFontPadding: false,
  },
});
