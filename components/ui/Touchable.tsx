import type { ReactNode } from 'react';
import {
  Pressable,
  type AccessibilityRole,
  type AccessibilityState,
  type Insets,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { useColors } from '@/theme';

export interface TouchableProps {
  onPress?: () => void;
  onLongPress?: () => void;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  children?: ReactNode;
  accessibilityLabel?: string;
  accessibilityHint?: string;
  accessibilityRole?: AccessibilityRole;
  accessibilityState?: AccessibilityState;
  hitSlop?: Insets | number;
  /** Ripple clipped to the shape (Android) and 0.85 opacity on press (iOS). */
  feedback?: 'opacity' | 'none';
  /** Extra style while pressed (keypad keys highlight instead of fading). */
  pressedStyle?: StyleProp<ViewStyle>;
  testID?: string;
}

/** Base pressable for every tappable element: consistent press feedback on both platforms. */
export function Touchable({
  feedback = 'opacity',
  style,
  pressedStyle,
  children,
  disabled,
  accessibilityRole = 'button',
  ...rest
}: TouchableProps) {
  const c = useColors();
  return (
    <Pressable
      {...rest}
      disabled={disabled}
      accessibilityRole={accessibilityRole}
      accessibilityState={{ disabled: !!disabled, ...rest.accessibilityState }}
      android_ripple={
        feedback === 'none' ? undefined : { color: `${c.primary}1F`, borderless: false, foreground: true }
      }
      style={({ pressed }) => [
        style,
        pressed && feedback === 'opacity' ? { opacity: 0.85 } : null,
        pressed ? pressedStyle : null,
      ]}
    >
      {children}
    </Pressable>
  );
}
