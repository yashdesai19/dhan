import { create } from 'zustand';

import type { AIResponse } from '@/types/domain';

export interface ToastSpec {
  id: number;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  /** 'tabs' sits above the tab bar (112); 'footer' above a sticky footer (120). */
  placement: 'tabs' | 'footer' | 'bottom';
}

interface ToastStore {
  current: ToastSpec | null;
  show: (t: Omit<ToastSpec, 'id' | 'placement'> & { placement?: ToastSpec['placement'] }) => void;
  hide: (id?: number) => void;
}

let toastId = 0;

/** One toast at a time (spec §14). */
export const useToastStore = create<ToastStore>((set, get) => ({
  current: null,
  show: (t) => {
    toastId += 1;
    set({ current: { placement: 'tabs', ...t, id: toastId } });
  },
  hide: (id) => {
    if (id === undefined || get().current?.id === id) set({ current: null });
  },
}));

interface AssistantStore {
  asked: AIResponse['id'][];
  typing: boolean;
  ask: (id: AIResponse['id']) => void;
  doneTyping: () => void;
  reset: () => void;
}

export const useAssistantStore = create<AssistantStore>((set, get) => ({
  asked: ['most'],
  typing: false,
  ask: (id) => {
    if (get().typing || get().asked.includes(id)) return;
    set({ asked: [...get().asked, id], typing: true });
  },
  doneTyping: () => set({ typing: false }),
  reset: () => set({ asked: ['most'], typing: false }),
}));

interface HighlightStore {
  /** The row just saved; Home and Activity tint it primary-soft while the toast shows. */
  id: string | null;
  set: (id: string | null) => void;
}

export const useHighlightStore = create<HighlightStore>((set) => ({
  id: null,
  set: (id) => set({ id }),
}));
