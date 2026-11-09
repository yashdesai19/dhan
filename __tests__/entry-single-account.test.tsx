import { renderHook } from '@testing-library/react-native';

import { useValidDraftIds } from '@/features/entry/EntryParts';
import { useEntryDraftStore } from '@/store/drafts';
import type { Account } from '@/types/domain';

const cash = { id: 'cash', name: 'Cash', archived: false } as Account;

// A new user owns only Cash. Opening Add expense used to loop until React crashed the screen.
it('settles on the only account instead of updating the draft forever', () => {
  const patch = jest.spyOn(useEntryDraftStore.getState(), 'patch');
  const accounts = [cash];
  const categories: never[] = [];
  expect(() => renderHook(() => useValidDraftIds(accounts, categories))).not.toThrow();
  const { accountId, fromId, toId } = useEntryDraftStore.getState().draft;
  expect([accountId, fromId, toId]).toEqual(['cash', 'cash', 'cash']);
  patch.mockRestore();
});
