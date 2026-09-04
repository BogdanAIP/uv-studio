export interface ProjectReference {
  id: string;
  kind: string;
  path: string;
  metadata: Record<string, unknown>;
}

export type ProjectIdentityKind = 'modern_direction' | 'legacy_compatibility' | 'invalid_recovery';
export type ProjectCompatibilityKind =
  | 'recipe'
  | 'studio_first'
  | 'studio_unversioned'
  | 'production_directions_v2';

export interface ProjectIdentity {
  kind: ProjectIdentityKind;
  direction_id: string | null;
  compatibility_kind: ProjectCompatibilityKind | null;
  reason: string | null;
}

export interface UVProject {
  schema_version: number;
  project_id: string;
  title: string;
  recipe_id: string;
  created_at: string;
  updated_at: string;
  settings: Record<string, unknown>;
  sources: ProjectReference[];
  artifacts: ProjectReference[];
  extensions: Record<string, unknown>;
  product_identity: ProjectIdentity;
}

export type ExecutionCompatibility = 'available' | 'partial' | 'unavailable';

export interface ExecutionInputSlot {
  slot_id: string;
  title: string;
  kind: 'text' | 'image' | 'video' | 'audio' | 'boolean' | 'number' | 'choice';
  required: boolean;
  description: string;
  maps_to: string | null;
  default: unknown;
}

export interface CapabilityOfferSummary {
  total: number;
  available: number;
  configuration_required: number;
  unavailable: number;
}

export interface RuntimeCapabilityStatus {
  known: boolean;
  operation_kind?: string;
  offer_summary: CapabilityOfferSummary;
}

export interface RuntimeConfigSlot {
  slot_id: string;
  title: string;
  capability_id: string;
  required: boolean;
  maps_to: string | null;
  capability_status: RuntimeCapabilityStatus;
}

export interface ProjectExecutionPlan {
  schema_version: number;
  project_id: string;
  recipe_id: string;
  recipe_title: string;
  compatibility: ExecutionCompatibility;
  can_prepare_native_execution: boolean;
  reason: string;
  input_slots: ExecutionInputSlot[];
  runtime_config_slots: RuntimeConfigSlot[];
  production_policy: Record<string, 'off' | 'optional' | 'required'>;
  target: {
    adapter_id: string;
    target_id: string;
    launch_path: string;
  } | null;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body && typeof body.detail === 'string' ? body.detail : fallback;
  return new Error(detail);
}

export async function listUVProjects(): Promise<UVProject[]> {
  const response = await fetch('/api/uv/projects', { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Failed to load projects');
  return response.json();
}

export async function getUVProject(projectId: string): Promise<UVProject> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Failed to load project');
  return response.json();
}

export async function getProjectExecutionPlan(projectId: string): Promise<ProjectExecutionPlan> {
  const response = await fetch(`/api/uv/projects/${encodeURIComponent(projectId)}/execution-plan`, {
    cache: 'no-store',
  });
  if (!response.ok) throw await apiError(response, 'Failed to load execution plan');
  return response.json();
}

export async function importUVProjectArchive(file: File): Promise<UVProject> {
  const response = await fetch('/api/uv/projects/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/zip' },
    body: file,
  });
  if (!response.ok) throw await apiError(response, 'Failed to import project archive');
  return response.json();
}

export function projectArchiveUrl(projectId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/archive`;
}
