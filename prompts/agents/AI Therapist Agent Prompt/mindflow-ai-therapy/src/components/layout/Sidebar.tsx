import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useUIStore } from '@/stores/uiStore';
import type { ViewId } from '@/types';
import React from 'react';

const NAV_ITEMS: { id: ViewId; label: string; icon: string }[] = [
  { id: 'chat', label: 'Therapy Chat', icon: '💬' },
  { id: 'screening', label: 'Screening', icon: '📋' },
  { id: 'dashboard', label: 'Progress', icon: '📊' },
  { id: 'clinical-file', label: 'Clinical File', icon: '📁' },
  { id: 'export', label: 'Export', icon: '📤' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
];

export const Sidebar: React.FC = () => {
  const { activeView, setView, sidebarOpen, toggleSidebar } = useUIStore();
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);

  return (
    <>
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 lg:hidden"
          onClick={toggleSidebar}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-full z-40 w-64 bg-white border-r border-neutral-200 flex flex-col transition-transform duration-300 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand */}
        <div className="p-5 border-b border-neutral-200">
          <h1 className="text-xl font-semibold text-primary flex items-center gap-2">
            <span className="text-2xl">🧠</span> MindFlow
          </h1>
          <p className="text-xs text-neutral-400 mt-1">AI Therapy Assistant</p>
        </div>

        {/* Profile badge */}
        {clinicalFile && (
          <div className="mx-4 mt-4 px-3 py-2 bg-primary/5 rounded-lg">
            <p className="text-sm font-medium text-neutral-700 truncate">
              {clinicalFile.profile.name}
            </p>
            <p className="text-xs text-neutral-400">
              Session {clinicalFile.sessions.length + 1}
            </p>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                activeView === item.id
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-neutral-600 hover:bg-neutral-100'
              }`}
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-200">
          <p className="text-[10px] text-neutral-300 text-center">
            MindFlow v1.0 — Not a substitute for professional care
          </p>
        </div>
      </aside>

      {/* Toggle button when collapsed */}
      {!sidebarOpen && (
        <button
          onClick={toggleSidebar}
          className="fixed top-4 left-4 z-50 p-2 bg-white border border-neutral-200 rounded-lg shadow-sm hover:bg-neutral-50 transition-colors"
          aria-label="Open menu"
        >
          <span className="text-lg">☰</span>
        </button>
      )}
    </>
  );
};
