'use client';

import type { ProjectReference } from '@/lib/projectsApi';
import type { CapabilityVideoEnvelope, CapabilityVideoResult } from '@/lib/renderApi';

export type MusicSectionKind =
  | 'intro'
  | 'verse'
  | 'pre_chorus'
  | 'chorus'
  | 'bridge'
  | 'drop'
  | 'breakdown'
  | 'outro'
  | 'instrumental'
  | 'other';

export type MusicMarkerKind = 'beat' | 'downbeat' | 'accent' | 'climax' | 'phrase_boundary' | 'cut_point';
export type MusicTransition = 'cut' | 'dissolve' | 'fade' | 'match_cut' | 'other';

export interface MusicSourceBinding {
  reference_id: string;
  reference_path: string;
  sha256: string;
  size_bytes: number;
  duration_us: number;
}

export interface MusicExcerpt {
  start_us: number;
  end_us: number;
}

export interface MusicSection {
  section_id: string;
  kind: MusicSectionKind;
  label: string;
  start_us: number;
  end_us: number;
}

export interface MusicTimingMarker {
  marker_id: string;
  kind: MusicMarkerKind;
  time_us: number;
}

export interface MusicLyricPhrase {
  phrase_id: string;
  start_us: number;
  end_us: number;
  text: string;
}

export interface MusicMapState {
  schema_version: number;
  song: MusicSourceBinding;
  excerpt: MusicExcerpt;
  sections: MusicSection[];
  markers: MusicTimingMarker[];
  lyric_phrases: MusicLyricPhrase[];
  revision_sha256: string;
}

export interface MusicShotPlan {
  shot_id: string;
  order: number;
  start_us: number;
  end_us: number;
  intent: string;
  sync_marker_ids: string[];
  transition_out: MusicTransition;
}

export interface MusicDirectionState {
  schema_version: number;
  music_map_revision_sha256: string;
  shots: MusicShotPlan[];
  revision_sha256: string;
}

export interface MusicVisualBinding {
  shot_id: string;
  source_id: string;
  source_path: string;
  source_sha256: string;
  source_size_bytes: number;
  source_start_us: number;
  source_end_us: number;
}

export interface MusicAssemblyState {
  schema_version: number;
  music_direction_revision_sha256: string;
  bindings: MusicVisualBinding[];
  revision_sha256: string;
}

export interface RhythmAuditCut {
  shot_id: string;
  cut_time_us: number;
  target: { target_id: string; kind: string; time_us: number } | null;
  delta_us: number | null;
  abs_delta_us: number | null;
  aligned: boolean;
}

export interface RhythmAudit {
  music_map_revision_sha256: string;
  music_direction_revision_sha256: string;
  tolerance_us: number;
  cuts: RhythmAuditCut[];
  summary: {
    cut_count: number;
    aligned_count: number;
    unaligned_count: number;
    all_aligned: boolean;
    max_abs_delta_us: number | null;
  };
}

export interface SetMusicMapCommand {
  command: 'set_music_map';
  song_reference_id: string;
  excerpt: MusicExcerpt;
  sections: MusicSection[];
  markers: MusicTimingMarker[];
  lyric_phrases: MusicLyricPhrase[];
}

export interface ClearMusicMapCommand {
  command: 'clear_music_map';
}

export interface SetMusicDirectionCommand {
  command: 'set_music_direction';
  music_map_revision_sha256: string;
  shots: MusicShotPlan[];
}

export interface ClearMusicDirectionCommand {
  command: 'clear_music_direction';
}

export interface MusicVisualAssignmentInput {
  shot_id: string;
  source_id: string;
  source_start_us: number;
}

export interface SetMusicAssemblyCommand {
  command: 'set_music_assembly';
  music_direction_revision_sha256: string;
  assignments: MusicVisualAssignmentInput[];
}

export interface ClearMusicAssemblyCommand {
  command: 'clear_music_assembly';
}

export interface RenderMusicVideoOutput {
  path: string;
  composition_mode: string;
  music_map_revision_sha256: string;
  music_direction_revision_sha256: string;
  music_assembly_revision_sha256: string;
  song_reference_id: string;
  song_excerpt: MusicExcerpt;
  visual_shot_ids: string[];
  actual_output_video_duration_us: number;
  actual_output_audio_duration_us: number;
}

