import { useClinicalFileStore } from '@/stores/clinicalFileStore';
import { useUIStore } from '@/stores/uiStore';
import type { IntakeApproach } from '@/types';
import React from 'react';

const OPTIONS: { id: IntakeApproach; icon: string; title: string; desc: string; color: string }[] = [
  {
    id: 'crisis',
    icon: '🆘',
    title: 'Crisis / Immediate Support',
    desc: 'If you\'re in crisis or need immediate support, we can address what\'s urgent now and do formal assessment later.',
    color: 'border-red-300 bg-red-50 hover:bg-red-100',
  },
  {
    id: 'brief',
    icon: '👋',
    title: 'Brief Introduction — Quick Start',
    desc: 'A brief conversation where I learn the basics about what you\'re going through. More comprehensive assessment over time.',
    color: 'border-primary bg-primary/5 hover:bg-primary/10',
  },
  {
    id: 'structured',
    icon: '📋',
    title: 'Structured Intake — Full Assessment',
    desc: 'A thorough clinical assessment including history, symptoms, and validated screening questionnaires (PHQ-9, GAD-7).',
    color: 'border-secondary bg-secondary/5 hover:bg-secondary/10',
  },
];

export const IntakeSelection: React.FC = () => {
  const createFile = useClinicalFileStore((s) => s.createFile);
  const setView = useUIStore((s) => s.setView);
  const [name, setName] = React.useState('');
  const [step, setStep] = React.useState<'name' | 'approach'>('name');

  const handleSelect = (approach: IntakeApproach) => {
    createFile(name || 'Client', approach);
    setView('chat');
  };

  return (
    <div className="max-w-2xl mx-auto py-12 px-4">
      <div className="text-center mb-10">
        <span className="text-5xl mb-4 block">🧠</span>
        <h1 className="text-3xl font-semibold text-neutral-800 mb-2">Welcome to MindFlow</h1>
        <p className="text-neutral-500 leading-relaxed">
          I'm Dr. Alex Morgan, a clinical psychologist. Let's begin your journey to feeling better.
        </p>
      </div>

      {step === 'name' ? (
        <div className="bg-white rounded-2xl border border-neutral-200 p-8 shadow-sm animate-fade-in">
          <label className="block text-sm font-medium text-neutral-600 mb-2">
            What should I call you?
          </label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Your name or preferred name"
            className="w-full border border-neutral-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary mb-4"
            autoFocus
          />
          <button
            onClick={() => setStep('approach')}
            className="w-full py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark transition-colors"
          >
            Continue
          </button>
        </div>
      ) : (
        <div className="space-y-4 animate-fade-in">
          <p className="text-center text-sm text-neutral-500 mb-6">
            How would you like to start, {name || 'there'}?
          </p>
          {OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => handleSelect(opt.id)}
              className={`w-full text-left border-2 rounded-2xl p-5 transition-all ${opt.color}`}
            >
              <div className="flex items-start gap-4">
                <span className="text-3xl">{opt.icon}</span>
                <div>
                  <h3 className="font-semibold text-neutral-800 mb-1">{opt.title}</h3>
                  <p className="text-sm text-neutral-500 leading-relaxed">{opt.desc}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      <p className="text-center text-xs text-neutral-300 mt-8">
        Everything you share is stored locally on your device. Your privacy is paramount.
      </p>
    </div>
  );
};
