// ═══════════════════════════════════════════════════════════════
// Session Store — Chat messages and session state
// ═══════════════════════════════════════════════════════════════

import type { Message, Session } from '@/types';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SessionState {
  currentSession: Session | null;
  pastSessions: Session[];
  isLoading: boolean;
  error: string | null;
  startSession: () => void;
  addMessage: (role: Message['role'], content: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  endSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      currentSession: null,
      pastSessions: [],
      isLoading: false,
      error: null,

      startSession: () => {
        const { pastSessions } = get();
        set({
          currentSession: {
            id: crypto.randomUUID(),
            number: pastSessions.length + 1,
            startedAt: Date.now(),
            messages: [],
          },
          error: null,
        });
      },

      addMessage: (role, content) =>
        set((state) => {
          if (!state.currentSession) return state;
          const msg: Message = {
            id: crypto.randomUUID(),
            role,
            content,
            timestamp: Date.now(),
          };
          return {
            currentSession: {
              ...state.currentSession,
              messages: [...state.currentSession.messages, msg],
            },
          };
        }),

      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),

      endSession: () =>
        set((state) => {
          if (!state.currentSession) return state;
          const finished: Session = { ...state.currentSession, endedAt: Date.now() };
          return {
            currentSession: null,
            pastSessions: [...state.pastSessions, finished],
          };
        }),
    }),
    { name: 'mindflow_sessions' },
  ),
);
