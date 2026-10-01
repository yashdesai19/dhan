import { router } from 'expo-router';

import { ConfirmSheet, Sheet, useSheet } from '@/components';
import { useSessionStore } from '@/store/session';
import { useAssistantStore } from '@/store/ui';

function Body() {
  const { close } = useSheet();
  const signOut = useSessionStore((s) => s.signOut);
  return (
    <ConfirmSheet
      icon="logout"
      title="Sign out of DHAN?"
      body="Your data stays in your account. You’ll need to log in again on this phone."
      confirmLabel="Sign out"
      onConfirm={() =>
        close(() => {
          // Navigate first, then clear the session, so the (app) guard doesn't race this.
          router.replace('/login');
          setTimeout(() => {
            signOut();
            useAssistantStore.getState().reset();
          }, 0);
        })
      }
    />
  );
}

export function SignOutSheet() {
  return (
    <Sheet label="Sign out confirmation">
      <Body />
    </Sheet>
  );
}
