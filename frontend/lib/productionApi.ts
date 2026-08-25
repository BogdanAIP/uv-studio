import type { StudioTimeline } from './timelineApi';

export interface ProductionScene {
  scene_id: string;
  title: string;
  summary: string;
  shot_ids: string[];
}

export interface ProductionShot {
  shot_id: string;
  scene_id: string;
  intent: string;
  reference_ids: string[];
  take_ids: string[];
  accepted_take_id: string | null;
  timeline_clip_ids: string[];
}

export interface ProductionTake {
  take_id: string;
  shot_id: string;
  reference_id: string;
  label: string;
  notes: string;
}

export interface ProductionSemantics {
  schema_version: number;
  document_kind: 'production_semantics';
  scenes: ProductionScene[];
  shots: ProductionShot[];
  takes: ProductionTake[];
}

export interface MicroDramaStory {
  title: string;
  premise: string;
  synopsis: string;
}

export interface MicroDramaCharacter {
  character_id: string;
  name: string;
  description: string;
}

export interface MicroDramaLocation {
  location_id: string;
  name: string;
  description: string;
}

export interface MicroDramaSceneContinuity {
  scene_id: string;
  character_ids: string[];
  location_id: string | null;
  canon_facts: string[];
  notes: string;
}

export interface MicroDramaDocument {
  schema_version: number;
  document_kind: 'micro_drama';
  story: MicroDramaStory | null;
  characters: MicroDramaCharacter[];
  locations: MicroDramaLocation[];
  scene_continuity: MicroDramaSceneContinuity[];
}

export type ProductionCommand =
  | {
      command: 'create_scene';
      scene_id: string;
      title: string;
      summary?: string;
    }
  | {
      command: 'create_shot';
      shot_id: string;
      scene_id: string;
      intent: string;
      reference_ids?: string[];
    }
  | {
      command: 'register_take';
      take_id: string;
      shot_id: string;
      reference_id: string;
      label?: string;
      notes?: string;
    }
  | {
      command: 'set_micro_drama_context';
      document: {
        story: MicroDramaStory | null;
        characters: MicroDramaCharacter[];
        locations: MicroDramaLocation[];
        scene_continuity: MicroDramaSceneContinuity[];
      };
    }
  | {
      command: 'accept_take';
      take_id: string;
      timeline_start_us: number;
      source_start_us?: number;
      duration_us: number;
      track_id?: string;
      clip_id?: string;
    };

export interface ProductionCommandResult {
  command: string;
  transaction_id: string;
  production: ProductionSemantics;
  micro_drama: MicroDramaDocument | null;
  timeline: StudioTimeline | null;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getProductionSemantics(projectId: string): Promise<ProductionSemantics> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/production`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить производственную структуру');
  return response.json();
}

export async function getMicroDramaDocument(projectId: string): Promise<MicroDramaDocument> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/production/micro-drama`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить данные мини-драмы');
  return response.json();
}

export async function executeProductionCommand(
  projectId: string,
  command: ProductionCommand,
): Promise<ProductionCommandResult> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/studio/production/commands`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось изменить производственную структуру');
  return response.json();
}
