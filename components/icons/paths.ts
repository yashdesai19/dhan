// Ported 1:1 from the approved DHAN canvas (24-unit grid, stroke icons).
// Do not edit by hand: add icons here only if they exist on the canvas.

export type IconElement =
  | { t: 'path'; d: string }
  | { t: 'circle'; cx: number; cy: number; r: number }
  | { t: 'rect'; x: number; y: number; width: number; height: number; rx?: number };

export const iconPaths = {
  home: [{ t: 'path', d: 'M4 11l8-7 8 7v9h-5v-6H9v6H4z' }],
  list: [
    { t: 'path', d: 'M9 6h11' },
    { t: 'path', d: 'M9 12h11' },
    { t: 'path', d: 'M9 18h11' },
    { t: 'path', d: 'M4.5 6h.01' },
    { t: 'path', d: 'M4.5 12h.01' },
    { t: 'path', d: 'M4.5 18h.01' },
  ],
  plus: [
    { t: 'path', d: 'M12 5v14' },
    { t: 'path', d: 'M5 12h14' },
  ],
  pie: [
    { t: 'circle', cx: 12, cy: 12, r: 8 },
    { t: 'path', d: 'M12 4v8l6 5' },
  ],
  grid: [
    { t: 'rect', x: 4, y: 4, width: 6.5, height: 6.5, rx: 2 },
    { t: 'rect', x: 13.5, y: 4, width: 6.5, height: 6.5, rx: 2 },
    { t: 'rect', x: 4, y: 13.5, width: 6.5, height: 6.5, rx: 2 },
    { t: 'rect', x: 13.5, y: 13.5, width: 6.5, height: 6.5, rx: 2 },
  ],
  chevL: [{ t: 'path', d: 'M15 6l-6 6 6 6' }],
  chevR: [{ t: 'path', d: 'M9 6l6 6-6 6' }],
  chevD: [{ t: 'path', d: 'M6 9l6 6 6-6' }],
  close: [
    { t: 'path', d: 'M6 6l12 12' },
    { t: 'path', d: 'M18 6L6 18' },
  ],
  search: [
    { t: 'circle', cx: 11, cy: 11, r: 6.5 },
    { t: 'path', d: 'M16 16l4 4' },
  ],
  filter: [
    { t: 'path', d: 'M4 7h10' },
    { t: 'path', d: 'M18 7h2' },
    { t: 'circle', cx: 16, cy: 7, r: 2 },
    { t: 'path', d: 'M4 17h4' },
    { t: 'path', d: 'M12 17h8' },
    { t: 'circle', cx: 10, cy: 17, r: 2 },
  ],
  bell: [
    { t: 'path', d: 'M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z' },
    { t: 'path', d: 'M10 20.5a2 2 0 0 0 4 0' },
  ],
  sparkle: [
    { t: 'path', d: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z' },
    { t: 'path', d: 'M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z' },
  ],
  food: [
    { t: 'path', d: 'M4 11h16a8 8 0 0 1-16 0z' },
    { t: 'path', d: 'M9 7.5c0-1 1-1.5 1-2.5' },
    { t: 'path', d: 'M13.5 7.5c0-1 1-1.5 1-2.5' },
  ],
  car: [
    { t: 'path', d: 'M5 16v-5l2-5h10l2 5v5' },
    { t: 'path', d: 'M3 16h18v3H3z' },
    { t: 'path', d: 'M7 12h.01' },
    { t: 'path', d: 'M17 12h.01' },
  ],
  bag: [
    { t: 'path', d: 'M5 8h14l-1 12H6z' },
    { t: 'path', d: 'M9 8a3 3 0 0 1 6 0' },
  ],
  bolt: [{ t: 'path', d: 'M13 3L5 14h6l-1 7 8-11h-6z' }],
  income: [
    { t: 'path', d: 'M12 4v11' },
    { t: 'path', d: 'M7 10l5 5 5-5' },
    { t: 'path', d: 'M5 20h14' },
  ],
  briefcase: [
    { t: 'rect', x: 3, y: 7, width: 18, height: 13, rx: 2 },
    { t: 'path', d: 'M9 7V5h6v2' },
  ],
  up: [
    { t: 'path', d: 'M12 19V5' },
    { t: 'path', d: 'M6 11l6-6 6 6' },
  ],
  down: [
    { t: 'path', d: 'M12 5v14' },
    { t: 'path', d: 'M6 13l6 6 6-6' },
  ],
  gift: [
    { t: 'rect', x: 4, y: 10, width: 16, height: 10, rx: 1 },
    { t: 'path', d: 'M3 7h18v3H3z' },
    { t: 'path', d: 'M12 7v13' },
    { t: 'path', d: 'M12 7c-1.5-3-5-3.5-5-1.2C7 7 10 7 12 7c2 0 5 0 5-1.2 0-2.3-3.5-1.8-5 1.2z' },
  ],
  percent: [
    { t: 'path', d: 'M19 5L5 19' },
    { t: 'circle', cx: 7, cy: 7, r: 2 },
    { t: 'circle', cx: 17, cy: 17, r: 2 },
  ],
  transfer: [
    { t: 'path', d: 'M4 8h15l-3-3' },
    { t: 'path', d: 'M20 16H5l3 3' },
  ],
  users: [
    { t: 'circle', cx: 9, cy: 8, r: 3 },
    { t: 'path', d: 'M3 20a6 6 0 0 1 12 0' },
    { t: 'circle', cx: 17, cy: 9, r: 2.5 },
    { t: 'path', d: 'M16 14.2a5 5 0 0 1 5 5.3' },
  ],
  bank: [
    { t: 'path', d: 'M3 10l9-6 9 6' },
    { t: 'path', d: 'M5 10v8' },
    { t: 'path', d: 'M9.5 10v8' },
    { t: 'path', d: 'M14.5 10v8' },
    { t: 'path', d: 'M19 10v8' },
    { t: 'path', d: 'M3 20h18' },
  ],
  wallet: [
    { t: 'rect', x: 3, y: 6, width: 18, height: 14, rx: 3 },
    { t: 'path', d: 'M3 10h18' },
    { t: 'path', d: 'M15.5 15h2' },
  ],
  card: [
    { t: 'rect', x: 3, y: 6, width: 18, height: 13, rx: 2 },
    { t: 'path', d: 'M3 10h18' },
    { t: 'path', d: 'M7 15h3' },
  ],
  cash: [
    { t: 'rect', x: 3, y: 7, width: 18, height: 11, rx: 2 },
    { t: 'circle', cx: 12, cy: 12.5, r: 2.5 },
    { t: 'path', d: 'M6.5 10h.01' },
    { t: 'path', d: 'M17.5 15h.01' },
  ],
  coin: [
    { t: 'circle', cx: 12, cy: 12, r: 8 },
    { t: 'path', d: 'M9.5 9h5' },
    { t: 'path', d: 'M9.5 12h5' },
    { t: 'path', d: 'M9.5 9h1.5a2.5 2.5 0 0 1 0 5H9.5l4 3' },
  ],
  target: [
    { t: 'circle', cx: 12, cy: 12, r: 8 },
    { t: 'circle', cx: 12, cy: 12, r: 4 },
    { t: 'path', d: 'M12 12h.01' },
  ],
  repeat: [
    { t: 'path', d: 'M17 3l3 3-3 3' },
    { t: 'path', d: 'M4 12v-2a4 4 0 0 1 4-4h12' },
    { t: 'path', d: 'M7 21l-3-3 3-3' },
    { t: 'path', d: 'M20 12v2a4 4 0 0 1-4 4H4' },
  ],
  calendar: [
    { t: 'rect', x: 4, y: 5, width: 16, height: 15, rx: 2 },
    { t: 'path', d: 'M4 10h16' },
    { t: 'path', d: 'M9 3v4' },
    { t: 'path', d: 'M15 3v4' },
  ],
  receipt: [
    { t: 'path', d: 'M6 3h12v18l-3-2-3 2-3-2-3 2z' },
    { t: 'path', d: 'M9 8h6' },
    { t: 'path', d: 'M9 12h6' },
  ],
  note: [
    { t: 'path', d: 'M5 4h14v16H5z' },
    { t: 'path', d: 'M8 9h8' },
    { t: 'path', d: 'M8 13h8' },
    { t: 'path', d: 'M8 17h5' },
  ],
  trash: [
    { t: 'path', d: 'M4 7h16' },
    { t: 'path', d: 'M9 7V4h6v3' },
    { t: 'path', d: 'M6 7l1 13h10l1-13' },
  ],
  edit: [
    { t: 'path', d: 'M4 20h4L19 9l-4-4L4 16z' },
    { t: 'path', d: 'M13 7l4 4' },
  ],
  check: [{ t: 'path', d: 'M5 12.5l4.5 4.5L19 7' }],
  lock: [
    { t: 'rect', x: 5, y: 11, width: 14, height: 10, rx: 2 },
    { t: 'path', d: 'M8 11V8a4 4 0 0 1 8 0v3' },
  ],
  faceid: [
    { t: 'path', d: 'M4 8V6a2 2 0 0 1 2-2h2' },
    { t: 'path', d: 'M16 4h2a2 2 0 0 1 2 2v2' },
    { t: 'path', d: 'M20 16v2a2 2 0 0 1-2 2h-2' },
    { t: 'path', d: 'M8 20H6a2 2 0 0 1-2-2v-2' },
    { t: 'path', d: 'M9 9.5v1' },
    { t: 'path', d: 'M15 9.5v1' },
    { t: 'path', d: 'M12 9.5v4h-1' },
    { t: 'path', d: 'M9 16c2 1.5 4 1.5 6 0' },
  ],
  shield: [
    { t: 'path', d: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z' },
    { t: 'path', d: 'M9 12l2 2 4-4' },
  ],
  moon: [{ t: 'path', d: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z' }],
  rupee: [
    { t: 'path', d: 'M7 5h10' },
    { t: 'path', d: 'M7 9h10' },
    { t: 'path', d: 'M7 5h3.5a4 4 0 0 1 0 8H7l7 7' },
  ],
  download: [
    { t: 'path', d: 'M12 4v11' },
    { t: 'path', d: 'M7 10l5 5 5-5' },
    { t: 'path', d: 'M5 20h14' },
  ],
  help: [
    { t: 'circle', cx: 12, cy: 12, r: 9 },
    { t: 'path', d: 'M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 1-1 1.7' },
    { t: 'path', d: 'M12 17h.01' },
  ],
  doc: [
    { t: 'path', d: 'M6 3h8l4 4v14H6z' },
    { t: 'path', d: 'M14 3v4h4' },
  ],
  logout: [
    { t: 'path', d: 'M10 5H5v14h5' },
    { t: 'path', d: 'M14 8l4 4-4 4' },
    { t: 'path', d: 'M18 12H9' },
  ],
  user: [
    { t: 'circle', cx: 12, cy: 8, r: 4 },
    { t: 'path', d: 'M4 20a8 8 0 0 1 16 0' },
  ],
  chart: [
    { t: 'path', d: 'M4 20h16' },
    { t: 'path', d: 'M7 16v-5' },
    { t: 'path', d: 'M12 16V7' },
    { t: 'path', d: 'M17 16v-8' },
  ],
  trend: [
    { t: 'path', d: 'M3 17l6-6 4 4 8-8' },
    { t: 'path', d: 'M15 7h6v6' },
  ],
  send: [{ t: 'path', d: 'M4 12l16-8-6 16-3-7z' }],
  mic: [
    { t: 'rect', x: 9, y: 3, width: 6, height: 11, rx: 3 },
    { t: 'path', d: 'M5 11a7 7 0 0 0 14 0' },
    { t: 'path', d: 'M12 18v3' },
  ],
  alert: [
    { t: 'path', d: 'M12 4l9 16H3z' },
    { t: 'path', d: 'M12 10v4' },
    { t: 'path', d: 'M12 17h.01' },
  ],
  info: [
    { t: 'circle', cx: 12, cy: 12, r: 9 },
    { t: 'path', d: 'M12 11v5' },
    { t: 'path', d: 'M12 8h.01' },
  ],
  wifioff: [
    { t: 'path', d: 'M3 3l18 18' },
    { t: 'path', d: 'M8.5 16.5a5 5 0 0 1 7 0' },
    { t: 'path', d: 'M5 12.5a10 10 0 0 1 4.5-2.6' },
    { t: 'path', d: 'M19 12.5a10 10 0 0 0-2.4-1.7' },
    { t: 'path', d: 'M12 20h.01' },
  ],
  camera: [
    { t: 'path', d: 'M4 8h3l2-3h6l2 3h3v11H4z' },
    { t: 'circle', cx: 12, cy: 13, r: 3.5 },
  ],
  heart: [{ t: 'path', d: 'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z' }],
  film: [
    { t: 'rect', x: 3, y: 5, width: 18, height: 14, rx: 2 },
    { t: 'path', d: 'M10 9l5 3-5 3z' },
  ],
  dumbbell: [
    { t: 'path', d: 'M6 8v8' },
    { t: 'path', d: 'M3 10v4' },
    { t: 'path', d: 'M18 8v8' },
    { t: 'path', d: 'M21 10v4' },
    { t: 'path', d: 'M6 12h12' },
  ],
  wifi: [
    { t: 'path', d: 'M2 9a14 14 0 0 1 20 0' },
    { t: 'path', d: 'M5 12.5a10 10 0 0 1 14 0' },
    { t: 'path', d: 'M8.5 16a5 5 0 0 1 7 0' },
    { t: 'path', d: 'M12 20h.01' },
  ],
  eye: [
    { t: 'path', d: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z' },
    { t: 'circle', cx: 12, cy: 12, r: 3 },
  ],
  mail: [
    { t: 'rect', x: 3, y: 5, width: 18, height: 14, rx: 2 },
    { t: 'path', d: 'M3 7l9 6 9-6' },
  ],
  dots: [
    { t: 'path', d: 'M5 12h.01' },
    { t: 'path', d: 'M12 12h.01' },
    { t: 'path', d: 'M19 12h.01' },
  ],
  tag: [
    { t: 'path', d: 'M3 12V4h8l9 9-8 8z' },
    { t: 'path', d: 'M7.5 7.5h.01' },
  ],
  archive: [
    { t: 'rect', x: 3, y: 4, width: 18, height: 5, rx: 1 },
    { t: 'path', d: 'M5 9v11h14V9' },
    { t: 'path', d: 'M10 13h4' },
  ],
  phone: [
    { t: 'rect', x: 7, y: 3, width: 10, height: 18, rx: 2 },
    { t: 'path', d: 'M11 18h2' },
  ],
  laptop: [
    { t: 'rect', x: 5, y: 5, width: 14, height: 10, rx: 1 },
    { t: 'path', d: 'M3 19h18' },
  ],
  swap: [
    { t: 'path', d: 'M8 4v16' },
    { t: 'path', d: 'M4 16l4 4 4-4' },
    { t: 'path', d: 'M16 20V4' },
    { t: 'path', d: 'M12 8l4-4 4 4' },
  ],
  minus: [{ t: 'path', d: 'M5 12h14' }],
  key: [
    { t: 'circle', cx: 8, cy: 15, r: 4 },
    { t: 'path', d: 'M11 12l9-9' },
    { t: 'path', d: 'M16 7l3 3' },
  ],
  globe: [
    { t: 'circle', cx: 12, cy: 12, r: 9 },
    { t: 'path', d: 'M3 12h18' },
    { t: 'path', d: 'M12 3a14 14 0 0 1 0 18' },
    { t: 'path', d: 'M12 3a14 14 0 0 0 0 18' },
  ],
  sun: [
    { t: 'circle', cx: 12, cy: 12, r: 4 },
    { t: 'path', d: 'M12 2v2' },
    { t: 'path', d: 'M12 20v2' },
    { t: 'path', d: 'M4.9 4.9l1.4 1.4' },
    { t: 'path', d: 'M17.7 17.7l1.4 1.4' },
    { t: 'path', d: 'M2 12h2' },
    { t: 'path', d: 'M20 12h2' },
    { t: 'path', d: 'M4.9 19.1l1.4-1.4' },
    { t: 'path', d: 'M17.7 6.3l1.4-1.4' },
  ],
  plane: [
    { t: 'path', d: 'M3 13l18-7-5 14-4-6z' },
    { t: 'path', d: 'M12 14l4-4' },
  ],
} satisfies Record<string, readonly IconElement[]>;

export type IconName = keyof typeof iconPaths;

export const iconNames = Object.keys(iconPaths) as IconName[];
