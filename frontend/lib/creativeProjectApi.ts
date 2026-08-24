import type { UVProject } from './projectsApi';

export type CreativeRouteState = 'ready' | 'needs_connection' | 'unavailable' | 'blocked';
export type CreativePhaseState = 'complete' | 'actionable' | 'optional' | 'blocked' | 'waiting';

export interface CreativeRoute {
  route_id: string;
  title: string;
  state: CreativeRouteState;
  route_class: string;
  reason: string;
  capability_id?: string;
  available_offer_count?: number;
  configuration_required_count?: number;
  has_local_free?: boolean;
  has_external?: boolean;
  may_cost_money?: boolean;
}

export interface CreativePhase {
  phase_id: string;
  title: string;
  state: CreativePhaseState;
  summary: string;
  blocking: boolean;
  routes: CreativeRoute[];
}

export interface CreativePlan {
  schema_version: number;
  project_id: string;
  title: string;
  goal: string;
  script: string;
  provider_policy: 'local_free_first';
  allow_paid_remote: false;
  overall_state: string;
  next_step: string;
  source_summary: {
    images: number;
    videos: number;
    audio: number;
    visuals: number;
  };
  current_outcome: Record<string, unknown> | null;
  phases: CreativePhase[];
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export function isIntentFirstProject(project: UVProject): boolean {
  const extension = project.extensions?.creative_project;
  if (!extension || typeof extension !== 'object' || Array.isArray(extension)) return false;
  const value = extension as Record<string, unknown>;
  return value.schema_version === 1 && typeof value.goal === 'string' && Boolean(value.goal.trim());
}

export async function createCreativeProject(input: {
  goal: string;
  title?: string;
}): Promise<UVProject> {
  const response = await fetch('/api/uv/creative-projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw await apiError(response, 'Не удалось создать проект');
  return response.json();
}

export async function getCreativePlan(projectId: string): Promise<CreativePlan> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/creative-plan`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Не удалось построить план проекта');
  return response.json();
}

export async function updateCreativeIntent(
  projectId: string,
  input: { goal?: string; script?: string },
): Promise<UVProject> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/creative-intent`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw await apiError(response, 'Не удалось сохранить замысел проекта');
  return response.json();
}
