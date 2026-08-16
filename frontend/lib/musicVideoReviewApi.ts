'use client';

export type MusicVideoReviewVerdict = 'approved' | 'needs_revision' | 'rejected';
export type MusicVideoReviewOutcome = 'pass' | 'fail' | 'uncertain';

export interface MusicVideoReviewState {
  schema_version: number;
  artifact_id: string;
  artifact_path: string;
  artifact_sha256: string;
  music_map_revision_sha256: string;
  music_direction_revision_sha256: string;
  music_assembly_revision_sha256: string;
  verdict: MusicVideoReviewVerdict;
  transition_outcome: MusicVideoReviewOutcome;
  evidence: {
    release_duration: { outcome: 'pass' | 'fail'; duration_us: number; required_min_us: number; required_max_us: number };
    rhythm_alignment: { outcome: 'pass' | 'fail'; summary: { cut_count: number; aligned_count: number; unaligned_count: number; all_aligned: boolean; max_abs_delta_us: number | null }; tolerance_us: number };
    master_audio_binding: { outcome: 'pass'; song_reference_id: string; song_sha256: string; excerpt: { start_us: number; end_us: number } };
    visual_assembly_binding: { outcome: 'pass'; binding_count: number; shot_ids: string[] };
  } & Record<string, unknown>;
  note: string | null;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getMusicVideoReview(projectId: string): Promise<MusicVideoReviewState | null> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/music-video-review`, { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить финальную проверку');
  const body = await response.json() as { music_video_review: MusicVideoReviewState | null };
  return body.music_video_review;
}

export async function submitMusicVideoReview(
  projectId: string,
  payload: {
    artifact_id: string;
    verdict: MusicVideoReviewVerdict;
    transition_outcome: MusicVideoReviewOutcome;
    note: string | null;
  },
): Promise<MusicVideoReviewState> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/music-video-review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw await apiError(response, 'Финальная проверка не сохранена');
  const body = await response.json() as { music_video_review: MusicVideoReviewState };
  return body.music_video_review;
}
