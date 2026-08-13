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

export interface CapabilityVideoResult {
  schema_version: number;
  project_id: string;
  capability_id: string;
  offer_id: string;
  adapter_id: string;
  output: Record<string, unknown>;
  artifact: ProjectReference;
}

export interface CapabilityVideoEnvelope<T extends CapabilityVideoResult = CapabilityVideoResult> {
  selection: Record<string, unknown>;
  result: T;
}

export interface RenderAcceptedEditsResult extends CapabilityVideoResult {
  capability_id: 'video.render_edits';
  output: RenderAcceptedEditsOutput & Record<string, unknown>;
}

async function capabilityError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export async function renderAcceptedEdits(
  projectId: string,
  sourcePath: string,
): Promise<CapabilityVideoEnvelope<RenderAcceptedEditsResult>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.render_edits/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { source_path: sourcePath } }),
    },
  );
  if (!response.ok) throw await capabilityError(response, 'Не удалось собрать мастер-рендер');
  return response.json();
}

export async function createBrowserPreview(
  projectId: string,
  artifactId: string,
): Promise<CapabilityVideoEnvelope> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.preview_artifact/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { artifact_id: artifactId } }),
    },
  );
  if (!response.ok) throw await capabilityError(response, 'Не удалось создать browser preview');
  return response.json();
}
