import type { ProjectReference, UVProject } from './projectsApi';

export type StudioMediaKind = 'video' | 'image' | 'audio';

export interface ProductionDirection {
  direction_id: string;
  title: string;
  description: string;
  primary_input_label: string;
  workspace_sections: string[];
  default_tools: string[];
  featured: boolean;
}

export interface StudioTimelineClip {
  clip_id: string;
  reference_id: string;
  timeline_start_us: number;
  source_start_us: number;
  duration_us: number;
  enabled: boolean;
  muted: boolean;
}

export interface StudioTimelineTrack {
  track_id: string;
  kind: 'video' | 'audio';
  title: string;
  enabled: boolean;
  muted: boolean;
  clips: StudioTimelineClip[];
}

export interface StudioTimeline {
  schema_version: number;
  timeline_id: string;
  tracks: StudioTimelineTrack[];
}

export interface StudioMLTClipProjection {
  track_id: string;
  clip_id: string;
  reference_id: string;
  media_kind: string;
  timeline_start_frame: number;
  source_in_frame: number;
  source_out_frame: number;
  duration_frames: number;
  enabled: boolean;
}

export interface StudioMLTTrackProjection {
  track_id: string;
  kind: 'video' | 'audio';
  enabled: boolean;
  muted: boolean;
  clips: StudioMLTClipProjection[];
}

export interface StudioMLTProjection {
  adapter_id: 'mlt';
  timeline_id: string;
  frame_rate: string;
  width: number;
  height: number;
  duration_us: number;
  duration_frames: number;
  exact_boundaries: boolean;
  max_boundary_error_us: number;
  tracks: StudioMLTTrackProjection[];
  runtime_available: boolean;
}

export interface StudioRenderResult {
  artifact: ProjectReference;
  timeline_revision_sha256: string;
  video_track_id: string;
  audio_track_id: string | null;
  duration_us: number;
}

export type StudioTimelineCommand =
  | {
      command: 'create_track';
      kind: 'video' | 'audio';
      title?: string;
      track_id?: string;
    }
  | {
      command: 'add_clip';
      track_id: string;
      reference_id: string;
      timeline_start_us: number;
      source_start_us?: number;
      duration_us: number;
      clip_id?: string;
    }
  | {
      command: 'move_clip';
      clip_id: string;
      timeline_start_us: number;
    }
  | {
      command: 'trim_clip';
      clip_id: string;
      source_start_us: number;
      duration_us: number;
    }
  | {
      command: 'remove_clip';
      clip_id: string;
    };

export interface StudioTimelineCommandResult {
  command: StudioTimelineCommand['command'];
  track_id: string | null;
  clip_id: string | null;
  timeline: StudioTimeline;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function listProductionDirections(): Promise<ProductionDirection[]> {
  const response = await fetch('/api/uv/projects/studio/directions', { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить направления Studio');
  return response.json();
}

export async function createStudioProject(
  title: string,
  directionId: string,
): Promise<UVProject> {
  const response = await fetch('/api/uv/projects/studio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, direction_id: directionId }),
  });
  if (!response.ok) throw await apiError(response, 'Не удалось создать Studio-проект');
  return response.json();
}

export async function getStudioTimeline(projectId: string): Promise<StudioTimeline> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/timeline`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить timeline');
  return response.json();
}

export async function executeStudioTimelineCommand(
  projectId: string,
  command: StudioTimelineCommand,
): Promise<StudioTimelineCommandResult> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/timeline/commands`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось изменить timeline');
  return response.json();
}

export async function getStudioMLTProjection(projectId: string): Promise<StudioMLTProjection> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/timeline/engine`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось построить MLT-проекцию');
  return response.json();
}

export async function renderStudioTimeline(projectId: string): Promise<StudioRenderResult> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/timeline/render`,
    { method: 'POST' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось экспортировать Studio timeline');
  return response.json();
}

export async function uploadStudioMedia(
  projectId: string,
  file: File,
  kind: StudioMediaKind,
): Promise<ProjectReference> {
  const suffix = kind === 'audio' ? '/audio' : kind === 'image' ? '/image' : '';
  const query = new URLSearchParams({ filename: file.name });
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/sources${suffix}?${query.toString()}`,
    {
      method: 'POST',
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      body: file,
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось импортировать медиафайл');
  return response.json();
}

export function studioSourceMediaUrl(
  projectId: string,
  source: Pick<ProjectReference, 'id' | 'kind'>,
): string {
  const encodedProject = encodeURIComponent(projectId);
  const encodedSource = encodeURIComponent(source.id);
  if (source.kind === 'audio') {
    return `/api/uv/projects/${encodedProject}/sources/audio/${encodedSource}/media`;
  }
  if (source.kind === 'image') {
    return `/api/uv/projects/${encodedProject}/sources/image/${encodedSource}/media`;
  }
  return `/api/uv/projects/${encodedProject}/sources/${encodedSource}/media`;
}

export function studioExportMediaUrl(projectId: string, artifactId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/studio/exports/${encodeURIComponent(artifactId)}/media`;
}

export function inferStudioMediaKind(file: File): StudioMediaKind | null {
  if (file.type.startsWith('video/')) return 'video';
  if (file.type.startsWith('image/')) return 'image';
  if (file.type.startsWith('audio/')) return 'audio';

  const name = file.name.toLowerCase();
  if (/\.(mp4|mov|mkv|webm|m4v|avi|mts|m2ts|mxf)$/.test(name)) return 'video';
  if (/\.(jpg|jpeg|png|webp|bmp|tif|tiff)$/.test(name)) return 'image';
  if (/\.(wav|mp3|flac|m4a|aac|ogg|opus)$/.test(name)) return 'audio';
  return null;
}
