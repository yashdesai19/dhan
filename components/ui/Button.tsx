import { ActivityIndicator, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { Icon, type IconName } from '@/components/icons/Icon';
import { hitSlop, iconSize, radius, size, space, useColors, type ColorName } from '@/theme';
import { haptics } from '@/hooks/feedback';
import { Text } from './Text';
import { Touchable } from './Touchable';

export type ButtonKind = 'primary' | 'secondary' | 'danger' | 'dashed' | 'ghost';
export type ButtonSize = 'lg' | 'md' | 'sm';

export interface ButtonProps {
  label: string;
  onPress?: () => void;
  kind?: ButtonKind;
  size?: ButtonSize;
  icon?: IconName;
  disabled?: boolean;
  loading?: boolean;
  /** Fill the remaining width in a row. */
  grow?: boolean;
  accessibilityHint?: string;
  style?: StyleProp<ViewStyle>;
  testID?: string;
}

const HEIGHT: Record<ButtonSize, number> = { lg: size.button, md: size.buttonMd, sm: size.buttonSm };

/** 56 / 52 / 48 pt buttons: primary, secondary, danger, dashed, ghost (spec §3). */
export function Button({
  label,
  onPress,
  kind = 'primary',
  size: sz = 'lg',
  icon,
  disabled,
  loading,
  grow,
  style,
  ...rest
}: ButtonProps) {
  const c = useColors();
  const palette: Record<ButtonKind, { bg: string; fg: ColorName; border?: string; dashed?: boolean }> = {
    primary: { bg: c.primary, fg: 'onPrimary' },
    secondary: { bg: c.surface, fg: 'ink', border: c.btnBorder },
    danger: { bg: c.expense, fg: 'onExpense' },
    dashed: { bg: 'transparent', fg: 'primary', border: c.faint, dashed: true },
    ghost: { bg: 'transparent', fg: 'primary' },
  };
  const p = palette[kind];
  const inactive = disabled || loading;
  const bg = inactive && kind === 'primary' ? c.track : p.bg;
  const fg: ColorName = inactive && kind === 'primary' ? 'muted' : p.fg;
  const h = HEIGHT[sz];
  return (
    <Touchable
      {...rest}
      disabled={inactive}
      onPress={() => {
        if (kind === 'primary') haptics.light();
        onPress?.();
      }}
      accessibilityLabel={label}
      accessibilityState={{ busy: !!loading, disabled: !!inactive }}
      style={[
        styles.base,
        {
          height: h,
          borderRadius: sz === 'sm' ? radius.chip : radius.button,
          backgroundColor: bg,
          borderWidth: p.border ? 1 : 0,
          borderColor: p.border,
          borderStyle: p.dashed ? 'dashed' : 'solid',
        },
        grow ? styles.grow : styles.full,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={c[fg]} />
      ) : (
        <>
          {icon ? <Icon name={icon} size={iconSize.lg} color={fg} strokeWidth={2} /> : null}
          <Text variant={sz === 'sm' ? 'small' : 'section'} weight="semibold" color={fg} numberOfLines={1}>
            {label}
          </Text>
        </>
      )}
    </Touchable>
  );
}

export interface SmallButtonProps {
  label: string;
  onPress?: () => void;
  kind?: 'primary' | 'secondary';
  accessibilityHint?: string;
  disabled?: boolean;
}

/** 40 pt row button (Settle up, Remind, Sign out on devices). Hit area reaches 48 via hitSlop. */
export function SmallButton({ label, onPress, kind = 'secondary', ...rest }: SmallButtonProps) {
  const c = useColors();
  const primary = kind === 'primary';
  return (
    <Touchable
      {...rest}
      onPress={onPress}
      hitSlop={hitSlop}
      accessibilityLabel={label}
      style={[
        styles.small,
        primary
          ? { backgroundColor: c.primary }
          : { backgroundColor: c.surface, borderWidth: 1, borderColor: c.btnBorder },
      ]}
    >
      <Text variant="small" weight={primary ? 'semibold' : 'medium'} color={primary ? 'onPrimary' : 'ink'}>
        {label}
      </Text>
    </Touchable>
  );
}

export interface TextButtonProps {
  label: string;
  onPress?: () => void;
  color?: ColorName;
  size?: 'md' | 'sm';
  disabled?: boolean;
  accessibilityHint?: string;
}

/** Text-only action with a 44 pt hit area and no visible box. */
export function TextButton({
  label,
  onPress,
  color = 'primary',
  size: sz = 'md',
  disabled,
  ...rest
}: TextButtonProps) {
  return (
    <Touchable
      {...rest}
      disabled={disabled}
      onPress={onPress}
      accessibilityLabel={label}
      feedback="opacity"
      style={styles.textBtn}
    >
      <Text variant={sz === 'md' ? 'body' : 'small'} weight="semibold" color={disabled ? 'faint' : color}>
        {label}
      </Text>
    </Touchable>
  );
}

export interface IconButtonProps {
  icon: IconName;
  accessibilityLabel: string;
  onPress?: () => void;
  /** Filled surface circle (default) or bare icon (month arrows, voice input). */
  variant?: 'circle' | 'bare';
  iconColor?: ColorName;
  badge?: boolean;
}

/** 44 pt circle with an 18 pt icon at stroke 2; always labelled (spec §18). */
export function IconButton({
  icon,
  accessibilityLabel,
  onPress,
  variant = 'circle',
  iconColor,
  badge,
}: IconButtonProps) {
  const c = useColors();
  return (
    <Touchable
      onPress={onPress}
      accessibilityLabel={accessibilityLabel}
      style={[
        styles.iconBtn,
        variant === 'circle' ? { backgroundColor: c.surface, borderWidth: 1, borderColor: c.line } : null,
      ]}
    >
      <Icon
        name={icon}
        size={variant === 'circle' ? iconSize.lg : iconSize.lg}
        color={iconColor ?? (variant === 'bare' ? 'muted' : 'ink')}
        strokeWidth={2}
      />
      {badge ? <View style={[styles.badge, { backgroundColor: c.primary, borderColor: c.surface }]} /> : null}
    </Touchable>
  );
}

const styles = StyleSheet.create({
  base: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space[8],
    paddingHorizontal: space[16],
  },
  full: { alignSelf: 'stretch' },
  grow: { flexGrow: 1, flexBasis: 0 },
  small: {
    height: size.small,
    paddingHorizontal: space[16],
    borderRadius: radius.chip,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  textBtn: {
    minHeight: size.touch,
    minWidth: size.touch,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: space[4],
  },
  iconBtn: {
    width: size.iconButton,
    height: size.iconButton,
    borderRadius: size.iconButton / 2,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  badge: { position: 'absolute', top: 9, right: 10, width: 9, height: 9, borderRadius: 5, borderWidth: 2 },
});
