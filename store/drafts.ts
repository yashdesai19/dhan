import { create } from 'zustand';

import type { ID, SplitMethod } from '@/types/domain';
import type { SplitItem } from '@/utils/splits';

export { amountValue, pressKey } from '@/utils/keypad';

/** In-progress Add expense / Add income / Transfer values; restored by Undo (spec §12). */
export interface EntryDraft {
  amount: string;
  categoryId: ID;
  incomeSourceId: ID;
  accountId: ID;
  fromId: ID;
  toId: ID;
  date?: string;
  note: string;
}

export const initialEntry: EntryDraft = {
  amount: '0',
  categoryId: 'food',
  incomeSourceId: 'salary',
  accountId: 'hdfc',
  fromId: 'hdfc',
  toId: 'cash',
  note: '',
};

interface EntryDraftStore {
  draft: EntryDraft;
  patch: (p: Partial<EntryDraft>) => void;
  reset: () => void;
  restore: (d: EntryDraft) => void;
}

export const useEntryDraftStore = create<EntryDraftStore>((set) => ({
  draft: initialEntry,
  patch: (p) => set((s) => ({ draft: { ...s.draft, ...p } })),
  reset: () => set({ draft: initialEntry }),
  restore: (d) => set({ draft: d }),
}));

export interface SplitDraft {
  amount: string;
  title: string;
  paidBy: ID;
  /** Account you paid from, when you paid; empty means your first account. */
  accountId: ID;
  groupId: ID;
  method: SplitMethod;
  included: Record<ID, boolean>;
  exact: Record<ID, string>;
  percent: Record<ID, string>;
  shares: Record<ID, number>;
  items: SplitItem[];
}

export const initialSplit: SplitDraft = {
  amount: '',
  title: '',
  paidBy: 'me',
  accountId: '',
  groupId: 'goa',
  method: 'equal',
  included: { me: true, aman: true, rahul: true, karan: true },
  exact: {},
  percent: { me: '25', aman: '25', rahul: '25', karan: '25' },
  shares: { me: 1, aman: 1, rahul: 1, karan: 1 },
  items: [
    { id: 'i1', title: 'Villa rent', amount: 10000, memberIds: ['me', 'aman', 'rahul', 'karan'] },
    { id: 'i2', title: 'Late checkout fee', amount: 2000, memberIds: ['me', 'aman'] },
  ],
};

interface SplitDraftStore {
  draft: SplitDraft;
  patch: (p: Partial<SplitDraft>) => void;
  reset: (p?: Partial<SplitDraft>) => void;
  restore: (d: SplitDraft) => void;
}

export const useSplitDraftStore = create<SplitDraftStore>((set) => ({
  draft: initialSplit,
  patch: (p) => set((s) => ({ draft: { ...s.draft, ...p } })),
  reset: (p) => set({ draft: { ...initialSplit, ...p } }),
  restore: (d) => set({ draft: d }),
}));
