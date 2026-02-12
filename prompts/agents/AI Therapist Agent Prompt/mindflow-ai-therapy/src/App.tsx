import { ChatView } from '@/components/chat/ChatView';
import { ClinicalFileViewer } from '@/components/clinical-file/ClinicalFileViewer';
import { ProgressDashboard } from '@/components/dashboard/ProgressDashboard';
import { ExportCenter } from '@/components/export/ExportCenter';
import { IntakeSelection } from '@/components/intake/IntakeSelection';
import { AppShell } from '@/components/layout/AppShell';
import { ScreeningHub } from '@/components/screening/ScreeningHub';
import { SettingsView } from '@/components/settings/SettingsView';
import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useUIStore } from '@/stores/uiStore';
import React from 'react';

const ViewMap: Record<string, React.FC> = {
  chat: ChatView,
  intake: IntakeSelection,
  screening: ScreeningHub,
  dashboard: ProgressDashboard,
  'clinical-file': ClinicalFileViewer,
  settings: SettingsView,
  export: ExportCenter,
};

const App: React.FC = () => {
  const activeView = useUIStore((s) => s.activeView);
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);

  // Force intake if no clinical file exists (except settings)
  const effectiveView = !clinicalFile && activeView !== 'settings' ? 'intake' : activeView;
  const ActiveComponent = ViewMap[effectiveView] || ChatView;

  return (
    <AppShell>
      <ActiveComponent />
    </AppShell>
  );
};

export default App;
