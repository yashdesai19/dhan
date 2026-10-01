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
