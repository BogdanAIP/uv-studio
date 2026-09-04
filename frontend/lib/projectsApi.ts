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
