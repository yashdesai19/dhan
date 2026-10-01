import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { useColors } from '@/theme';

export type LogoVariant = 'app' | 'splash' | 'onSurface';

interface LogoProps {
  size?: number;
  /** app: primary tile, bg-coloured D. splash: splash tile colours. */
  variant?: LogoVariant;
  /** Corner radius on the 64-unit grid (16 on screens, 18 on splash). */
  radius?: number;
  accessibilityLabel?: string;
}

/** The DHAN mark: rounded tile, D stroke, gold coin (Brand board). */
export function Logo({ size = 56, variant = 'app', radius, accessibilityLabel = 'DHAN' }: LogoProps) {
  const c = useColors();
  const tile = variant === 'splash' ? c.splashTile : c.primary;
  const mark = variant === 'splash' ? c.splashMark : c.onPrimary === '#FFFFFF' ? c.bg : c.onPrimary;
  const rx = radius ?? (variant === 'splash' ? 18 : 16);
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      accessibilityRole="image"
      accessibilityLabel={accessibilityLabel}
    >
      <Rect width={64} height={64} rx={rx} fill={tile} />
      <Path
        d="M22 17V47H31A15 15 0 0 0 31 17Z"
        fill="none"
        stroke={mark}
        strokeWidth={5}
        strokeLinejoin="round"
      />
      <Circle cx={31} cy={32} r={4.5} fill={c.gold} />
    </Svg>
  );
}
