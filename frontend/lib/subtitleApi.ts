import type { ProjectReference } from './projectsApi';

export interface WebVTTExportOutput {
  path: string;
  artifact_id: string;
  format: 'webvtt';
  language: string;
  cue_count: number;
  script_kind: 'transcript' | 'translation';
  script_id: string;
}

interface WebVTTExecutionEnvelope {
  selection: Record<string, unknown>;
  result: {
    schema_version: number;
    project_id: string;
    capability_id: 'subtitle.export_webvtt';
    offer_id: string;
    adapter_id: 'local_webvtt';
    output: WebVTTExportOutput;
    artifact: ProjectReference;
  };
}

async function apiError(response: Response): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail?.message && typeof detail.message === 'string') return new Error(detail.message);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error('Не удалось экспортировать WebVTT');
}

export async function exportWebVTT(
  projectId: string,
  input: { dubbing_id: string; translation_id?: string },
): Promise<WebVTTExecutionEnvelope> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/subtitle.export_webvtt/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selection_policy: 'local_free_first', input }),
    },
  );
  if (!response.ok) throw await apiError(response);
  return response.json();
}

export function projectArtifactDownloadUrl(projectId: string, artifactId: string): string {
  return `/api/uv/projects/${encodeURIComponent(projectId)}/artifacts/${encodeURIComponent(artifactId)}/file`;
}
