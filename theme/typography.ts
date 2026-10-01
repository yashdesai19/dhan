// Typography tokens (spec §4). Two families: Instrument Serif for money and headlines, Geist for UI.
// Each weight is its own family name so Android renders the right cut.

export const fontFiles = {
  'Geist-Regular': require('../assets/fonts/Geist-Regular.ttf'),
  'Geist-Medium': require('../assets/fonts/Geist-Medium.ttf'),
  'Geist-SemiBold': require('../assets/fonts/Geist-SemiBold.ttf'),
  'Geist-Bold': require('../assets/fonts/Geist-Bold.ttf'),
  'InstrumentSerif-Regular': require('../assets/fonts/InstrumentSerif-Regular.ttf'),
  'InstrumentSerif-Italic': require('../assets/fonts/InstrumentSerif-Italic.ttf'),
} as const;

export const fonts = {
  regular: 'Geist-Regular',
  medium: 'Geist-Medium',
  semibold: 'Geist-SemiBold',
  bold: 'Geist-Bold',
  serif: 'InstrumentSerif-Regular',
  serifItalic: 'InstrumentSerif-Italic',
} as const;

export type Weight = 'regular' | 'medium' | 'semibold' | 'bold';

export interface TypeStyle {
  fontFamily: string;
  fontSize: number;
  lineHeight?: number;
  letterSpacing?: number;
  textTransform?: 'uppercase' | 'none';
}

export const textVariants = {
  title: { fontFamily: fonts.semibold, fontSize: 26, lineHeight: 32 },
  heading: { fontFamily: fonts.semibold, fontSize: 22, lineHeight: 28 },
  sheetTitle: { fontFamily: fonts.semibold, fontSize: 20, lineHeight: 26 },
  profileName: { fontFamily: fonts.semibold, fontSize: 18, lineHeight: 24 },
  greeting: { fontFamily: fonts.semibold, fontSize: 17, lineHeight: 22 },
  section: { fontFamily: fonts.semibold, fontSize: 16, lineHeight: 22 },
  bodyLg: { fontFamily: fonts.regular, fontSize: 16, lineHeight: 24 },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 21 },
  small: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20 },
  meta: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 18 },
  caption: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 16 },
  label: {
    fontFamily: fonts.semibold,
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  micro: { fontFamily: fonts.medium, fontSize: 11, lineHeight: 14 },
  badgeMonth: { fontFamily: fonts.semibold, fontSize: 10, lineHeight: 12, letterSpacing: 0.6 },
  key: { fontFamily: fonts.medium, fontSize: 24, lineHeight: 30 },
  wordmark: { fontFamily: fonts.bold, fontSize: 30, lineHeight: 36, letterSpacing: 8 },
  displayXl: { fontFamily: fonts.serif, fontSize: 42, lineHeight: 44 },
  display: { fontFamily: fonts.serif, fontSize: 40, lineHeight: 42 },
  displaySm: { fontFamily: fonts.serif, fontSize: 38, lineHeight: 42 },
  tagline: { fontFamily: fonts.serifItalic, fontSize: 26, lineHeight: 32 },
} as const satisfies Record<string, TypeStyle>;
export type TextVariant = keyof typeof textVariants;

export const weightFamily: Record<Weight, string> = {
  regular: fonts.regular,
  medium: fonts.medium,
  semibold: fonts.semibold,
  bold: fonts.bold,
};

/** Serif money sizes used on the canvas. */
export const moneySizes = { xl: 76, lg: 64, hero60: 60, hero: 56, md: 52, sm: 44, xs: 34 } as const;
export type MoneySize = keyof typeof moneySizes;
