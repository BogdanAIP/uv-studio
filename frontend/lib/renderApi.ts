import type { ProjectReference } from './projectsApi';

export interface RenderAcceptedEditsOutput {
  path: string;
  source_path: string;
  edit_ids: string[];
  expected_output_video_duration_us: number;
  actual_output_video_duration_us: number;
  composition_mode: string;
  audio_policy: string;
}

export interface RenderAcceptedEditsResult {
  schema_version: number;
  project_id: string;
  capability_id: 'video.render_edits';
  offer_id: string;
  adapter_id: string;
  output: RenderAcceptedEditsOutput;
  artifact: ProjectReference;
}

export interface RenderAcceptedEditsEnvelope {
  selection: Record<string, unknown>;
  result: RenderAcceptedEditsResult;
}

async function renderError(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error('Не удалось собрать мастер-рендер');
}

export async function renderAcceptedEdits(
  projectId: string,
  sourcePath: string,
): Promise<RenderAcceptedEditsEnvelope> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.render_edits/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { source_path: sourcePath } }),
    },
  );
  if (!response.ok) throw await renderError(response);
  return response.json();
}
