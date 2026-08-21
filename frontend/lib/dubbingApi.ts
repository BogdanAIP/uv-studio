import type { ProjectReference } from './projectsApi';
import type { CapabilityVideoEnvelope, CapabilityVideoResult } from './renderApi';
import { executeProjectWorkflowAction } from './productWorkflowApi';

export interface DubbingTranscriptSegment {
  segment_id: string;
  start_us: number;
  end_us: number;
  text: string;
  speaker_label: string | null;
  confidence: number | null;
}

export interface DubbingTranscript {
  schema_version: number;
  dubbing_id: string;
  source_id: string;
  source_sha256: string;
  language: string;
  start_us: number;
  end_us: number;
  origin: 'imported' | 'asr';
  segments: DubbingTranscriptSegment[];
}

export interface DubbingTranslationSegment {
  segment_id: string;
  text: string;
}

export interface DubbingTranslation {
  schema_version: number;
  translation_id: string;
  dubbing_id: string;
  transcript_sha256: string;
  target_language: string;
  segments: DubbingTranslationSegment[];
}

export interface DubbingState {
  schema_version: number;
  transcripts: DubbingTranscript[];
  translations: DubbingTranslation[];
}

export interface PreparedSpeechTake {
  schema_version: number;
  take_id: string;
  dubbing_id: string;
  script_kind: 'transcript' | 'translation';
  script_id: string;
  script_sha256: string;
  audio_id: string;
  audio_sha256: string;
  duration_us: number;
  origin: 'imported' | 'recorded' | 'tts';
  segment_id: string | null;
}

export interface PreparedSpeechState {
  schema_version: number;
  takes: PreparedSpeechTake[];
}

export interface DubbingLoudnessEvidence {
  audio_id: string;
  audio_sha256: string;
  duration_us: number;
  measurable: boolean;
  integrated_lufs: number | null;
  true_peak_dbtp: number | null;
  loudness_range_lu: number | null;
  threshold_lufs: number | null;
}

export interface DubbingReview extends Record<string, unknown> {
  schema_version: number;
  review_id: string;
  take_id: string;
  take_sha256: string;
  dubbing_id: string;
  source_id: string;
  source_sha256: string;
  script_kind: 'transcript' | 'translation';
  script_id: string;
  script_sha256: string;
  audio_id: string;
  audio_sha256: string;
  segment_id: string | null;
  target_start_us: number;
  target_end_us: number;
  audio_duration_us: number;
  timing_delta_us: number;
  timing_pass: boolean;
  loudness: DubbingLoudnessEvidence;
  audio_safety_pass: boolean;
  content_fidelity_confirmed: boolean;
  synchronization_confirmed: boolean;
  verdict: 'approved' | 'rejected' | 'needs_revision';
  note: string | null;
}

export interface AcceptedDubbingEdit {
  schema_version: number;
  accepted_id: string;
  review_id: string;
  take_id: string;
  take_sha256: string;
  dubbing_id: string;
  source_id: string;
  source_sha256: string;
  target_start_us: number;
  target_end_us: number;
  script_kind: 'transcript' | 'translation';
  script_id: string;
  script_sha256: string;
  audio_id: string;
  audio_sha256: string;
  segment_id: string | null;
  composition_policy:
    | 'replace_source_audio_range'
    | 'duck_source_mix'
    | 'replace_dialogue_preserve_background';
}

export interface DubbingEditorState {
  sources: ProjectReference[];
  artifacts: ProjectReference[];
  prepared_audio: ProjectReference[];
  dubbing: DubbingState;
  prepared_speech: PreparedSpeechState;
  dubbing_reviews: DubbingReview[];
  accepted_dubbing: AcceptedDubbingEdit[];
}

export interface CurrentDubbingReviews {
  current_by_take: Record<string, string>;
  ambiguous_legacy_take_ids: string[];
}

export interface AsrDraft {
  source_id: string;
  source_sha256: string;
  language: string;
  start_us: number;
  end_us: number;
  segments: DubbingTranscriptSegment[];
}

interface CapabilityEnvelope<T> {
  selection: Record<string, unknown>;
  result: {
    schema_version: number;
    project_id: string;
    capability_id: string;
    offer_id: string;
    adapter_id: string;
    output: T;
    artifact: ProjectReference | null;
  };
}

export interface DubbingRenderOutput {
  path: string;
  source_id: string;
  visual_edit_ids: string[];
  accepted_dubbing_ids: string[];
  composition_mode: string;
  time_mapping_mode: string;
  actual_output_video_duration_us: number;
  actual_output_audio_duration_us: number;
}

export interface DubbingRenderResult extends CapabilityVideoResult {
  capability_id: 'video.render_dubbing';
  output: DubbingRenderOutput & Record<string, unknown>;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

async function editorCommand<T>(projectId: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/editor/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw await apiError(response, 'Команда дубляжа не выполнена');
  return response.json();
}

async function orchestratedDomain<T>(
  projectId: string,
  actionId: string,
  input: Record<string, unknown>,
): Promise<T> {
  const response = await executeProjectWorkflowAction<T>(projectId, actionId, input);
  if (!('result' in response)) throw new Error(`${actionId}: ожидался semantic domain result`);
  return response.result;
}

async function orchestratedCapability<T>(
  projectId: string,
  actionId: string,
  input: Record<string, unknown>,
): Promise<T> {
  const response = await executeProjectWorkflowAction<T>(projectId, actionId, input);
  if (!('execution' in response)) throw new Error(`${actionId}: ожидался capability execution result`);
  return response.execution;
}

export async function getCurrentDubbingReviews(projectId: string): Promise<CurrentDubbingReviews> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/dubbing-reviews/current`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось определить текущий Review');
  return response.json();
}

export async function getDubbingEditorState(projectId: string): Promise<DubbingEditorState> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/editor/state`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить состояние дубляжа');
  const state: DubbingEditorState = await response.json();
  const current = await getCurrentDubbingReviews(projectId);
  const ambiguous = new Set(current.ambiguous_legacy_take_ids);
  return {
    ...state,
    dubbing_reviews: state.dubbing_reviews.filter(review => {
      if (ambiguous.has(review.take_id)) return false;
      return current.current_by_take[review.take_id] === review.review_id;
    }),
  };
}

