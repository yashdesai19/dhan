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

/** A fetched DHAN AI answer, or why it couldn't be fetched. */
export type AssistantAnswer =
  | { answer: string; stats: AIResponse['stats'] }
  | { error: string };

interface AssistantStore {
  asked: AIResponse['id'][];
  typing: boolean;
  /** Answers fetched from the API, kept for the session so a question is asked only once. */
  answers: Partial<Record<AIResponse['id'], AssistantAnswer>>;
  ask: (id: AIResponse['id']) => void;
  doneTyping: () => void;
  setAnswer: (id: AIResponse['id'], answer: AssistantAnswer) => void;
  reset: () => void;
}

export const useAssistantStore = create<AssistantStore>((set, get) => ({
  asked: ['most'],
  typing: false,
  answers: {},
  ask: (id) => {
    if (get().typing || get().asked.includes(id)) return;
    set({ asked: [...get().asked, id], typing: true });
  },
  doneTyping: () => set({ typing: false }),
  setAnswer: (id, answer) => set({ answers: { ...get().answers, [id]: answer } }),
  reset: () => set({ asked: ['most'], typing: false, answers: {} }),
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
