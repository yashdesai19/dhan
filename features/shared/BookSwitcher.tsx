import { ChipGroup } from '@/components';
import { usePrefsStore } from '@/store/prefs';
import { ALL_BOOKS_ID } from '@/utils/books';
import { useActiveBook } from './hooks';

/** Chips for moving between books. Hidden until the user has a business book. */
export function BookSwitcher() {
  const { id, books, hasBusiness } = useActiveBook();
  const set = usePrefsStore((s) => s.set);
  if (!hasBusiness) return null;
  return (
    <ChipGroup
      wrap={false}
      options={[
        ...books.map((b) => ({ value: b.id, label: b.name })),
        { value: ALL_BOOKS_ID, label: 'All' },
      ]}
      selected={[id]}
      onChange={([v]) => v && set('activeBookId', v)}
    />
  );
}
