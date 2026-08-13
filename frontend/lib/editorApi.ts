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

export type ReplacementMethodClass = 'deterministic_edit' | 'prepared_asset' | 'generative_transform';
export type ReplacementAudioStrategy = 'preserve_source' | 'replacement_audio';

export interface ReplacementPlan {
  schema_version: number;
  edit_id: string;
  source_path: string;
  start_us: number;
  end_us: number;
  brief_sha256: string;
  method_class: ReplacementMethodClass;
  goal: string;
  required_changes: string[];
  allowed_changes: string[];
  forbidden_changes: string[];
  audio_strategy: ReplacementAudioStrategy;
  sample_policy: 'not_required' | 'required_before_full_generation';
  constraint_ids: string[];
  review_target_ids: string[];
}

export interface ReplacementCandidate {
  schema_version: number;
  candidate_id: string;
  edit_id: string;
  source_path: string;
  start_us: number;
  end_us: number;
  plan_sha256: string;
  method_class: ReplacementMethodClass;
  stage: 'sample' | 'full';
  artifact_id: string;
  artifact_path: string;
  execution_run_id: string | null;
}

export interface SampleApproval {
  edit_id: string;
  candidate_id: string;
  plan_sha256: string;
}

export type ReviewVerdict = 'approved' | 'rejected' | 'needs_revision';
export type ReviewOutcome = 'pass' | 'fail' | 'uncertain';
export type ReviewConfidence = 'low' | 'medium' | 'high';

export interface ReviewEvidenceReference {
  kind: 'brief_evidence' | 'candidate_artifact';
  ref_id: string;
}

export interface ReplacementReviewObservation {
  observation_id: string;
  kind: 'observation' | 'inference';
  statement: string;
  confidence: ReviewConfidence;
  evidence: ReviewEvidenceReference[];
}

export interface ReplacementReviewAssessment {
  target_id: string;
  outcome: ReviewOutcome;
  observation_ids: string[];
}

export interface ReplacementReview {
  schema_version: number;
  review_id: string;
  candidate_id: string;
  edit_id: string;
  source_path: string;
  start_us: number;
  end_us: number;
  plan_sha256: string;
  candidate_sha256: string;
  artifact_sha256: string;
  verdict: ReviewVerdict;
  observations: ReplacementReviewObservation[];
  assessments: ReplacementReviewAssessment[];
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
  artifacts: ProjectReference[];
  briefs: RangeContinuityBrief[];
  replacement_plans: ReplacementPlan[];
  replacement_candidates: ReplacementCandidate[];
  sample_approvals: SampleApproval[];
  replacement_reviews: ReplacementReview[];
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

export interface ReplacementPlanProposal {
  edit_id: string;
  method_class: ReplacementMethodClass;
  goal: string;
  required_changes: string[];
  allowed_changes?: string[];
  forbidden_changes?: string[];
  audio_strategy?: ReplacementAudioStrategy;
}

export interface CreateReplacementReviewInput {
  candidate_id: string;
  verdict: ReviewVerdict;
  observations: ReplacementReviewObservation[];
  assessments: ReplacementReviewAssessment[];
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

export function projectArtifactMediaUrl(projectId: string, artifactId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/media`;
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

export async function approveReplacementPlan(
  projectId: string,
  proposal: ReplacementPlanProposal,
): Promise<{ schema_version: number; plans: ReplacementPlan[] }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/replacement-plans/${encodeURIComponent(proposal.edit_id)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        allowed_changes: [],
        forbidden_changes: [],
        audio_strategy: 'preserve_source',
        ...proposal,
      }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось утвердить план замены');
  return response.json();
}

export async function prepareAssetReplacementCandidate(
  projectId: string,
  editId: string,
  sourcePath: string,
): Promise<{ candidate: ReplacementCandidate }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/replacement-candidates/prepared-asset`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ edit_id: editId, source_path: sourcePath }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подготовить candidate');
  return response.json();
}

export async function createReplacementReview(
  projectId: string,
  input: CreateReplacementReviewInput,
): Promise<ReplacementReview> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/replacement-reviews`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось сохранить проверку candidate');
  return response.json();
}

export async function acceptReplacementReview(
  projectId: string,
  reviewId: string,
): Promise<{ schema_version: number; edits: AcceptedRangeEdit[] }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/replacement-reviews/${encodeURIComponent(reviewId)}/accept`,
    { method: 'POST' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось принять проверенную замену');
  return response.json();
}
