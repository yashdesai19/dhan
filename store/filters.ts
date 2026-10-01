import { create } from 'zustand';

import { defaultFilters, type TxFilters } from '@/utils/filters';

export * from '@/utils/filters';

interface FiltersStore {
  filters: TxFilters;
  set: (p: Partial<TxFilters>) => void;
  reset: () => void;
}

export const useFiltersStore = create<FiltersStore>((set) => ({
  filters: defaultFilters,
  set: (p) => set((s) => ({ filters: { ...s.filters, ...p } })),
  reset: () => set({ filters: defaultFilters }),
}));
