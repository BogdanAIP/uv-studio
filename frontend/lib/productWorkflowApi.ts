import type { CapabilityVideoEnvelope } from '@/lib/renderApi';
import type { PhotoToVideoResult } from '@/lib/stage8MediaApi';

export type WorkflowReadiness = 'ready' | 'setup_required' | 'partial' | 'unavailable';

export interface WorkflowPrerequisite {
  prerequisite_id: string;
  title: string;
  explanation: string;
  satisfied: boolean;
  resolution: string | null;
}

export interface WorkflowWorkspace {
  workspace_id: string;
  title: string;
  description: string;
}

export interface WorkflowAction {
  action_id: string;
  title: string;
  explanation: string;
  enabled: boolean;
  blocked_by: string[];
  prerequisite_ids: string[];
  input_schema: Record<string, unknown>;
  suggested_input: Record<string, unknown>;
  execution_class: string;
  authorization_class: string;
  capability_id: string;
  expected_result: string;
}

export interface WorkflowArtifact {
  artifact_id: string;
  kind: string;
  path: string;
  lifecycle: string;
  metadata: Record<string, unknown>;
}

export interface WorkflowDiagnostic {
  code: string;
  severity: string;
  message: string;
}

export interface ProjectWorkflowState {
  schema_version: number;
  project_id: string;
  recipe_id: string;
  recipe_title: string;
  readiness: WorkflowReadiness;
  summary: string;
  current_outcome: WorkflowArtifact | null;
  prerequisites: WorkflowPrerequisite[];
  relevant_workspaces: WorkflowWorkspace[];
  next_actions: WorkflowAction[];
  active_jobs: Array<Record<string, unknown>>;
  user_decisions: Array<Record<string, unknown>>;
  recent_artifacts: WorkflowArtifact[];
  diagnostics: WorkflowDiagnostic[];
}

export interface ComposePhotosActionInput {
  image_source_ids: string[];
  duration_per_image_us?: number;
  audio_source_id?: string;
}

export interface ComposePhotosActionResponse {
  schema_version: number;
  action_id: 'compose_photos';
  execution: CapabilityVideoEnvelope<PhotoToVideoResult>;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getProjectWorkflow(projectId: string): Promise<ProjectWorkflowState> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/workflow`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить состояние процесса');
  return response.json();
}

export async function executeComposePhotosAction(
  projectId: string,
  input: ComposePhotosActionInput,
): Promise<ComposePhotosActionResponse> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/workflow/actions/compose_photos`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось собрать видео из фотографий');
  return response.json();
}
