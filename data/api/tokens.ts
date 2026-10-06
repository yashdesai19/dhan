// Session tokens live in the OS keychain/keystore (expo-secure-store), never in AsyncStorage.
import * as SecureStore from 'expo-secure-store';

const KEYS = {
  access: 'dhan.accessToken',
  refresh: 'dhan.refreshToken',
  userId: 'dhan.userId',
} as const;

type Key = keyof typeof KEYS;
const cache: Partial<Record<Key, string | null>> = {};

async function read(key: Key): Promise<string | null> {
  if (!(key in cache)) cache[key] = await SecureStore.getItemAsync(KEYS[key]);
  return cache[key] ?? null;
}

async function write(key: Key, value: string | null): Promise<void> {
  cache[key] = value;
  if (value === null) await SecureStore.deleteItemAsync(KEYS[key]);
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
