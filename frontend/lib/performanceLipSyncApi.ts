'use client';

import type { CapabilityVideoEnvelope, CapabilityVideoResult } from '@/lib/renderApi';

async function apiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

export interface PerformanceLipSyncOffer {
  offer_id: string;
  capability_id: 'video.digital_human';
  adapter_id: string;
  title: string;
  availability: 'available' | 'configuration_required' | 'unavailable';
  reason: string;
  locality: string;
  cost_class: string;
  asynchronous: boolean;
  features: string[];
  adapter: {
    adapter_id: string;
    title: string;
    description: string;
    kind: string;
  };
}

export interface PerformanceLipSyncOutput {
  path: string;
  artifact_id: string;
  duration_us: number;
  engine: string;
}

export interface PerformanceLipSyncResult extends CapabilityVideoResult {
  capability_id: 'video.digital_human';
  adapter_id: 'local_musetalk';
  output: PerformanceLipSyncOutput & Record<string, unknown>;
}

export async function getPerformanceLipSyncOffers(): Promise<PerformanceLipSyncOffer[]> {
  const response = await fetch('/api/uv/capabilities/video.digital_human/offers', { cache: 'no-store' });
  if (!response.ok) throw await apiError(response, 'Не удалось получить состояние lip-sync capability');
  return response.json();
}

export async function renderPerformanceLipSync(
  projectId: string,
  portraitSourceId: string,
  speechSourceId: string,
): Promise<CapabilityVideoEnvelope<PerformanceLipSyncResult>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/video.digital_human/execute`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        selection_policy: 'local_free_first',
        input: {
          portrait_source_id: portraitSourceId,
          speech_source_id: speechSourceId,
        },
      }),
    },
  );
  if (!response.ok) throw await apiError(response, 'Не удалось выполнить lip-sync');
  return response.json();
}
