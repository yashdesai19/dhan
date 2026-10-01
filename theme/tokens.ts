// Theme-independent design tokens (spec §4). Screens use these, never raw numbers.

/** Spacing scale, keyed by its own value so intent stays readable: space[16]. */
export const space = {
  0: 0,
  2: 2,
  4: 4,
  6: 6,
  8: 8,
  10: 10,
  12: 12,
  14: 14,
  16: 16,
  18: 18,
  20: 20,
  22: 22,
  24: 24,
  28: 28,
  32: 32,
  40: 40,
  44: 44,
  48: 48,
} as const;
export type Space = keyof typeof space;

export const radius = {
  skeleton: 8,
  segment: 10,
  chip: 12,
  tileSm: 12,
  field: 14,
  tile: 14,
  track: 14,
  button: 16,
  banner: 16,
  toast: 16,
  tileLg: 16,
  kpi: 18,
  quick: 18,
  card: 20,
  fab: 20,
  tileXl: 20,
  sheet: 28,
  pill: 999,
} as const;

export const size = {
  touch: 44,
  button: 56,
  buttonMd: 52,
  buttonSm: 48,
  small: 40,
  chip: 40,
  field: 52,
  segment: 40,
  segmentLg: 44,
  key: 56,
  tabBar: 58,
  tabBarBottomPad: 26,
  fab: 58,
  fabLift: 18,
  toggleW: 51,
  toggleH: 31,
  toggleKnob: 27,
  sheetHandleW: 40,
  sheetHandleH: 5,
  iconButton: 44,
  emptyIcon: 72,
  confirmIcon: 60,
  quickAction: 56,
  dateBadgeW: 42,
  dateBadgeH: 46,
} as const;

export const iconSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 22,
  tab: 24,
  fab: 26,
  empty: 30,
  hero: 40,
} as const;

export const avatarSize = {
  xs: 26,
  sm: 30,
  md: 34,
  lg: 36,
  xl: 40,
  xxl: 44,
  hero: 52,
  profile: 56,
  large: 88,
} as const;

export const tileSize = {
  sm: { box: 36, radius: radius.tileSm, icon: iconSize.lg },
  md: { box: 42, radius: radius.tile, icon: iconSize.xl },
  lg: { box: 48, radius: radius.tileLg, icon: iconSize.xxl },
  xl: { box: 60, radius: radius.tileXl, icon: iconSize.fab },
} as const;
export type TileSize = keyof typeof tileSize;

export const layout = {
  gutter: 20,
  gutterAuth: 24,
  sectionGap: 22,
  sectionGapTight: 18,
  labelGap: 10,
  /** Canvas top offsets include a 47 pt status area; apply only the remainder below the safe area. */
  canvasStatusArea: 47,
  topStack: 56,
  topTab: 60,
  topHome: 64,
  bottomScrollPad: 120,
  stickyPad: { top: 16, side: 20, bottom: 34 },
  toastOffsetTabs: 112,
  toastOffsetFooter: 120,
  sheetPad: { top: 10, side: 20, bottom: 34, gap: 18 },
  maxEmptyBody: 290,
  chatUserMax: 280,
  chatAiMax: 300,
} as const;

export const shadow = {
  segment: { offsetY: 1, radius: 2, elevation: 1 },
  fab: { offsetY: 6, radius: 16, elevation: 8 },
  toast: { offsetY: 8, radius: 24, elevation: 10 },
  knob: { offsetY: 1, radius: 3, elevation: 2 },
} as const;

export const motion = {
  fast: 100,
  quick: 150,
  base: 200,
  medium: 250,
  modal: 300,
  numbers: 400,
  chart: 400,
  progress: 500,
  toastHold: 5000,
  typing: 900,
  chartStagger: 30,
  sheetSpring: { damping: 20, stiffness: 180 },
} as const;

export const hitSlop = { top: 4, bottom: 4, left: 4, right: 4 } as const;
