import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import { usePrefsStore } from '@/store/prefs';
import { dark, light, type ColorTokens } from './colors';

export type Scheme = 'light' | 'dark';

export interface Theme {
  scheme: Scheme;
  colors: ColorTokens;
}

const ThemeContext = createContext<Theme>({ scheme: 'light', colors: light });

/** Follows the system unless Settings forces Light or Dark (spec §5). */
export function ThemeProvider({ children, forceScheme }: { children: ReactNode; forceScheme?: Scheme }) {
  const system = useColorScheme();
  const preference = usePrefsStore((s) => s.theme);
  const scheme: Scheme =
    forceScheme ?? (preference === 'system' ? (system === 'dark' ? 'dark' : 'light') : preference);
  const value = useMemo<Theme>(() => ({ scheme, colors: scheme === 'dark' ? dark : light }), [scheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  return useContext(ThemeContext);
}

export function useColors(): ColorTokens {
  return useContext(ThemeContext).colors;
}
