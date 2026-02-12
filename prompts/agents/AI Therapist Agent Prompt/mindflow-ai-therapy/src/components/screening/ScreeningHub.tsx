import { GAD7_OPTIONS, GAD7_QUESTIONS, PHQ9_OPTIONS, PHQ9_QUESTIONS } from '@/config/constants';
import { createScreeningResult } from '@/services/screening.service';
import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useUIStore } from '@/stores/uiStore';
import type { ScreenerType } from '@/types';
import React from 'react';

const SCREENERS: { id: ScreenerType; title: string; icon: string; questions: string[]; options: { value: number; label: string }[] }[] = [
  { id: 'PHQ9', title: 'PHQ-9 — Depression', icon: '🌧️', questions: PHQ9_QUESTIONS, options: PHQ9_OPTIONS },
  { id: 'GAD7', title: 'GAD-7 — Anxiety', icon: '😰', questions: GAD7_QUESTIONS, options: GAD7_OPTIONS },
];

export const ScreeningHub: React.FC = () => {
  const [activeScreener, setActiveScreener] = React.useState<typeof SCREENERS[0] | null>(null);
  const [answers, setAnswers] = React.useState<number[]>([]);
  const [currentQ, setCurrentQ] = React.useState(0);
  const [result, setResult] = React.useState<ReturnType<typeof createScreeningResult> | null>(null);
  const addScreeningResult = useClinicalFileStore((s) => s.addScreeningResult);
  const setView = useUIStore((s) => s.setView);

  const startScreener = (screener: typeof SCREENERS[0]) => {
    setActiveScreener(screener);
    setAnswers(new Array(screener.questions.length).fill(-1));
    setCurrentQ(0);
    setResult(null);
  };

  const handleAnswer = (value: number) => {
    const newAnswers = [...answers];
    newAnswers[currentQ] = value;
    setAnswers(newAnswers);

    if (currentQ < (activeScreener?.questions.length ?? 0) - 1) {
      setCurrentQ(currentQ + 1);
    }
  };

  const handleSubmit = () => {
    if (!activeScreener || answers.includes(-1)) return;
    const r = createScreeningResult(activeScreener.id, answers);
    addScreeningResult(r);
    setResult(r);
  };

  const getSeverityColor = (severity: string) => {
    if (severity.includes('Severe')) return 'text-red-600 bg-red-50';
    if (severity.includes('Moderate')) return 'text-amber-600 bg-amber-50';
    if (severity.includes('Mild')) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  // Results view
  if (result) {
    return (
      <div className="max-w-2xl mx-auto py-12 px-4 animate-fade-in">
        <div className="bg-white rounded-2xl border border-neutral-200 p-8 shadow-sm text-center">
          <h2 className="text-2xl font-semibold text-neutral-800 mb-2">
            {activeScreener?.title} Results
          </h2>
          <div className="my-6">
            <p className="text-5xl font-bold text-primary">{result.totalScore}</p>
            <span className={`inline-block mt-2 px-4 py-1.5 rounded-full text-sm font-medium ${getSeverityColor(result.severity)}`}>
              {result.severity}
            </span>
          </div>
          <p className="text-sm text-neutral-500 leading-relaxed mb-6">{result.interpretation}</p>
          {result.flagged && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-left">
              <p className="text-sm text-red-700 font-medium">
                ⚠️ Your response to the suicidal ideation question has been flagged. Please discuss this with Dr. Morgan in your session.
              </p>
            </div>
          )}
          <div className="flex gap-3 justify-center">
            <button onClick={() => { setActiveScreener(null); setResult(null); }} className="px-5 py-2.5 border border-neutral-300 rounded-xl text-sm hover:bg-neutral-50 transition-colors">
              Take Another
            </button>
            <button onClick={() => setView('chat')} className="px-5 py-2.5 bg-primary text-white rounded-xl text-sm hover:bg-primary-dark transition-colors">
              Discuss with Dr. Morgan
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Questionnaire view
  if (activeScreener) {
    const progress = answers.filter((a) => a >= 0).length / activeScreener.questions.length;
    const allAnswered = !answers.includes(-1);

    return (
      <div className="max-w-2xl mx-auto py-12 px-4 animate-fade-in">
        <div className="bg-white rounded-2xl border border-neutral-200 p-8 shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-neutral-800">{activeScreener.title}</h2>
            <span className="text-sm text-neutral-400">
              {currentQ + 1} / {activeScreener.questions.length}
            </span>
          </div>

          {/* Progress bar */}
          <div className="w-full bg-neutral-100 rounded-full h-1.5 mb-8">
            <div
              className="bg-primary h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${progress * 100}%` }}
            />
          </div>

          <p className="text-sm text-neutral-500 mb-2">
            Over the <strong>last 2 weeks</strong>, how often have you been bothered by:
          </p>
          <p className="text-base font-medium text-neutral-800 mb-6">
            {activeScreener.questions[currentQ]}
          </p>

          <div className="space-y-2 mb-8">
            {activeScreener.options.map((opt) => (
              <button
                key={opt.value}
                onClick={() => handleAnswer(opt.value)}
                className={`w-full text-left px-4 py-3 rounded-xl border-2 text-sm transition-all ${
                  answers[currentQ] === opt.value
                    ? 'border-primary bg-primary/5 text-primary font-medium'
                    : 'border-neutral-200 hover:border-neutral-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex justify-between">
            <button
              onClick={() => setCurrentQ(Math.max(0, currentQ - 1))}
              disabled={currentQ === 0}
              className="px-4 py-2 text-sm text-neutral-500 hover:text-neutral-700 disabled:opacity-30"
            >
              ← Previous
            </button>
            {currentQ < activeScreener.questions.length - 1 ? (
              <button
                onClick={() => setCurrentQ(currentQ + 1)}
                disabled={answers[currentQ] < 0}
                className="px-5 py-2 bg-primary text-white rounded-xl text-sm disabled:opacity-40"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={!allAnswered}
                className="px-5 py-2 bg-secondary text-white rounded-xl text-sm font-medium disabled:opacity-40"
              >
                Submit & Score
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Screener selection
  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      <h1 className="text-2xl font-semibold text-neutral-800 mb-2">Screening Tools</h1>
      <p className="text-neutral-500 text-sm mb-8">
        Validated clinical questionnaires to track your symptoms over time.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {SCREENERS.map((s) => (
          <button
            key={s.id}
            onClick={() => startScreener(s)}
            className="bg-white border border-neutral-200 rounded-2xl p-6 text-left hover:shadow-md transition-shadow"
          >
            <span className="text-3xl mb-3 block">{s.icon}</span>
            <h3 className="font-semibold text-neutral-800 mb-1">{s.title}</h3>
            <p className="text-xs text-neutral-400">{s.questions.length} questions · ~2 min</p>
          </button>
        ))}
      </div>
    </div>
  );
};
