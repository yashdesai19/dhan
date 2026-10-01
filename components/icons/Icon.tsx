import { memo } from 'react';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { useColors, type ColorName } from '@/theme';
import { iconPaths, type IconName } from './paths';

export type { IconName } from './paths';

export interface IconProps {
  name: IconName;
  size?: number;
  /** A theme token name, or a raw colour already resolved from the theme. */
  color?: ColorName | (string & {});
  strokeWidth?: number;
}

/**
 * The 73 DHAN line icons, drawn exactly as on the canvas: 24-unit grid, no fill, round caps and
 * joins. Icons are decorative; an icon-only button puts its label on the button.
 */
function IconBase({ name, size = 20, color = 'ink', strokeWidth = 1.75 }: IconProps) {
  const colors = useColors();
  const stroke = color in colors ? colors[color as ColorName] : color;
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
    >
      {iconPaths[name].map((el, i) => {
        switch (el.t) {
          case 'path':
            return <Path key={i} d={el.d} />;
          case 'circle':
            return <Circle key={i} cx={el.cx} cy={el.cy} r={el.r} />;
          case 'rect':
            return <Rect key={i} x={el.x} y={el.y} width={el.width} height={el.height} rx={el.rx} />;
        }
      })}
    </Svg>
  );
}

export const Icon = memo(IconBase);
