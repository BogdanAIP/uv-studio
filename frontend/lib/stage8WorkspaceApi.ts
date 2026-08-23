'use client';

export type Stage8CompositionRecipeId =
  | 'general_video'
  | 'story_video'
  | 'commercial_product'
  | 'free_project'
  | 'narrated_video';

export interface Stage8WorkspaceSourceBinding {
  source_id: string;
  kind: 'image' | 'video' | 'audio';
  role: string;
  path: string;
  sha256: string;
  size_bytes: number;
}

export interface Stage8RecipeWorkspace {
  schema_version: number;
  recipe_id: Stage8CompositionRecipeId;
  brief: string;
  script: string;
  sources: Stage8WorkspaceSourceBinding[];
  revision_sha256: string;
}

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function getStage8RecipeWorkspace(
  projectId: string,
): Promise<Stage8RecipeWorkspace | null> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/stage8/workspace`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось загрузить workspace режима');
  const payload = await response.json();
  return payload.workspace ?? null;
}

export async function saveStage8RecipeWorkspace(
  projectId: string,
  input: { brief: string; script: string; source_ids: string[] },
): Promise<Stage8RecipeWorkspace> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/stage8/workspace`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось сохранить workspace режима');
  return (await response.json()).workspace;
}
