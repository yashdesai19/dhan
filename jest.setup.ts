import { mockConfig } from '@/mock/config';

// Repositories resolve instantly in tests.
mockConfig.latency = [0, 0];

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);
jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn(),
  notificationAsync: jest.fn(),
  selectionAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' },
  NotificationFeedbackType: { Success: 'success', Warning: 'warning', Error: 'error' },
}));
// The phone confirms its owner unless a test says otherwise
jest.mock('expo-local-authentication', () => ({
  SecurityLevel: { NONE: 0, SECRET: 1, BIOMETRIC_WEAK: 2, BIOMETRIC_STRONG: 3 },
  getEnrolledLevelAsync: jest.fn(async () => 3),
  authenticateAsync: jest.fn(async () => ({ success: true })),
}));
jest.mock(
  'react-native-safe-area-context',
  () => require('react-native-safe-area-context/jest/mock').default,
);
// Worklets and Reanimated mocks for Jest tests.
jest.mock('react-native-worklets', () => ({
  createWorkletRuntime: jest.fn(),
  runOnJS: (fn: (...args: unknown[]) => unknown) => fn,
  runOnUI: (fn: (...args: unknown[]) => unknown) => fn,
  scheduleOnUI: (fn: (...args: unknown[]) => unknown) => fn,
  makeMutable: (val: unknown) => ({ value: val }),
  useSharedValue: (val: unknown) => ({ value: val }),
  useWorkletCallback: (fn: (...args: unknown[]) => unknown) => fn,
  createSerializable: (v: unknown) => v,
  isWorkletFunction: () => false,
  serializableMappingCache: new Map(),
  RuntimeKind: { JS: 0, UI: 1 },
}));
jest.mock('react-native-reanimated', () => ({
  ...require('react-native-reanimated/mock'),
  useReducedMotion: () => false,
}));
jest.mock('@gorhom/bottom-sheet', () => ({
  __esModule: true,
  ...require('@gorhom/bottom-sheet/mock'),
}));

export const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  back: jest.fn(),
  canGoBack: jest.fn(() => true),
  canDismiss: jest.fn(() => true),
  dismissAll: jest.fn(),
  navigate: jest.fn(),
  setParams: jest.fn(),
};

jest.mock('expo-router', () => ({
  useRouter: () => mockRouter,
  router: mockRouter,
  useLocalSearchParams: () => ({ id: 'hdfc', personId: 'karan', category: 'food' }),
  usePathname: () => '/',
  Redirect: () => null,
  Stack: Object.assign(({ children }: { children?: React.ReactNode }) => children ?? null, {
    Screen: () => null,
  }),
}));
