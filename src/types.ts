export interface MicroStep {
  step_id: number;
  title: string;
  description: string;
  duration_minutes: number;
  completed?: boolean;
}

export interface AnalysisResponse {
  empathy_response: string;
  detected_emotion: string; // e.g. Anxious, Burnout, Confused, Demotivated, Overwhelmed
  energy_level_required: string; // Low, Medium, High
  micro_steps: MicroStep[];
}

export interface HistorySession {
  id: string;
  timestamp: string; // ISO String
  original_curhatan: string;
  contextHistory?: string;
  empathy_response: string;
  detected_emotion: string;
  energy_level_required: string;
  micro_steps: MicroStep[];
}
