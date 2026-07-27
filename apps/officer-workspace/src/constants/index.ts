export const CONFIDENCE = {
  HIGH_THRESHOLD: 0.85,
  MEDIUM_THRESHOLD: 0.6,
  HIGH_LABEL: 'High',
  MEDIUM_LABEL: 'Medium',
  LOW_LABEL: 'Low',
} as const;

export const MOCK_AUTH = {
  DEV_ROLE: 'Officer',
  DEV_BRANCH: 'Cawangan Ibu Pejabat',
  DEV_NAME: 'Pegawai MARA',
} as const;

export const API = {
  BASE_PATH: '/api',
  ENDPOINTS: {
    CREATE_ASSESSMENT: '/loans/assessments',
    SUBMIT_DECISION: (threadId: string) => `/loans/assessments/${threadId}/decision`,
  },
} as const;

export const UI = {
  DEFAULT_CONFIDENCE_THRESHOLD: 0.85,
  DEBOUNCE_MS: 300,
  TOAST_DURATION: 4000,
  LOCALE: 'en-MY',
  BRAND_ORANGE: '#F97316',
  BRAND_ORANGE_HOVER: '#EA580C',
  DEFAULT_SECTOR: 'general',
  DEFAULT_REGION: 'unknown',
  PLACEHOLDER_MOCK_FILE_NAME: 'document.pdf',
  ACCEPTED_FILE_TYPES: '.pdf,.doc,.docx,.png,.jpg,.jpeg',
  DATE_FORMAT_OPTIONS: { hour: '2-digit' as const, minute: '2-digit' as const },
  INPUT_BAR_HEIGHT: 58,
  BUTTON_DIMENSION: 42,
  ICON_BUTTON_DIMENSION: 9,
} as const;

export const WORKSPACE = {
  PAGE_TITLE: 'Officer Workspace',
  PAGE_SUBTITLE: 'Chat & task view',
  CHAT_HEADING: 'Workspace',
  CHAT_PLACEHOLDER: 'Describe your task — e.g. Assess the loan application from Ahmad bin Abdullah',
  FILE_ATTACH_TITLE: 'Attach file',
  VOICE_INPUT_TITLE: 'Voice input',
  SEND_MESSAGE_TITLE: 'Send message',
  TASK_HEADING: 'Tasks',
  CHIP_ACTIVE_LABEL: 'active',
  CHIP_AWAITING_LABEL: 'awaiting',
  TOAST_ASSESSMENT_STARTED: 'Assessment started',
  TOAST_ASSESSMENT_FAILED: 'Failed to start assessment',
  DOT_AGENT_COLOR: 'bg-emerald-500',
  FONT_XS_11: 'text-[11px]',
} as const;
