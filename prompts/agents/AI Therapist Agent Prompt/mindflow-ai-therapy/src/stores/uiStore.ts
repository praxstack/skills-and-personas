// ═══════════════════════════════════════════════════════════════
// UI Store — Navigation, sidebar, settings
// ═══════════════════════════════════════════════════════════════

import { DEFAULT_MODEL } from '@/config/constants';
import type { AppSettings, ViewId } from '@/types';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIState {
  activeView: ViewId;
  sidebarOpen: boolean;
  settings: AppSettings;
  setView: (view: ViewId) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  updateSettings: (patch: Partial<AppSettings>) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      activeView: 'chat' as ViewId,
      sidebarOpen: true,
      settings: {
        apiKey: '',
        modelId: DEFAULT_MODEL,
        darkMode: false,
      },

      setView: (view) => set({ activeView: view }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      updateSettings: (patch) =>
        set((s) => ({ settings: { ...s.settings, ...patch } })),
    }),
    { name: 'mindflow_settings' },
  ),
);
