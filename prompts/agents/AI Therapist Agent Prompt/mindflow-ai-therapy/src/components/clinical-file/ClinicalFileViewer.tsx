import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import React from 'react';

export const ClinicalFileViewer: React.FC = () => {
  const clinicalFile = useClinicalFileStore((s) => s.clinicalFile);

  if (!clinicalFile) {
    return (
      <div className="max-w-2xl mx-auto py-20 text-center">
        <span className="text-4xl mb-4 block">📁</span>
        <h2 className="text-xl font-semibold text-neutral-700 mb-2">No Clinical File</h2>
        <p className="text-neutral-400 text-sm">Complete your intake to create a clinical file.</p>
      </div>
    );
  }

  const formatDate = (ts: number) =>
    new Date(ts).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="max-w-3xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-neutral-800 mb-1">Clinical File</h1>
        <p className="text-sm text-neutral-400">
          Created {formatDate(clinicalFile.createdAt)} · Last updated {formatDate(clinicalFile.updatedAt)}
        </p>
      </div>

      {/* Demographics */}
      <section className="bg-white border border-neutral-200 rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-neutral-800 mb-3">👤 Demographics</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-neutral-400">Name</span>
            <p className="font-medium text-neutral-700">{clinicalFile.profile.name}</p>
          </div>
          {clinicalFile.profile.age && (
            <div>
              <span className="text-neutral-400">Age</span>
              <p className="font-medium text-neutral-700">{clinicalFile.profile.age}</p>
            </div>
          )}
          {clinicalFile.profile.pronouns && (
            <div>
              <span className="text-neutral-400">Pronouns</span>
              <p className="font-medium text-neutral-700">{clinicalFile.profile.pronouns}</p>
            </div>
          )}
          <div>
            <span className="text-neutral-400">Intake Approach</span>
            <p className="font-medium text-neutral-700 capitalize">{clinicalFile.intakeApproach}</p>
          </div>
        </div>
      </section>

      {/* Presenting Problems */}
      {clinicalFile.presentingProblems.length > 0 && (
        <section className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-3">🔍 Presenting Problems</h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-neutral-600">
            {clinicalFile.presentingProblems.map((p, i) => (
              <li key={i}>{p}</li>
            ))}
          </ul>
        </section>
      )}

      {/* Screening Summary */}
      {clinicalFile.screeningHistory.length > 0 && (
        <section className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-3">📋 Screening History</h2>
          <div className="space-y-2">
            {clinicalFile.screeningHistory.map((s) => (
              <div key={s.id} className="flex items-center justify-between bg-neutral-50 rounded-lg px-4 py-2">
                <div>
                  <span className="text-sm font-medium text-neutral-700">{s.type}</span>
                  <span className="text-xs text-neutral-400 ml-2">{formatDate(s.date)}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-primary">{s.totalScore}</span>
                  <span className="text-xs text-neutral-400 ml-2">({s.severity})</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Diagnosis Notes */}
      {clinicalFile.diagnosisNotes && (
        <section className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-3">📝 Diagnosis Notes</h2>
          <p className="text-sm text-neutral-600 whitespace-pre-wrap">{clinicalFile.diagnosisNotes}</p>
        </section>
      )}

      {/* Medications */}
      {clinicalFile.medications.length > 0 && (
        <section className="bg-white border border-neutral-200 rounded-2xl p-6">
          <h2 className="text-lg font-semibold text-neutral-800 mb-3">💊 Medications</h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-neutral-600">
            {clinicalFile.medications.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
};
