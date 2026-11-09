// Session tokens live in the OS keychain/keystore (expo-secure-store), never in AsyncStorage.
// Browsers have no keystore: there they stay in sessionStorage, gone when the tab is closed.
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

const KEYS = {
  access: 'dhan.accessToken',
  refresh: 'dhan.refreshToken',
  userId: 'dhan.userId',
} as const;

type Key = keyof typeof KEYS;

const isWeb = Platform.OS === 'web';

/** Web only: whether this browser session still holds a login. */
export function hasBrowserSession(): boolean {
  return isWeb && sessionStorage.getItem(KEYS.refresh) !== null;
}
const cache: Partial<Record<Key, string | null>> = {};

async function read(key: Key): Promise<string | null> {
  if (!(key in cache)) {
    cache[key] = isWeb ? sessionStorage.getItem(KEYS[key]) : await SecureStore.getItemAsync(KEYS[key]);
  }
  return cache[key] ?? null;
}

async function write(key: Key, value: string | null): Promise<void> {
  cache[key] = value;
  if (isWeb) {
    if (value === null) sessionStorage.removeItem(KEYS[key]);
    else sessionStorage.setItem(KEYS[key], value);
  } else if (value === null) await SecureStore.deleteItemAsync(KEYS[key]);
  else await SecureStore.setItemAsync(KEYS[key], value);
}

export const tokens = {
  access: () => read('access'),
  refresh: () => read('refresh'),
  userId: () => read('userId'),
  async save(access: string, refresh: string): Promise<void> {
    await Promise.all([write('access', access), write('refresh', refresh)]);
  },
  saveUserId: (id: string) => write('userId', id),
  async clear(): Promise<void> {
    await Promise.all([write('access', null), write('refresh', null), write('userId', null)]);
  },
};
