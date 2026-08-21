import type { CapabilityVideoEnvelope } from '@/lib/renderApi';
import type { PhotoToVideoResult, VisualizerResult } from '@/lib/stage8MediaApi';

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
  capability_id: string | null;
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

export interface WorkflowDomainActionResponse<TResult = Record<string, unknown>> {
  schema_version: number;
  action_id: string;
  result: TResult;
}

export interface WorkflowCapabilityActionResponse<TResult = Record<string, unknown>> {
  schema_version: number;
  action_id: string;
  execution: TResult;
}

export type WorkflowActionResponse<TResult = Record<string, unknown>> =
  | WorkflowDomainActionResponse<TResult>
  | WorkflowCapabilityActionResponse<TResult>;

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

export interface RenderVisualizerActionInput {
  audio_source_id: string;
  artwork_source_id?: string;
}

export interface RenderVisualizerActionResponse {
  schema_version: number;
  action_id: 'render_visualizer';
  execution: CapabilityVideoEnvelope<VisualizerResult>;
}

const TARGETED_EDIT_COMPAT_ACTIONS = new Set([
  'select_target_range',
  'prepare_replacement',
  'review_replacement',
  'accept_replacement',
  'render_accepted_edits',
]);

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

async function jsonOrError<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) throw await apiError(response, fallback);
  return response.json();
}

function requiredString(input: Record<string, unknown>, key: string): string {
  const value = input[key];
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`Legacy targeted-edit compatibility input is missing ${key}`);
  }
  return value.trim();
}

function recordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    : [];
}

function requestedChangeFromBrief(brief: Record<string, unknown>): string {
  const constraints = recordArray(brief.constraints);
  const requested = constraints.find(item => item.constraint_id === 'requested_change') ?? constraints[0];
  const requirement = requested?.requirement;
  if (typeof requirement !== 'string' || !requirement.trim()) {
    throw new Error('Legacy targeted-edit compatibility could not resolve the requested change');
  }
  return requirement.trim();
}

