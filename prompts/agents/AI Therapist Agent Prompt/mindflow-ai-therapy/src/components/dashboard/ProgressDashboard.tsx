import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useSessionStore } from '@/stores/sessionStore';
import React from 'react';

export const ProgressDashboard: React.FC = () => {
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);
  const pastSessions = useSessionStore((s) => s.pastSessions);

  if (!clinicalFile) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <span className="text-4xl mb-4 block">📊</span>
        <h2 className="text-xl font-semibold text-neutral-700 mb-2">No Data Yet</h2>
        <p className="text-neutral-400 text-sm">Complete your intake and a session to see progress data.</p>
      </div>
    );
  }

  const screeningHistory = clinicalFile.screeningHistory;
  const phq9Scores = screeningHistory.filter((s) => s.type === 'PHQ9');
  const gad7Scores = screeningHistory.filter((s) => s.type === 'GAD7');

  const getSeverityColor = (severity: string) => {
    if (severity.includes('Severe')) return 'bg-red-100 text-red-700';
    if (severity.includes('Moderate')) return 'bg-amber-100 text-amber-700';
    if (severity.includes('Mild')) return 'bg-yellow-100 text-yellow-700';
    return 'bg-green-100 text-green-700';
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-neutral-800 mb-1">Progress Dashboard</h1>
        <p className="text-sm text-neutral-400">
          Tracking your therapeutic journey, {clinicalFile.profile.name}.
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Sessions', value: pastSessions.length, icon: '💬' },
          { label: 'Screenings', value: screeningHistory.length, icon: '📋' },
          { label: 'Goals', value: clinicalFile.treatmentGoals.length, icon: '🎯' },
          { label: 'Days Active', value: Math.max(1, Math.ceil((Date.now() - clinicalFile.createdAt) / 86400000)), icon: '📅' },
        ].map((stat) => (
          <div key={stat.label} className="bg-white border border-neutral-200 rounded-xl p-4 text-center">
            <span className="text-2xl block mb-1">{stat.icon}</span>
            <p className="text-2xl font-bold text-primary">{stat.value}</p>
            <p className="text-xs text-neutral-400">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Screening history */}
      {screeningHistory.length > 0 && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-4">Screening History</h2>

          {/* PHQ-9 trend */}
          {phq9Scores.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-neutral-600 mb-3">🌧️ PHQ-9 (Depression)</h3>
              <div className="flex items-end gap-2 h-24">
                {phq9Scores.map((s, i) => (
                  <div key={s.id} className="flex flex-col items-center flex-1">
                    <span className="text-xs text-neutral-500 mb-1">{s.totalScore}</span>
                    <div
                      className="w-full bg-primary/20 rounded-t-md transition-all"
                      style={{ height: `${Math.max(8, (s.totalScore / 27) * 100)}%` }}
                    />
                    <span className="text-[10px] text-neutral-300 mt-1">#{i + 1}</span>
                  </div>
                ))}
              </div>
              <div className="mt-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${getSeverityColor(phq9Scores[phq9Scores.length - 1].severity)}`}>
                  Latest: {phq9Scores[phq9Scores.length - 1].severity} ({phq9Scores[phq9Scores.length - 1].totalScore}/27)
                </span>
              </div>
            </div>
          )}

          {/* GAD-7 trend */}
          {gad7Scores.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-neutral-600 mb-3">😰 GAD-7 (Anxiety)</h3>
              <div className="flex items-end gap-2 h-24">
                {gad7Scores.map((s, i) => (
                  <div key={s.id} className="flex flex-col items-center flex-1">
                    <span className="text-xs text-neutral-500 mb-1">{s.totalScore}</span>
                    <div
                      className="w-full bg-accent/20 rounded-t-md transition-all"
                      style={{ height: `${Math.max(8, (s.totalScore / 21) * 100)}%` }}
                    />
                    <span className="text-[10px] text-neutral-300 mt-1">#{i + 1}</span>
                  </div>
                ))}
              </div>
              <div className="mt-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${getSeverityColor(gad7Scores[gad7Scores.length - 1].severity)}`}>
                  Latest: {gad7Scores[gad7Scores.length - 1].severity} ({gad7Scores[gad7Scores.length - 1].totalScore}/21)
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Treatment goals */}
      {clinicalFile.treatmentGoals.length > 0 && (
        <div className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-4">Treatment Goals</h2>
          <div className="space-y-3">
            {clinicalFile.treatmentGoals.map((goal) => (
              <div key={goal.id} className="flex items-center gap-4">
                <div className="flex-1">
                  <p className="text-sm font-medium text-neutral-700">{goal.title}</p>
                  <div className="mt-1 w-full bg-neutral-100 rounded-full h-2">
                    <div
                      className="bg-secondary h-2 rounded-full transition-all"
                      style={{ width: `${goal.progress}%` }}
                    />
                  </div>
                </div>
                <span className="text-sm font-medium text-neutral-500">{goal.progress}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
