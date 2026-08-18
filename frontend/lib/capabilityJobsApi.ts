export type CapabilityJobStatus =
  | 'queued'
  | 'running'
  | 'cancelling'
  | 'succeeded'
  | 'failed'
  | 'cancelled';

export interface CapabilityJobError {
  code: string;
  message: string;
}

export interface CapabilityJob<T = Record<string, unknown>> {
  schema_version: number;
  job_id: string;
  project_id: string;
  capability_id: string;
  offer_id: string;
  adapter_id: string;
  status: CapabilityJobStatus;
  cancel_requested: boolean;
  created_at_unix: number;
  started_at_unix: number | null;
  finished_at_unix: number | null;
  result: T | null;
  error: CapabilityJobError | null;
}

const terminalStatuses = new Set<CapabilityJobStatus>(['succeeded', 'failed', 'cancelled']);

async function jobApiError(response: Response, fallback: string): Promise<Error> {
  const body = await response.json().catch(() => null);
  const detail = body?.detail;
  if (typeof detail === 'string') return new Error(detail);
  if (typeof detail?.message === 'string') return new Error(detail.message);
  if (detail !== undefined) return new Error(JSON.stringify(detail));
  return new Error(fallback);
}

function sleepWithSignal(delayMs: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    let settled = false;
    const cleanup = () => signal?.removeEventListener('abort', abort);
    const finish = () => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve();
    };
    const abort = () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      cleanup();
      reject(new DOMException('Polling cancelled', 'AbortError'));
    };
    const timer = window.setTimeout(finish, delayMs);
    signal?.addEventListener('abort', abort, { once: true });
  });
}

export function isTerminalCapabilityJob(status: CapabilityJobStatus): boolean {
  return terminalStatuses.has(status);
}

export async function startCapabilityJob<T = Record<string, unknown>>(
  projectId: string,
  capabilityId: string,
  input: Record<string, unknown>,
): Promise<CapabilityJob<T>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capabilities/${encodeURIComponent(capabilityId)}/jobs`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input }),
    },
  );
  if (!response.ok) throw await jobApiError(response, 'Не удалось запустить локальную задачу');
  return response.json();
}

export async function getCapabilityJob<T = Record<string, unknown>>(
  projectId: string,
  jobId: string,
): Promise<CapabilityJob<T>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capability-jobs/${encodeURIComponent(jobId)}`,
    { cache: 'no-store' },
  );
  if (!response.ok) throw await jobApiError(response, 'Не удалось получить состояние локальной задачи');
  return response.json();
}

export async function cancelCapabilityJob<T = Record<string, unknown>>(
  projectId: string,
  jobId: string,
): Promise<CapabilityJob<T>> {
  const response = await fetch(
    `/api/uv/projects/${encodeURIComponent(projectId)}/capability-jobs/${encodeURIComponent(jobId)}/cancel`,
    { method: 'POST' },
  );
  if (!response.ok) throw await jobApiError(response, 'Не удалось отменить локальную задачу');
  return response.json();
}

export async function waitForCapabilityJob<T = Record<string, unknown>>(
  projectId: string,
  jobId: string,
  options: {
    signal?: AbortSignal;
    pollIntervalMs?: number;
    maxConsecutivePollErrors?: number;
    onUpdate?: (job: CapabilityJob<T>) => void;
    onPollError?: (error: Error, consecutiveFailures: number) => void;
  } = {},
): Promise<CapabilityJob<T>> {
  const pollIntervalMs = options.pollIntervalMs ?? 250;
  const maxConsecutivePollErrors = options.maxConsecutivePollErrors ?? 8;
  let consecutiveFailures = 0;

  for (;;) {
    if (options.signal?.aborted) throw new DOMException('Polling cancelled', 'AbortError');
    let job: CapabilityJob<T>;
    try {
      job = await getCapabilityJob<T>(projectId, jobId);
      consecutiveFailures = 0;
    } catch (error) {
      consecutiveFailures += 1;
      const normalized = error instanceof Error ? error : new Error('Не удалось получить состояние локальной задачи');
      options.onPollError?.(normalized, consecutiveFailures);
      if (consecutiveFailures >= maxConsecutivePollErrors) throw normalized;
      const retryDelay = Math.min(pollIntervalMs * 2 ** Math.min(consecutiveFailures - 1, 3), 2_000);
      await sleepWithSignal(retryDelay, options.signal);
      continue;
    }
    options.onUpdate?.(job);
    if (isTerminalCapabilityJob(job.status)) return job;
    await sleepWithSignal(pollIntervalMs, options.signal);
  }
}
