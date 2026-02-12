// ═══════════════════════════════════════════════════════════════
// App Constants
// ═══════════════════════════════════════════════════════════════

export const APP_NAME = 'MindFlow';
export const APP_VERSION = '1.0.0';

export const STORAGE_KEYS = {
  CLINICAL_FILE: 'mindflow_clinical_file',
  SETTINGS: 'mindflow_settings',
  SESSIONS: 'mindflow_sessions',
} as const;

export const DEFAULT_MODEL = 'claude-sonnet-4-20250514';

export const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';

// PHQ-9 Questions
export const PHQ9_QUESTIONS = [
  'Little interest or pleasure in doing things',
  'Feeling down, depressed, or hopeless',
  'Trouble falling or staying asleep, or sleeping too much',
  'Feeling tired or having little energy',
  'Poor appetite or overeating',
  'Feeling bad about yourself — or that you are a failure or have let yourself or your family down',
  'Trouble concentrating on things, such as reading the newspaper or watching television',
  'Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual',
  'Thoughts that you would be better off dead, or of hurting yourself in some way',
];

export const PHQ9_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
];

// GAD-7 Questions
export const GAD7_QUESTIONS = [
  'Feeling nervous, anxious, or on edge',
  'Not being able to stop or control worrying',
  'Worrying too much about different things',
  'Trouble relaxing',
  'Being so restless that it\'s hard to sit still',
  'Becoming easily annoyed or irritable',
  'Feeling afraid, as if something awful might happen',
];

export const GAD7_OPTIONS = [
  { value: 0, label: 'Not at all' },
  { value: 1, label: 'Several days' },
  { value: 2, label: 'More than half the days' },
  { value: 3, label: 'Nearly every day' },
];

// Crisis resources
export const CRISIS_RESOURCES = [
  { name: '988 Suicide & Crisis Lifeline', number: '988', type: 'call/text' },
  { name: 'Crisis Text Line', number: 'Text HOME to 741741', type: 'text' },
  { name: 'Emergency Services', number: '911', type: 'call' },
  { name: 'SAMHSA Helpline', number: '1-800-662-4357', type: 'call' },
];
