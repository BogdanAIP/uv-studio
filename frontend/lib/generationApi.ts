export type GenerationStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export interface NamedModelExecution {
  adapter_id: string;
  availability: 'available' | 'configuration_required' | 'unavailable';
  reason: string;
  locality: 'local' | 'remote' | 'hybrid';
  cost_class: 'free' | 'potentially_paid' | 'paid';
  asynchronous: boolean;
}

export interface NamedModel {
  schema_version: number;
  model_id: string;
  title: string;
  description: string;
  capability_id: string;
  offer_id: string;
  output_kind: 'text' | 'image' | 'video' | 'audio';
  execution: NamedModelExecution;
}

export interface GenerationContract {
  schema_version?: number;
  fixed_constraints: string[];
  editable_variables: string[];
  forbidden_changes: string[];
  approved_reference_id?: string | null;
}

export interface GenerationAttempt {
  attempt_id: string;
  retry_index: number;
  status: Exclude<GenerationStatus, 'queued'>;
  started_at: string;
  ended_at: string | null;
  output_reference_id: string | null;
  take_id: string | null;
  error: string | null;
}

export interface GenerationJobRequest {
  project_id: string;
  shot_id: string;
  model_id: string;
  execution_mapping: {
    capability_id: string;
    offer_id: string;
    adapter_id: string;
  };
  inputs: Record<string, unknown>;
  generation_contract: GenerationContract;
}

export interface GenerationJob {
  record_type: 'generation_job';
  schema_version: number;
  job_id: string;
  project_id: string;
  idempotency_key: string;
  request_digest: string;
  request: GenerationJobRequest;
  status: GenerationStatus;
  created_at: string;
  updated_at: string;
  attempts: GenerationAttempt[];
}

export interface GenerationPreparation {
  model: NamedModel;
  request_digest: string;
  request: GenerationJobRequest;
  authorization: {
    schema_version: number;
    locality: string;
    cost_class: string;
    cost_estimate: Record<string, unknown>;
    consent_required: string[];
    authorization_required: boolean;
  };
}

interface GenerationRequestBase {
  shot_id: string;
  model_id: string;
  inputs: Record<string, unknown>;
  contract: GenerationContract;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail?.message && typeof detail.message === 'string') return new Error(detail.message);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function listNamedModels(): Promise<NamedModel[]> {
  const response = await fetch('/api/uv/models', { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить список моделей');
  return response.json();
}

export async function prepareGeneration(
  projectId: string,
  request: GenerationRequestBase,
): Promise<GenerationPreparation> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/prepare`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подготовить генерацию');
  return response.json();
}

export async function authorizeGeneration(
  projectId: string,
  request: GenerationRequestBase,
  acknowledgements: string[],
): Promise<{ authorization_token: string | null }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/authorize`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...request, acknowledgements }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подтвердить запуск модели');
  return response.json();
}

export async function submitGeneration(
  projectId: string,
  request: GenerationRequestBase & { idempotency_key: string; authorization_token?: string | null },
): Promise<{ reused: boolean; job: GenerationJob }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось поставить генерацию в очередь');
  return response.json();
}

export async function listGenerationJobs(projectId: string): Promise<GenerationJob[]> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить историю генерации');
  return response.json();
}

export async function getGenerationJob(projectId: string, jobId: string): Promise<GenerationJob> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs/${encodeURIComponent(jobId)}`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось получить состояние генерации');
  return response.json();
}

export async function cancelGeneration(projectId: string, jobId: string): Promise<GenerationJob> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs/${encodeURIComponent(jobId)}/cancel`,
    { method: 'POST' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось отменить генерацию');
  return response.json();
}

export async function prepareGenerationRetry(
  projectId: string,
  jobId: string,
): Promise<{ job: GenerationJob; authorization: GenerationPreparation['authorization'] }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs/${encodeURIComponent(jobId)}/prepare-retry`,
    { method: 'POST' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подготовить повторный запуск');
  return response.json();
}

export async function retryGeneration(
  projectId: string,
  jobId: string,
  authorizationToken: string | null,
): Promise<GenerationJob> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/generation/jobs/${encodeURIComponent(jobId)}/retry`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ authorization_token: authorizationToken }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось повторить генерацию');
  return response.json();
}
