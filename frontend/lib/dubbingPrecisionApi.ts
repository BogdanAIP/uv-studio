import type { ProjectReference } from './projectsApi';
import type {
  DubbingTranslation,
  DubbingTranslationSegment,
  PreparedSpeechTake,
} from './dubbingApi';

export interface TranslationDraft {
  source_language: string;
  target_language: string;
  segments: DubbingTranslationSegment[];
}

export interface AlignmentMark {
  mark_id: string;
  unit: 'word' | 'token' | 'phoneme';
  text: string;
  audio_start_us: number;
  audio_end_us: number;
  confidence: number | null;
}

export interface AlignmentDraft {
  take_id: string;
  language: string;
  marks: AlignmentMark[];
}

export interface DubbingAlignment {
  schema_version: number;
  alignment_id: string;
  take_id: string;
  take_sha256: string;
  dubbing_id: string;
  script_kind: 'transcript' | 'translation';
  script_id: string;
  script_sha256: string;
  audio_id: string;
  audio_sha256: string;
  language: string;
  segment_id: string | null;
  target_start_us: number;
  target_end_us: number;
  marks: AlignmentMark[];
}

export interface DubbingAlignmentState {
  schema_version: number;
  alignments: DubbingAlignment[];
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

interface ExecutionPreparation {
  authorization_required: boolean;
  consent_required: string[];
  cost_estimate: Record<string, unknown>;
}

interface PreparationEnvelope {
  selection: Record<string, unknown>;
  authorization: ExecutionPreparation;
}

interface AuthorizationEnvelope extends PreparationEnvelope {
  authorization_token: string;
  expires_at_unix: number;
}

interface SpeechSynthesisOutput {
  run_id: string;
  path: string;
  voice: string;
  speed: number;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail?.message && typeof detail.message === 'string') return new Error(detail.message);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

async function capabilityPost<T>(
  projectId: string,
  capabilityId: string,
  action: 'execute' | 'prepare-execution' | 'authorize-execution',
  body: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/${encodeURIComponent(capabilityId)}/${action}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!response.ok) throw await apiError(response, `${capabilityId}: операция недоступна`);
  return response.json();
}

async function editorCommand<T>(projectId: string, body: Record<string, unknown>): Promise<T> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/editor/commands`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  );
  if (!response.ok) throw await apiError(response, 'Команда редактора не выполнена');
  return response.json();
}

export async function createLocalTranslationDraft(
  projectId: string,
  input: {
    source_language: string;
    target_language: string;
    segments: DubbingTranslationSegment[];
  },
): Promise<TranslationDraft> {
  const envelope = await capabilityPost<CapabilityEnvelope<TranslationDraft>>(
    projectId,
    'text.translate',
    'execute',
    { selection_policy: 'local_free_first', input },
  );
  return envelope.result.output;
}

export async function createForcedAlignmentDraft(
  projectId: string,
  takeId: string,
): Promise<AlignmentDraft> {
  const envelope = await capabilityPost<CapabilityEnvelope<AlignmentDraft>>(
    projectId,
    'audio.align',
    'execute',
    {
      selection_policy: 'local_free_first',
      input: { take_id: takeId },
    },
  );
  return envelope.result.output;
}

export async function acceptForcedAlignment(
  projectId: string,
  draft: AlignmentDraft,
): Promise<{ command: 'accept_dubbing_alignment'; payload: { alignment: DubbingAlignment } }> {
  return editorCommand(projectId, {
    command: 'accept_dubbing_alignment',
    take_id: draft.take_id,
    marks: draft.marks,
  });
}

export async function prepareSpeechSynthesis(
  projectId: string,
  input: { text: string; voice: string; speed: number },
): Promise<PreparationEnvelope> {
  return capabilityPost(projectId, 'speech.synthesize', 'prepare-execution', {
    selection_policy: 'local_free_first',
    input,
  });
}

export async function synthesizeSpeechWithExplicitRemoteConsent(
  projectId: string,
  input: { text: string; voice: string; speed: number },
): Promise<CapabilityEnvelope<SpeechSynthesisOutput>> {
  const preparation = await prepareSpeechSynthesis(projectId, input);
  if (!preparation.authorization.authorization_required) {
    return capabilityPost(projectId, 'speech.synthesize', 'execute', {
      selection_policy: 'local_free_first',
      input,
    });
  }
  const required = preparation.authorization.consent_required;
  if (!required.includes('remote_execution')) {
    throw new Error(
      `Синтез запросил неожиданный тип согласия: ${required.join(', ') || 'неизвестно'}`,
    );
  }
  const unsupported = required.filter(item => item !== 'remote_execution');
  if (unsupported.length > 0) {
    throw new Error(
      `UI не подтверждает дополнительные риски автоматически: ${unsupported.join(', ')}`,
    );
  }
  const authorization = await capabilityPost<AuthorizationEnvelope>(
    projectId,
    'speech.synthesize',
    'authorize-execution',
    {
      selection_policy: 'local_free_first',
      input,
      acknowledgements: ['remote_execution'],
    },
  );
  return capabilityPost(projectId, 'speech.synthesize', 'execute', {
    selection_policy: 'local_free_first',
    input,
    authorization_token: authorization.authorization_token,
  });
}

export async function promoteGeneratedSpeechArtifact(
  projectId: string,
  artifactId: string,
): Promise<ProjectReference> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/prepared-audio/from-artifact/${encodeURIComponent(artifactId)}?origin=tts`,
    { method: 'POST' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось подготовить синтезированную речь');
  return response.json();
}

export async function attachGeneratedPreparedSpeech(
  projectId: string,
  input: {
    dubbing_id: string;
    audio_id: string;
    translation_id?: string;
    segment_id?: string;
  },
): Promise<{
  command: 'attach_prepared_speech';
  dubbing_id: string;
  payload: { prepared_speech: PreparedSpeechTake };
}> {
  return editorCommand(projectId, { command: 'attach_prepared_speech', ...input });
}

export async function saveTranslatedDraft(
  projectId: string,
  input: {
    dubbing_id: string;
    target_language: string;
    segments: DubbingTranslationSegment[];
    translation_id?: string;
  },
): Promise<{
  command: 'upsert_dubbing_translation';
  dubbing_id: string;
  payload: { translation: DubbingTranslation };
}> {
  return editorCommand(projectId, { command: 'upsert_dubbing_translation', ...input });
}
