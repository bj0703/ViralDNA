import type { CreateJobResponse, IntentResponse, JobResult, JobViewModel, WorkbenchData } from '../types';

const DEFAULT_BASE_URL = '';

export function getApiBaseUrl() {
  return (import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchWorkbenchData(jobId: string, baseUrl = getApiBaseUrl()): Promise<WorkbenchData> {
  const [viewModel, rawResult] = await Promise.all([
    fetch(`${baseUrl}/sample-analysis/jobs/${jobId}/view-model`).then((response) =>
      parseJsonResponse<JobViewModel>(response),
    ),
    fetch(`${baseUrl}/sample-analysis/jobs/${jobId}/result`).then((response) =>
      parseJsonResponse<JobResult>(response),
    ),
  ]);

  return { viewModel, rawResult };
}

export async function uploadAnalysisJob(
  files: File[],
  sessionName: string,
  notesJson: string,
  baseUrl = getApiBaseUrl(),
): Promise<CreateJobResponse> {
  const formData = new FormData();

  files.forEach((file) => formData.append('files', file));
  if (sessionName.trim()) {
    formData.append('session_name', sessionName.trim());
  }
  if (notesJson.trim()) {
    formData.append('notes_json', notesJson.trim());
  }

  const response = await fetch(`${baseUrl}/sample-analysis/jobs`, {
    method: 'POST',
    body: formData,
  });
  return parseJsonResponse<CreateJobResponse>(response);
}

export async function detectIntent(text: string, targetVideoId?: string, baseUrl = getApiBaseUrl()): Promise<IntentResponse> {
  const response = await fetch(`${baseUrl}/sample-analysis/intent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      target_video_id: targetVideoId || null,
    }),
  });
  return parseJsonResponse<IntentResponse>(response);
}
