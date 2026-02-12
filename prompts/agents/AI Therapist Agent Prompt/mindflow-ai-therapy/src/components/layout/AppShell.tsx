import { CrisisBanner } from '@/components/safety/CrisisBanner';
import { useUIStore } from '@/stores/uiStore';
import React from 'react';
import { Sidebar } from './Sidebar';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="flex h-screen bg-neutral-50 overflow-hidden">
      <Sidebar />
      <main
        className={`flex-1 flex flex-col transition-all duration-300 ${
          sidebarOpen ? 'ml-64' : 'ml-0'
        }`}
      >
        <CrisisBanner />
        <div className="flex-1 overflow-y-auto">{children}</div>
      </main>
    </div>
  );
};
