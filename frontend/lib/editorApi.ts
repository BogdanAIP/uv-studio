import type { ProjectReference } from './projectsApi';

export interface ContinuityEvidence {
  evidence_id: string;
  role: 'before' | 'requested' | 'after' | 'reference';
  path: string;
  source_start_us: number | null;
  source_end_us: number | null;
}

export interface ContinuityConstraint {
  constraint_id: string;
  category: string;
  requirement: string;
  evidence_ids: string[];
}

export interface ReviewTarget {
  target_id: string;
  criterion: string;
  required: boolean;
  evidence_ids: string[];
}

export interface RangeContinuityBrief {
  schema_version: number;
  edit_id: string;
  source_path: string;
  start_us: number;
  end_us: number;
  evidence: ContinuityEvidence[];
  mechanical_facts: Array<Record<string, unknown>>;
  observations: Array<Record<string, unknown>>;
  constraints: ContinuityConstraint[];
  review_targets: ReviewTarget[];
}

export interface AcceptedRangeEdit {
  edit_id: string;
  source_path: string;
  start_us: number;
  end_us: number;
  replacement_path: string;
}

export interface EditorState {
  sources: ProjectReference[];
  briefs: RangeContinuityBrief[];
  accepted_edits: AcceptedRangeEdit[];
}

export interface ResolvedProjectMediaRange {
  source_path: string;
  source_duration_us: number;
  requested: {
    start_us: number;
    end_us: number;
    duration_us: number;
  };
  context: {
    requested_before_us: number;
    requested_after_us: number;
    start_us: number;
    end_us: number;
    before_duration_us: number;
    after_duration_us: number;
  };
}

export interface SelectRangeInput {
  source_id: string;
  start_us: number;
  end_us: number;
  change_request: string;
  context_before_us?: number;
  context_after_us?: number;
}

export interface SelectRangeResult {
  command: 'select_range';
  source_id: string;
  edit_id: string;
  resolved_range: ResolvedProjectMediaRange;
  brief: RangeContinuityBrief;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getEditorState(projectId: string): Promise<EditorState> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/editor/state`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить состояние редактора');
  return response.json();
}

export async function uploadProjectSource(
  projectId: string,
  file: File,
): Promise<ProjectReference> {
  const query = new URLSearchParams({ filename: file.name });
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sources?${query.toString()}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
      },
      body: file,
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось импортировать видео');
  return response.json();
}

export function projectSourceMediaUrl(projectId: string, sourceId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}/media`;
}

export async function selectProjectRange(
  projectId: string,
  input: SelectRangeInput,
): Promise<SelectRangeResult> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/editor/commands`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: 'select_range',
        ...input,
      }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подготовить выбранный диапазон');
  return response.json();
}
