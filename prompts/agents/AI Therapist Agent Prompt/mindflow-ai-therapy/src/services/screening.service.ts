// ═══════════════════════════════════════════════════════════════
// Screening Service — Pure scoring functions
// ═══════════════════════════════════════════════════════════════

import type { GAD7Severity, PHQ9Severity, ScreenerType, ScreeningResult } from '@/types';

export function scorePHQ9(answers: number[]): { total: number; severity: PHQ9Severity; flagged: boolean } {
  const total = answers.reduce((a, b) => a + b, 0);
  const flagged = (answers[8] ?? 0) > 0; // Item 9 — suicidal ideation

  let severity: PHQ9Severity;
  if (total <= 4) severity = 'Minimal';
  else if (total <= 9) severity = 'Mild';
  else if (total <= 14) severity = 'Moderate';
  else if (total <= 19) severity = 'Moderately Severe';
  else severity = 'Severe';

  return { total, severity, flagged };
}

export function scoreGAD7(answers: number[]): { total: number; severity: GAD7Severity } {
  const total = answers.reduce((a, b) => a + b, 0);

  let severity: GAD7Severity;
  if (total <= 4) severity = 'Minimal';
  else if (total <= 9) severity = 'Mild';
  else if (total <= 14) severity = 'Moderate';
  else severity = 'Severe';

  return { total, severity };
}

export function interpretScore(type: ScreenerType, total: number): string {
  if (type === 'PHQ9') {
    if (total <= 4) return 'Your responses suggest minimal depression symptoms.';
    if (total <= 9) return 'Your responses suggest mild depression. Watchful waiting and lifestyle changes may be beneficial.';
    if (total <= 14) return 'Your responses suggest moderate depression. A treatment plan with therapy is recommended.';
    if (total <= 19) return 'Your responses suggest moderately severe depression. Active treatment with therapy and possibly medication is recommended.';
    return 'Your responses suggest severe depression. Immediate treatment with therapy and medication is strongly recommended.';
  }
  if (type === 'GAD7') {
    if (total <= 4) return 'Your responses suggest minimal anxiety symptoms.';
    if (total <= 9) return 'Your responses suggest mild anxiety. Monitoring and stress management may be helpful.';
    if (total <= 14) return 'Your responses suggest moderate anxiety. Therapeutic intervention is recommended.';
    return 'Your responses suggest severe anxiety. Active treatment with therapy and possibly medication is recommended.';
  }
  return 'Score recorded.';
}

export function createScreeningResult(
  type: ScreenerType,
  answers: number[],
): ScreeningResult {
  const id = crypto.randomUUID();
  const date = Date.now();

  if (type === 'PHQ9') {
    const { total, severity, flagged } = scorePHQ9(answers);
    return { id, type, date, answers, totalScore: total, severity, interpretation: interpretScore(type, total), flagged };
  }

  if (type === 'GAD7') {
    const { total, severity } = scoreGAD7(answers);
    return { id, type, date, answers, totalScore: total, severity, interpretation: interpretScore(type, total), flagged: false };
  }

  // ASRS — simple sum, no clinical severity bands in v1
  const total = answers.reduce((a, b) => a + b, 0);
  return { id, type, date, answers, totalScore: total, severity: total >= 14 ? 'Likely' : 'Unlikely', interpretation: interpretScore(type, total), flagged: false };
}
