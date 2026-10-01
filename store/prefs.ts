import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type ThemePref = 'system' | 'light' | 'dark';
export type LockAfter = 'now' | '1m' | '5m';

export interface Prefs {
  theme: ThemePref;
  hideBalances: boolean;
  budgetAlerts: boolean;
  weeklySummary: boolean;
  appLock: boolean;
  lockAfter: LockAfter;
  hideInSwitcher: boolean;
  notify: { bills: boolean; budget: boolean; splits: boolean; ai: boolean };
}

interface PrefsStore extends Prefs {
  /** True once AsyncStorage has been read (not persisted). */
  hydrated: boolean;
  set: <K extends keyof Prefs>(key: K, value: Prefs[K]) => void;
  setNotify: (key: keyof Prefs['notify'], value: boolean) => void;
}

export const defaultPrefs: Prefs = {
  theme: 'system',
  hideBalances: false,
  budgetAlerts: true,
  weeklySummary: true,
  appLock: true,
  lockAfter: '1m',
  hideInSwitcher: true,
  notify: { bills: true, budget: true, splits: true, ai: false },
};

export const usePrefsStore = create<PrefsStore>()(
  persist(
    (set) => ({
      ...defaultPrefs,
      hydrated: false,
      set: (key, value) => set({ [key]: value } as Partial<Prefs>),
      setNotify: (key, value) => set((s) => ({ notify: { ...s.notify, [key]: value } })),
    }),
    {
      name: 'dhan.prefs',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s): Prefs => ({
        theme: s.theme,
        hideBalances: s.hideBalances,
        budgetAlerts: s.budgetAlerts,
        weeklySummary: s.weeklySummary,
        appLock: s.appLock,
        lockAfter: s.lockAfter,
        hideInSwitcher: s.hideInSwitcher,
        notify: s.notify,
      }),
      onRehydrateStorage: () => () => usePrefsStore.setState({ hydrated: true }),
    },
  ),
);
