export interface ScoringRunRequest {
  tenant_id: string;
  jwt_token: string;
  environment: string;
  summary_template: string;
  experience_id?: string;
}

export interface ScoringRunAccepted {
  job_id: string;
  status: string;
  tenant_id: string;
}

export interface CallRationale {
  accuracy: string;
  information_capture: string;
  context_adherence: string;
}

export interface CallScoreResult {
  call_id: string;
  call_end_time: string | null;
  summary_present: boolean;
  accuracy: number | null;
  information_capture: number | null;
  context_adherence: number | null;
  composite_score: number | null;
  status: 'scored' | 'no_summary' | 'unscored' | 'empty_transcript';
  rationale: CallRationale | null;
}

export interface ScoringJobResult {
  job_id: string;
  tenant_id: string;
  status: 'processing' | 'completed' | 'failed';
  overall_score: number | null;
  window_start: string | null;
  window_end: string | null;
  calls_scored: number;
  calls_missing_summary: number;
  calls_unscored: number;
  computed_at: string | null;
  calls: CallScoreResult[];
  error: string | null;
}
