import { useCallback } from 'react';
import { useRouter, type Href } from 'expo-router';

/** Close every modal and sheet above the tabs, then show a tab (success flows, spec §7). */
export function useReturnTo() {
  const router = useRouter();
  return useCallback(
    (href: Href) => {
      if (router.canDismiss()) router.dismissAll();
      router.navigate(href);
    },
    [router],
  );
}