export interface RenderMusicVideoResult extends CapabilityVideoResult {
  capability_id: 'video.render_music_video';
  output: RenderMusicVideoOutput & Record<string, unknown>;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { cache: 'no-store', ...init });
  if (!response.ok) throw await apiError(response, 'Music Video operation failed');
  return response.json();
}

async function uploadProjectSource(
  projectId: string,
  file: File,
  kind: 'video' | 'audio',
): Promise<ProjectReference> {
  const suffix = kind === 'audio' ? '/audio' : '';
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sources${suffix}?filename=${encodeURIComponent(file.name)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      body: file,
    },
  );
  if (!response.ok) {
    throw await apiError(response, kind === 'audio' ? 'Не удалось загрузить песню' : 'Не удалось загрузить видео');
  }
  return response.json();
}

export async function uploadProjectAudioSource(projectId: string, file: File): Promise<ProjectReference> {
  return uploadProjectSource(projectId, file, 'audio');
}

export async function uploadProjectVideoSource(projectId: string, file: File): Promise<ProjectReference> {
  return uploadProjectSource(projectId, file, 'video');
}

export function projectAudioUrl(projectId: string, sourceId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/sources/audio/${encodeURIComponent(sourceId)}/media`;
}

export function projectVideoUrl(projectId: string, sourceId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/sources/${encodeURIComponent(sourceId)}/media`;
}

export function projectVideoArtifactUrl(projectId: string, artifactId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/media`;
}

export async function getMusicMap(projectId: string): Promise<MusicMapState | null> {
  const response = await requestJson<{ music_map: MusicMapState | null }>(
    `/api/uv/projects/${encodeURIComponent(projectId)}/music-map`,
  );
  return response.music_map;
}

export async function executeMusicMapCommand(
  projectId: string,
  command: SetMusicMapCommand | ClearMusicMapCommand,
): Promise<{ command: string; payload: MusicMapState | null }> {
  return requestJson(`/api/uv/projects/${encodeURIComponent(projectId)}/music-map/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
}

export async function getMusicDirection(projectId: string): Promise<MusicDirectionState | null> {
  const response = await requestJson<{ music_direction: MusicDirectionState | null }>(
    `/api/uv/projects/${encodeURIComponent(projectId)}/music-direction`,
  );
  return response.music_direction;
}

export async function executeMusicDirectionCommand(
  projectId: string,
  command: SetMusicDirectionCommand | ClearMusicDirectionCommand,
): Promise<{ command: string; payload: MusicDirectionState | null }> {
  return requestJson(`/api/uv/projects/${encodeURIComponent(projectId)}/music-direction/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
}

export async function getMusicAssembly(projectId: string): Promise<MusicAssemblyState | null> {
  const response = await requestJson<{ music_assembly: MusicAssemblyState | null }>(
    `/api/uv/projects/${encodeURIComponent(projectId)}/music-assembly`,
  );
  return response.music_assembly;
}

export async function executeMusicAssemblyCommand(
  projectId: string,
  command: SetMusicAssemblyCommand | ClearMusicAssemblyCommand,
): Promise<{ command: string; payload: MusicAssemblyState | null }> {
  return requestJson(`/api/uv/projects/${encodeURIComponent(projectId)}/music-assembly/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command),
  });
}

export async function getRhythmAudit(projectId: string, toleranceUs = 120_000): Promise<RhythmAudit> {
  return requestJson(
    `/api/uv/projects/${encodeURIComponent(projectId)}/music-direction/rhythm-audit?tolerance_us=${encodeURIComponent(String(toleranceUs))}`,
  );
}

export async function renderMusicVideo(
  projectId: string,
  assemblyRevisionSha256: string,
): Promise<CapabilityVideoEnvelope<RenderMusicVideoResult>> {
  return requestJson(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.render_music_video/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selection_policy: 'local_free_first',
        input: { assembly_revision_sha256: assemblyRevisionSha256 },
      }),
    },
  );
}