export async function transcribeProjectSource(
  projectId: string,
  input: { source_id: string; start_us?: number; end_us?: number; language?: string },
  orchestrated = false,
): Promise<AsrDraft> {
  if (orchestrated) {
    const envelope = await orchestratedCapability<CapabilityEnvelope<AsrDraft>>(
      projectId,
      'transcribe_dubbing_source',
      input,
    );
    return envelope.result.output;
  }
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/speech.transcribe/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selection_policy: 'local_free_first', input }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Локальное распознавание речи недоступно');
  const envelope: CapabilityEnvelope<AsrDraft> = await response.json();
  return envelope.result.output;
}

export async function acceptAsrTranscript(
  projectId: string,
  draft: AsrDraft,
  orchestrated = false,
): Promise<{ command: 'accept_asr_transcript'; dubbing_id: string; payload: { transcript: DubbingTranscript } }> {
  const input = {
    source_id: draft.source_id,
    language: draft.language,
    start_us: draft.start_us,
    end_us: draft.end_us,
    segments: draft.segments,
  };
  if (orchestrated) return orchestratedDomain(projectId, 'accept_asr_transcript', input);
  return editorCommand(projectId, { command: 'accept_asr_transcript', ...input });
}

export async function saveDubbingTranslation(
  projectId: string,
  input: {
    dubbing_id: string;
    target_language: string;
    segments: DubbingTranslationSegment[];
    translation_id?: string;
  },
  orchestrated = false,
): Promise<{ command: 'upsert_dubbing_translation'; dubbing_id: string; payload: { translation: DubbingTranslation } }> {
  let safeInput = input;
  if (input.translation_id) {
    const state = await getDubbingEditorState(projectId);
    const existing = state.dubbing.translations.find(item => item.translation_id === input.translation_id);
    if (!existing || existing.dubbing_id !== input.dubbing_id || existing.target_language !== input.target_language.trim().toLowerCase()) {
      const { translation_id: _ignored, ...withoutIdentity } = input;
      safeInput = withoutIdentity;
    }
  }
  if (orchestrated) {
    return orchestratedDomain(projectId, 'save_dubbing_translation', safeInput as unknown as Record<string, unknown>);
  }
  return editorCommand(projectId, { command: 'upsert_dubbing_translation', ...safeInput });
}

export async function uploadPreparedAudio(
  projectId: string,
  file: File,
  origin: 'imported' | 'recorded' = 'imported',
): Promise<ProjectReference> {
  const query = new URLSearchParams({ filename: file.name, origin });
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/prepared-audio?${query.toString()}`,
    {
      method: 'POST',
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      body: file,
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось импортировать речевую дорожку');
  return response.json();
}

export function preparedAudioMediaUrl(projectId: string, audioId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/prepared-audio/${encodeURIComponent(audioId)}/media`;
}

export async function attachPreparedSpeech(
  projectId: string,
  input: {
    dubbing_id: string;
    audio_id: string;
    translation_id?: string;
    segment_id?: string;
  },
  orchestrated = false,
): Promise<{ command: 'attach_prepared_speech'; dubbing_id: string; payload: { prepared_speech: PreparedSpeechTake } }> {
  if (orchestrated) {
    return orchestratedDomain(projectId, 'attach_prepared_speech', input as unknown as Record<string, unknown>);
  }
  return editorCommand(projectId, { command: 'attach_prepared_speech', ...input });
}

export async function reviewPreparedSpeech(
  projectId: string,
  input: {
    take_id: string;
    verdict: 'approved' | 'rejected' | 'needs_revision';
    content_fidelity_confirmed: boolean;
    synchronization_confirmed: boolean;
    note?: string;
  },
  orchestrated = false,
): Promise<{ command: 'review_prepared_speech'; payload: { review: DubbingReview; current_review_id: string } }> {
  if (orchestrated) {
    return orchestratedDomain(projectId, 'review_prepared_speech', input as unknown as Record<string, unknown>);
  }
  return editorCommand(projectId, { command: 'review_prepared_speech', ...input });
}

export async function acceptDubbingReview(
  projectId: string,
  reviewId: string,
  orchestrated = false,
): Promise<{ command: 'accept_dubbing_review'; payload: { accepted_dubbing: AcceptedDubbingEdit } }> {
  if (orchestrated) {
    return orchestratedDomain(projectId, 'accept_dubbing_review', { review_id: reviewId });
  }
  return editorCommand(projectId, {
    command: 'accept_dubbing_review',
    review_id: reviewId,
    composition_policy: 'replace_source_audio_range',
  });
}

export async function renderAcceptedDubbing(
  projectId: string,
  sourceId: string,
  orchestrated = false,
): Promise<CapabilityVideoEnvelope<DubbingRenderResult>> {
  if (orchestrated) {
    return orchestratedCapability<CapabilityVideoEnvelope<DubbingRenderResult>>(
      projectId,
      'render_accepted_dubbing',
      { source_id: sourceId },
    );
  }
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.render_dubbing/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selection_policy: 'local_free_first', input: { source_id: sourceId } }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось собрать мастер с дубляжом');
  return response.json();
}
