// ═══════════════════════════════════════════════════════════════
// Clinical File Store — Zustand + localStorage persistence
// ═══════════════════════════════════════════════════════════════

import type { ClinicalFile, IntakeApproach, ScreeningResult, TreatmentGoal } from '@/types';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ClinicalFileState {
  clinicalFile: ClinicalFile | null;
  createFile: (name: string, approach: IntakeApproach) => void;
  addScreeningResult: (result: ScreeningResult) => void;
  addTreatmentGoal: (goal: Omit<TreatmentGoal, 'id' | 'createdAt' | 'updatedAt'>) => void;
  updateGoalProgress: (goalId: string, progress: number) => void;
  updateDiagnosisNotes: (notes: string) => void;
  addPresentingProblem: (problem: string) => void;
  reset: () => void;
}

export const useClinicalFileStore = create<ClinicalFileState>()(
  persist(
    (set) => ({
      clinicalFile: null,

      createFile: (name, approach) =>
        set({
          clinicalFile: {
            id: crypto.randomUUID(),
            createdAt: Date.now(),
            updatedAt: Date.now(),
            profile: { name, createdAt: Date.now() },
            presentingProblems: [],
            intakeApproach: approach,
            screeningHistory: [],
            sessions: [],
            treatmentGoals: [],
            medications: [],
            diagnosisNotes: '',
          },
        }),

      addScreeningResult: (result) =>
        set((state) => {
          if (!state.clinicalFile) return state;
          return {
            clinicalFile: {
              ...state.clinicalFile,
              updatedAt: Date.now(),
              screeningHistory: [...state.clinicalFile.screeningHistory, result],
            },
          };
        }),

      addTreatmentGoal: (goal) =>
        set((state) => {
          if (!state.clinicalFile) return state;
          const newGoal: TreatmentGoal = {
            ...goal,
            id: crypto.randomUUID(),
            createdAt: Date.now(),
            updatedAt: Date.now(),
          };
          return {
            clinicalFile: {
              ...state.clinicalFile,
              updatedAt: Date.now(),
              treatmentGoals: [...state.clinicalFile.treatmentGoals, newGoal],
            },
          };
        }),

      updateGoalProgress: (goalId, progress) =>
        set((state) => {
          if (!state.clinicalFile) return state;
          return {
            clinicalFile: {
              ...state.clinicalFile,
              updatedAt: Date.now(),
              treatmentGoals: state.clinicalFile.treatmentGoals.map((g) =>
                g.id === goalId ? { ...g, progress, updatedAt: Date.now() } : g,
              ),
            },
          };
        }),

      updateDiagnosisNotes: (notes) =>
        set((state) => {
          if (!state.clinicalFile) return state;
          return {
            clinicalFile: { ...state.clinicalFile, updatedAt: Date.now(), diagnosisNotes: notes },
          };
        }),

      addPresentingProblem: (problem) =>
        set((state) => {
          if (!state.clinicalFile) return state;
          return {
            clinicalFile: {
              ...state.clinicalFile,
              updatedAt: Date.now(),
              presentingProblems: [...state.clinicalFile.presentingProblems, problem],
            },
          };
        }),

      reset: () => set({ clinicalFile: null }),
    }),
    { name: 'mindflow_clinical_file' },
  ),
);
