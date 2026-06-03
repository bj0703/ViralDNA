export type TimelineSegment = {
  segment_id: string;
  segment_type: 'script' | 'pace' | string;
  label: string;
  title: string;
  summary: string;
  start_seconds: number;
  end_seconds: number;
  confidence: number;
  status: string;
};

export type VideoViewModel = {
  sample_id: string;
  video: {
    filename: string;
    duration_seconds: number;
    preview_url: string | null;
  };
  timeline: TimelineSegment[];
  panels: {
    overview: {
      transcript_overview?: string | null;
      warnings?: string[];
      availability?: Record<string, string>;
    };
    script: {
      hook?: Record<string, unknown>;
      middle_segments?: Array<Record<string, unknown>>;
      ending?: Record<string, unknown>;
    };
    pace: {
      overall_pace?: string;
      shot_density_estimate?: number;
      highlight_position_seconds?: number;
      highlight_position_status?: string;
      segments?: Array<Record<string, unknown>>;
    };
    packaging_and_sound?: unknown;
    migration_suggestion?: unknown;
    risks?: string[];
  };
};

export type JobViewModel = {
  job_id: string;
  session_id: string;
  session_name?: string | null;
  status: string;
  video_count: number;
  videos: VideoViewModel[];
};

export type JobResult = {
  job_id: string;
  session_id: string;
  session_name?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  sample_results: Array<Record<string, unknown>>;
  debug: Record<string, unknown>;
};

export type CreateJobResponse = {
  job_id: string;
  session_id: string;
  status: string;
  sample_count: number;
};

export type IntentResponse = {
  intent: string;
  analysis_scope: string;
  target_video_id?: string | null;
  fallback_behavior: string;
  confidence: number;
  source: string;
  raw_model_output?: string | null;
  reason?: string | null;
};

export type WorkbenchData = {
  viewModel: JobViewModel;
  rawResult: JobResult;
};
