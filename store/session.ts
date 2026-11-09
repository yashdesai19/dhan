import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { hasBrowserSession } from '@/data/api/tokens';

/** Mock session (spec §12). No auth service: a flag decides which stack opens. */
interface SessionStore {
  onboarded: boolean;
  signedIn: boolean;
  /** Not persisted: every cold start with app lock on begins locked. */
  locked: boolean;
  hydrated: boolean;
  completeOnboarding: () => void;
  signIn: () => void;
  signOut: () => void;
  lock: () => void;
  unlock: () => void;
  setHydrated: () => void;
}

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      onboarded: false,
      signedIn: false,
      locked: true,
      hydrated: false,
      completeOnboarding: () => set({ onboarded: true }),
      signIn: () => set({ signedIn: true, onboarded: true, locked: false }),
      signOut: () => set({ signedIn: false, locked: false }),
      lock: () => set({ locked: true }),
      unlock: () => set({ locked: false }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: 'dhan.session',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({ onboarded: s.onboarded, signedIn: s.signedIn }),
      onRehydrateStorage: () => (state) => {
        // A browser forgets its login with the tab; don't open the app as if still signed in
        if (Platform.OS === 'web' && state?.signedIn && !hasBrowserSession()) state.signOut();
        state?.setHydrated();
      },
    },
  ),
);
