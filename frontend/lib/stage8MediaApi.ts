'use client';

import type { ProjectReference } from '@/lib/projectsApi';
import type { CapabilityVideoEnvelope, CapabilityVideoResult } from '@/lib/renderApi';

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

async function uploadSource(
  projectId: string,
  file: File,
  kind: 'image' | 'audio',
): Promise<ProjectReference> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sources/${kind}?filename=${encodeURIComponent(file.name)}`,
    {
      method: 'POST',
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      body: file,
    },
  );
  if (!response.ok) {
    throw await apiError(
      response,
      kind === 'image' ? 'Не удалось загрузить изображение' : 'Не удалось загрузить аудио',
    );
  }
  return response.json();
}

export function uploadProjectImageSource(projectId: string, file: File): Promise<ProjectReference> {
  return uploadSource(projectId, file, 'image');
}

export function uploadStage8AudioSource(projectId: string, file: File): Promise<ProjectReference> {
  return uploadSource(projectId, file, 'audio');
}

export function projectStage8ArtifactUrl(projectId: string, artifactId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/media`;
}

export interface PhotoToVideoOutput {
  path: string;
  artifact_id: string;
  composition_mode: string;
  duration_us: number;
}

export interface PhotoToVideoResult extends CapabilityVideoResult {
  capability_id: 'video.compose_photos';
  output: PhotoToVideoOutput & Record<string, unknown>;
}

export interface VisualizerOutput {
  path: string;
  artifact_id: string;
  composition_mode: string;
  duration_us: number;
}

export interface VisualizerResult extends CapabilityVideoResult {
  capability_id: 'audio.visualize';
  output: VisualizerOutput & Record<string, unknown>;
}

export async function renderAudioVisualizer(
  projectId: string,
  audioSourceId: string,
  artworkSourceId?: string,
): Promise<CapabilityVideoEnvelope<VisualizerResult>> {
  const input: Record<string, unknown> = { audio_source_id: audioSourceId };
  if (artworkSourceId) input.artwork_source_id = artworkSourceId;
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/audio.visualize/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selection_policy: 'local_free_first', input }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось собрать аудиовизуализатор');
  return response.json();
}
