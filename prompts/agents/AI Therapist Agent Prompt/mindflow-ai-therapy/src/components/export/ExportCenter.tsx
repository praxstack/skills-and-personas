import { StorageService } from '@/services/storage.service';
import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useSessionStore } from '@/stores/sessionStore';
import React from 'react';

export const ExportCenter: React.FC = () => {
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);
  const pastSessions = useSessionStore((s) => s.pastSessions);
  const currentSession = useSessionStore((s) => s.currentSession);

  const download = (content: string, filename: string, type = 'application/json') => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportClinicalFile = () => {
    if (!clinicalFile) return;
    download(JSON.stringify(clinicalFile, null, 2), 'mindflow-clinical-file.json');
  };

  const exportSessions = () => {
    const allSessions = [...pastSessions, ...(currentSession ? [currentSession] : [])];
    download(JSON.stringify(allSessions, null, 2), 'mindflow-sessions.json');
  };

  const exportClinicalMarkdown = () => {
    if (!clinicalFile) return;
    const lines = [
      `# Clinical File — ${clinicalFile.profile.name}`,
      `Created: ${new Date(clinicalFile.createdAt).toLocaleDateString()}`,
      `Intake: ${clinicalFile.intakeApproach}`,
      '',
      '## Presenting Problems',
      ...clinicalFile.presentingProblems.map((p) => `- ${p}`),
      '',
      '## Screening History',
      ...clinicalFile.screeningHistory.map(
        (s) => `- ${s.type}: ${s.totalScore} (${s.severity}) — ${new Date(s.date).toLocaleDateString()}`,
      ),
      '',
      '## Treatment Goals',
      ...clinicalFile.treatmentGoals.map((g) => `- ${g.title}: ${g.progress}%`),
      '',
      '## Diagnosis Notes',
      clinicalFile.diagnosisNotes || 'None recorded.',
    ];
    download(lines.join('\n'), 'mindflow-clinical-file.md', 'text/markdown');
  };

  const exportFullBackup = () => {
    download(StorageService.exportAll(), `mindflow-full-backup-${new Date().toISOString().slice(0, 10)}.json`);
  };

  const cards = [
    { title: 'Clinical File (JSON)', desc: 'Structured clinical data', icon: '📁', action: exportClinicalFile, disabled: !clinicalFile },
    { title: 'Clinical File (Markdown)', desc: 'Human-readable summary', icon: '📄', action: exportClinicalMarkdown, disabled: !clinicalFile },
    { title: 'Session Logs', desc: 'All chat transcripts', icon: '💬', action: exportSessions, disabled: pastSessions.length === 0 && !currentSession },
    { title: 'Full Backup', desc: 'Everything — import later', icon: '💾', action: exportFullBackup, disabled: false },
  ];

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-semibold text-neutral-800 mb-2">Export Center</h1>
      <p className="text-sm text-neutral-400 mb-8">
        Download your data. All exports stay on your device.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {cards.map((card) => (
          <button
            key={card.title}
            onClick={card.action}
            disabled={card.disabled}
            className="bg-white border border-neutral-200 rounded-2xl p-6 text-left hover:shadow-md transition-shadow disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span className="text-3xl mb-3 block">{card.icon}</span>
            <h3 className="font-semibold text-neutral-800 mb-1">{card.title}</h3>
            <p className="text-xs text-neutral-400">{card.desc}</p>
          </button>
        ))}
      </div>
    </div>
  );
};