async function executeLegacyTargetedAction<TResult>(
  projectId: string,
  actionId: string,
  input: Record<string, unknown>,
): Promise<WorkflowActionResponse<TResult>> {
  const encodedProjectId = encodeURIComponent(projectId);

  if (actionId === 'select_target_range') {
    const response = await fetch(`/api/uv/projects/${encodedProjectId}/editor/commands`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: 'select_range', ...input }),
    });
    const result = await jsonOrError<TResult>(response, 'Не удалось подготовить выбранный диапазон');
    return { schema_version: 1, action_id: actionId, result };
  }

  if (actionId === 'prepare_replacement') {
    const editId = requiredString(input, 'edit_id');
    const replacementSourceId = requiredString(input, 'replacement_source_id');
    const editorState = await jsonOrError<Record<string, unknown>>(
      await fetch(`/api/uv/projects/${encodedProjectId}/editor/state`, { cache: 'no-store' }),
      'Не удалось прочитать текущее состояние редактора',
    );
    const brief = recordArray(editorState.briefs).find(item => item.edit_id === editId);
    const replacement = recordArray(editorState.sources).find(item => item.id === replacementSourceId);
    if (!brief || !replacement) {
      throw new Error('Текущий Brief или выбранный клип больше не существует в проекте');
    }
    const sourcePath = replacement.path;
    if (typeof sourcePath !== 'string' || !sourcePath) {
      throw new Error('Выбранный клип не имеет project-owned source path');
    }
    const change = requestedChangeFromBrief(brief);
    const planState = await jsonOrError<Record<string, unknown>>(
      await fetch(
        `/api/uv/projects/${encodedProjectId}/replacement-plans/${encodeURIComponent(editId)}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            edit_id: editId,
            method_class: 'prepared_asset',
            goal: change,
            required_changes: [change],
            allowed_changes: [],
            forbidden_changes: ['Не изменять исходное видео вне выбранного диапазона.'],
            audio_strategy: 'preserve_source',
          }),
        },
      ),
      'Не удалось утвердить план замены',
    );
    const plan = recordArray(planState.plans).find(item => item.edit_id === editId);
    if (!plan) throw new Error('Утверждённый план не найден в текущем состоянии проекта');

    const candidateEnvelope = await jsonOrError<Record<string, unknown>>(
      await fetch(`/api/uv/projects/${encodedProjectId}/replacement-candidates/prepared-asset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ edit_id: editId, source_path: sourcePath }),
      }),
      'Не удалось подготовить вариант замены',
    );
    const candidate = candidateEnvelope.candidate;
    if (!candidate || typeof candidate !== 'object') {
      throw new Error('Подготовка замены завершилась без candidate');
    }
    return {
      schema_version: 1,
      action_id: actionId,
      result: { plan, candidate } as TResult,
    };
  }

  if (actionId === 'review_replacement') {
    const response = await fetch(`/api/uv/projects/${encodedProjectId}/replacement-reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    const result = await jsonOrError<TResult>(response, 'Не удалось сохранить проверку варианта');
    return { schema_version: 1, action_id: actionId, result };
  }

  if (actionId === 'accept_replacement') {
    const reviewId = requiredString(input, 'review_id');
    const response = await fetch(
      `/api/uv/projects/${encodedProjectId}/replacement-reviews/${encodeURIComponent(reviewId)}/accept`,
      { method: 'POST' },
    );
    const result = await jsonOrError<TResult>(response, 'Не удалось принять проверенную замену');
    return { schema_version: 1, action_id: actionId, result };
  }

  if (actionId === 'render_accepted_edits') {
    const response = await fetch(
      `/api/uv/projects/${encodedProjectId}/capabilities/video.render_edits/execute`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input }),
      },
    );
    const execution = await jsonOrError<TResult>(response, 'Не удалось собрать мастер-рендер');
    return { schema_version: 1, action_id: actionId, execution };
  }

  throw new Error(`Legacy targeted-edit compatibility does not support ${actionId}`);
}

export async function getProjectWorkflow(projectId: string): Promise<ProjectWorkflowState> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/workflow`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить состояние процесса');
  return response.json();
}

async function isExplicitlyUnmigratedTargetedSurface(projectId: string): Promise<boolean> {
  const state = await getProjectWorkflow(projectId);
  const hasTargetedWorkspace = state.relevant_workspaces.some(
    workspace => workspace.workspace_id === 'targeted_edit',
  );
  const explicitlyUnmigrated = state.diagnostics.some(
    diagnostic => diagnostic.code === 'workflow_not_migrated',
  );
  return !hasTargetedWorkspace && explicitlyUnmigrated;
}

export async function executeProjectWorkflowAction<TResult = Record<string, unknown>>(
  projectId: string,
  actionId: string,
  input: Record<string, unknown>,
): Promise<WorkflowActionResponse<TResult>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/workflow/actions/${encodeURIComponent(actionId)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  );
  if (response.ok) return response.json();

  // Migration-only compatibility: only an explicitly non-migrated recipe may fall back to the
  // established UV-owned editor domains. A migrated targeted workflow always fails closed here,
  // so a broken/missing Orchestrator action cannot be hidden by legacy behavior.
  if (
    response.status === 404
    && TARGETED_EDIT_COMPAT_ACTIONS.has(actionId)
    && await isExplicitlyUnmigratedTargetedSurface(projectId)
  ) {
    return executeLegacyTargetedAction<TResult>(projectId, actionId, input);
  }
  throw await apiError(response, 'Не удалось выполнить следующее действие проекта');
}

export async function executeComposePhotosAction(
  projectId: string,
  input: ComposePhotosActionInput,
): Promise<ComposePhotosActionResponse> {
  return executeProjectWorkflowAction<CapabilityVideoEnvelope<PhotoToVideoResult>>(
    projectId,
    'compose_photos',
    input as unknown as Record<string, unknown>,
  ) as Promise<ComposePhotosActionResponse>;
}

export async function executeRenderVisualizerAction(
  projectId: string,
  input: RenderVisualizerActionInput,
): Promise<RenderVisualizerActionResponse> {
  return executeProjectWorkflowAction<CapabilityVideoEnvelope<VisualizerResult>>(
    projectId,
    'render_visualizer',
    input as unknown as Record<string, unknown>,
  ) as Promise<RenderVisualizerActionResponse>;
}
