// ═══════════════════════════════════════════════════════════════
// MindFlow Type System — Complete Domain Model
// ═══════════════════════════════════════════════════════════════

export type IntakeApproach = 'crisis' | 'brief' | 'structured';
export type MessageRole = 'user' | 'assistant';
export type ViewId = 'chat' | 'intake' | 'screening' | 'dashboard' | 'clinical-file' | 'settings' | 'export';
export type ScreenerType = 'PHQ9' | 'GAD7' | 'ASRS';

export type PHQ9Severity = 'Minimal' | 'Mild' | 'Moderate' | 'Moderately Severe' | 'Severe';
export type GAD7Severity = 'Minimal' | 'Mild' | 'Moderate' | 'Severe';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
}

export interface Session {
  id: string;
  number: number;
  startedAt: number;
  endedAt?: number;
  messages: Message[];
  moodRating?: number;
  sleepRating?: number;
  homework?: string;
  homeworkCompleted?: boolean;
  notes?: string;
}

export interface ScreeningResult {
  id: string;
  type: ScreenerType;
  date: number;
  answers: number[];
  totalScore: number;
  severity: string;
  interpretation: string;
  flagged: boolean; // PHQ-9 item 9 > 0
}

export interface TreatmentGoal {
  id: string;
  title: string;
  description: string;
  progress: number; // 0-100
  createdAt: number;
  updatedAt: number;
}

export interface ClinicalFile {
  id: string;
  createdAt: number;
  updatedAt: number;
  profile: UserProfile;
  presentingProblems: string[];
  intakeApproach: IntakeApproach;
  screeningHistory: ScreeningResult[];
  sessions: Session[];
  treatmentGoals: TreatmentGoal[];
  safetyPlan?: SafetyPlan;
  medications: string[];
  diagnosisNotes: string;
}

export interface UserProfile {
  name: string;
  age?: number;
  pronouns?: string;
  occupation?: string;
  emergencyContact?: string;
  createdAt: number;
}

export interface SafetyPlan {
  warningSignals: string[];
  copingStrategies: string[];
  peopleToCall: string[];
  professionalsToContact: string[];
  placesToGo: string[];
  environmentalSafety: string[];
  updatedAt: number;
}

export interface AppSettings {
  apiKey: string;
  modelId: string;
  darkMode: boolean;
}

// Screener question definitions
export interface ScreenerQuestion {
  id: number;
  text: string;
  options: { value: number; label: string }[];
}
