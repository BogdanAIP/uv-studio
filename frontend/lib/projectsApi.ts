export interface ProjectReference {
  id: string;
  kind: string;
  path: string;
  metadata: Record<string, unknown>;
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
}

export interface CreateProjectInput {
  title: string;
  recipe_id?: string;
  settings?: Record<string, unknown>;
  extensions?: Record<string, unknown>;
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

export async function createUVProject(input: CreateProjectInput): Promise<UVProject> {
  const response = await fetch('/api/uv/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw await apiError(response, 'Failed to create project');
  return response.json();
}
