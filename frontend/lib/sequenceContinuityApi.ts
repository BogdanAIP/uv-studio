export type SequenceRuleCategory =
  | 'visual'
  | 'motion'
  | 'audio'
  | 'timing'
  | 'content'
  | 'technical'
  | 'style';

export type SequenceReviewOutcome = 'pass' | 'fail' | 'uncertain';
export type SequenceReviewVerdict = 'approved' | 'needs_revision' | 'rejected';

export interface SequenceContinuityRule {
  rule_id: string;
  category: SequenceRuleCategory;
  requirement: string;
}

export interface SequenceReviewTarget {
  target_id: string;
  criterion: string;
  required: boolean;
}

export interface SequenceObservation {
  observation_id: string;
  kind: 'observation' | 'inference';
  category: SequenceRuleCategory;
  statement: string;
  confidence: 'low' | 'medium' | 'high';
}

export interface SequenceReviewResult {
  target_id: string;
  outcome: SequenceReviewOutcome;
  note: string | null;
}

export interface SequenceShotPlan {
  shot_id: string;
  order: number;
  intent: string;
  anchor_take_id: string | null;
  anchor_take_sha256: string | null;
  locks: SequenceContinuityRule[];
  allowed_changes: SequenceContinuityRule[];
  review_targets: SequenceReviewTarget[];
  revision_sha256: string;
}

export interface SequenceTakeReview {
  review_id: string;
  take_id: string;
  shot_id: string;
  plan_revision_sha256: string;
  take_sha256: string;
  anchor_take_id: string | null;
  anchor_take_sha256: string | null;
  verdict: SequenceReviewVerdict;
  results: SequenceReviewResult[];
  observations: SequenceObservation[];
  note: string | null;
}

export interface SequenceTake {
  take_id: string;
  shot_id: string;
  reference_id: string;
  reference_path: string;
  reference_kind: 'source' | 'artifact';
  artifact_sha256: string;
  size_bytes: number;
  plan_revision_sha256: string;
  status: 'prepared' | 'accepted' | 'rejected';
  current_review_id: string | null;
}

export interface SequenceRecord {
  sequence_id: string;
  title: string;
  plans: SequenceShotPlan[];
  takes: SequenceTake[];
  reviews: SequenceTakeReview[];
  anchor_take_id: string | null;
}

export interface SequenceContinuityState {
  schema_version: number;
  sequences: SequenceRecord[];
}

export interface SequenceContextMedia {
  role: 'anchor' | 'candidate';
  take_id: string;
  reference_id: string;
  reference_kind: 'source' | 'artifact';
  reference_path: string;
  sha256: string;
  duration_us: number;
  window_start_us: number;
  window_end_us: number;
  sample_times_us: number[];
  observations?: SequenceObservation[];
}

export interface SequenceTimelineContext {
  sequence_id: string;
  shot_id: string;
  plan_revision_sha256: string;
  window_us: number;
  anchor: SequenceContextMedia | null;
  candidate: SequenceContextMedia;
  locks: SequenceContinuityRule[];
  allowed_changes: SequenceContinuityRule[];
  review_targets: SequenceReviewTarget[];
}

export type SequenceCommand =
  | {
      command: 'create_sequence';
      title: string;
      sequence_id?: string;
    }
  | {
      command: 'upsert_sequence_shot';
      sequence_id: string;
      shot_id: string;
      order: number;
      intent: string;
      anchor_take_id: string | null;
      locks: SequenceContinuityRule[];
      allowed_changes: SequenceContinuityRule[];
      review_targets: SequenceReviewTarget[];
    }
  | {
      command: 'register_sequence_take';
      sequence_id: string;
      shot_id: string;
      reference_id: string;
      take_id?: string;
    }
  | {
      command: 'review_sequence_take';
      sequence_id: string;
      take_id: string;
      verdict: SequenceReviewVerdict;
      results: SequenceReviewResult[];
      observations: SequenceObservation[];
      note: string | null;
    }
  | {
      command: 'accept_sequence_take';
      sequence_id: string;
      review_id: string;
    }
  | {
      command: 'reanchor_sequence';
      sequence_id: string;
      take_id: string;
    };

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getSequenceState(projectId: string): Promise<SequenceContinuityState> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sequence/state`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить состояние последовательности');
  return response.json();
}

export async function executeSequenceCommand<T>(
  projectId: string,
  command: SequenceCommand,
): Promise<{ command: SequenceCommand['command']; payload: T }> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sequence/commands`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось выполнить команду последовательности');
  return response.json();
}

export async function getSequenceTimelineContext(
  projectId: string,
  sequenceId: string,
  takeId: string,
  options: { windowUs?: number; samples?: number } = {},
): Promise<SequenceTimelineContext> {
  const query = new URLSearchParams();
  if (options.windowUs !== undefined) query.set('window_us', String(options.windowUs));
  if (options.samples !== undefined) query.set('samples', String(options.samples));
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sequence/${encodeURIComponent(sequenceId)}/takes/${encodeURIComponent(takeId)}/context${suffix}`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось получить контекст границы');
  return response.json();
}

export function sequenceMediaUrl(
  projectId: string,
  media: Pick<SequenceContextMedia, 'reference_kind' | 'reference_id'>,
): string {
  const collection = media.reference_kind === 'source' ? 'sources' : 'artifacts';
  return `/api/uv/projects/${encodeURIComponent(projectId)}/${collection}/${encodeURIComponent(media.reference_id)}/media`;
}
