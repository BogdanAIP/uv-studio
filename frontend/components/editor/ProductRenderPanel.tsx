'use client';

import { Download, Film, Loader2, MonitorPlay, RefreshCw, Square } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { CapabilityJob, CapabilityJobStatus } from '@/lib/capabilityJobsApi';
import {
  cancelCapabilityJob,
  startCapabilityJob,
  waitForCapabilityJob,
} from '@/lib/capabilityJobsApi';
import type { EditorState } from '@/lib/editorApi';
import { projectArtifactMediaUrl } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  createBrowserPreview,
  type CapabilityVideoEnvelope,
  type RenderAcceptedEditsResult,
} from '@/lib/renderApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface ProductRenderPanelProps {
  projectId: string;
  editorState: EditorState;
  source: ProjectReference;
  onStateChanged: () => Promise<EditorState>;
  onProjectChanged?: () => void | Promise<void>;
}

type RenderJob = CapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>;

function stringArray(value: unknown): string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string') ? value : [];
}

function numberMetadata(reference: ProjectReference, key: string): number | null {
  const value = reference.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function sameRevision(currentIds: string[], renderedIds: string[]): boolean {
  return currentIds.length === renderedIds.length && currentIds.every((id, index) => id === renderedIds[index]);
}

function statusLabel(status: CapabilityJobStatus | null): string {
  switch (status) {
    case 'queued': return 'В очереди…';
    case 'running': return 'Собираем видео…';
    case 'cancelling': return 'Останавливаем…';
    case 'cancelled': return 'Сборка отменена';
    case 'failed': return 'Сборка не удалась';
    case 'succeeded': return 'Готово';
    default: return 'Подготовка…';
  }
}

export function ProductRenderPanel({
  projectId,
  editorState,
  source,
  onStateChanged,
  onProjectChanged,
}: ProductRenderPanelProps) {
  const [busy, setBusy] = useState<'render' | 'preview' | null>(null);
  const [latestArtifactId, setLatestArtifactId] = useState<string | null>(null);
  const [latestPreviewId, setLatestPreviewId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<CapabilityJobStatus | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const activeJobRef = useRef<string | null>(null);
  const pollingRef = useRef<AbortController | null>(null);

  useEffect(() => () => {
    pollingRef.current?.abort();
    const activeJob = activeJobRef.current;
    if (activeJob) void cancelCapabilityJob(projectId, activeJob).catch(() => undefined);
  }, [projectId]);

  const accepted = useMemo(
    () => editorState.accepted_edits.filter(edit => edit.source_path === source.path),
    [editorState.accepted_edits, source.path],
  );
  const acceptedIds = useMemo(() => accepted.map(edit => edit.edit_id), [accepted]);
  const renders = useMemo(
    () => editorState.artifacts.filter(artifact =>
      artifact.kind === 'video' &&
      artifact.metadata.lifecycle === 'render' &&
      artifact.metadata.source_path === source.path,
    ),
    [editorState.artifacts, source.path],
  );
  const activeRender = renders.find(item => item.id === latestArtifactId) ?? renders.at(-1) ?? null;
  const previews = useMemo(
    () => activeRender
      ? editorState.artifacts.filter(artifact =>
          artifact.kind === 'video' &&
          artifact.metadata.lifecycle === 'browser_preview' &&
          artifact.metadata.source_artifact_id === activeRender.id,
        )
      : [],
    [activeRender, editorState.artifacts],
  );
  const activePreview = previews.find(item => item.id === latestPreviewId) ?? previews.at(-1) ?? null;
  const renderedIds = activeRender ? stringArray(activeRender.metadata.edit_ids) : [];
  const currentRevision = activeRender ? sameRevision(acceptedIds, renderedIds) : false;
  const durationUs = activeRender ? numberMetadata(activeRender, 'actual_output_video_duration_us') : null;

  const refreshEverything = async () => {
    await onStateChanged();
    await onProjectChanged?.();
  };

  const makePreview = async (masterId: string) => {
    const preview = await createBrowserPreview(projectId, masterId);
    const previewId = preview.result.artifact?.id;
    if (!previewId) throw new Error('Не удалось подготовить просмотр итогового видео.');
    setLatestPreviewId(previewId);
  };

  const acceptTerminal = async (terminal: RenderJob): Promise<string | null> => {
    if (terminal.status === 'cancelled') {
      activeJobRef.current = null;
      setJobStatus('cancelled');
      setNotice('Сборка отменена. Незавершённый файл не добавлен в проект.');
      return null;
    }
    if (terminal.status === 'failed') {
      activeJobRef.current = null;
      setJobStatus('failed');
      throw new Error(terminal.error?.message ?? 'Не удалось собрать итоговое видео.');
    }
    if (terminal.status !== 'succeeded' || !terminal.result?.result.artifact?.id) {
      throw new Error('Приложение не получило подтверждение готового файла.');
    }
    activeJobRef.current = null;
    setJobStatus('succeeded');
    const masterId = terminal.result.result.artifact.id;
    setLatestArtifactId(masterId);
    setLatestPreviewId(null);
    return masterId;
  };

  const handleRender = async () => {
    if (accepted.length === 0) return;
    const polling = new AbortController();
    pollingRef.current?.abort();
    pollingRef.current = polling;
    setBusy('render');
    setError(null);
    setPreviewError(null);
    setNotice(null);
    setJobId(null);
    setJobStatus('queued');
    let keepControls = false;
    let completed = false;
    let startedId: string | null = null;
    try {
      const started = await startCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
        projectId,
        'video.render_edits',
        { source_path: source.path },
      );
      startedId = started.job_id;
      activeJobRef.current = started.job_id;
      setJobId(started.job_id);
      setJobStatus(started.status);
      const terminal = await waitForCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
        projectId,
        started.job_id,
        {
          signal: polling.signal,
          onUpdate: job => setJobStatus(job.status),
          onPollError: (_, failures) => setNotice(`Проверяем состояние сборки повторно (${failures}/8)…`),
        },
      );
      const masterId = await acceptTerminal(terminal);
      if (!masterId) return;
      completed = true;
      setNotice('Итоговое видео готово. Подготавливаем просмотр…');
      try {
        await makePreview(masterId);
      } catch (reason) {
        setPreviewError(reason instanceof Error ? reason.message : 'Просмотр пока недоступен, но итоговый файл сохранён.');
      }
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === 'AbortError') return;
      if (startedId && activeJobRef.current === startedId) {
        keepControls = true;
        setNotice('Связь со сборкой временно потеряна. Можно повторить проверку или отменить задачу.');
      }
      setError(reason instanceof Error ? reason.message : 'Не удалось собрать итоговое видео.');
    } finally {
      if (completed) await refreshEverything();
      if (pollingRef.current === polling) pollingRef.current = null;
      if (!keepControls) setBusy(null);
    }
  };

  const handleCancel = async () => {
    const activeId = activeJobRef.current;
    if (!activeId) return;
    setError(null);
    setNotice('Останавливаем сборку…');
    try {
      const requested = await cancelCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(projectId, activeId);
      setJobStatus(requested.status);
      let terminal = requested;
      if (!['cancelled', 'failed', 'succeeded'].includes(requested.status)) {
        const polling = new AbortController();
        pollingRef.current?.abort();
        pollingRef.current = polling;
        terminal = await waitForCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
          projectId,
          activeId,
          { signal: polling.signal, onUpdate: job => setJobStatus(job.status) },
        );
      }
      const masterId = await acceptTerminal(terminal);
      if (masterId) {
        setNotice('Сборка успела завершиться до отмены. Итоговый файл сохранён.');
        await refreshEverything();
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Не удалось остановить сборку.');
    } finally {
      if (!activeJobRef.current) setBusy(null);
    }
  };

  const handlePreview = async () => {
    if (!activeRender) return;
    setBusy('preview');
    setPreviewError(null);
    try {
      await makePreview(activeRender.id);
      await refreshEverything();
    } catch (reason) {
      setPreviewError(reason instanceof Error ? reason.message : 'Не удалось подготовить просмотр.');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-600">Итоговое видео</p>
          <h3 className="mt-2 text-lg font-medium text-zinc-100">Собрать применённые изменения</h3>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-600">
            UV Studio соберёт исходное видео и все применённые изменения в один итоговый файл.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void handleRender()}
            disabled={busy !== null || accepted.length === 0}
            className="inline-flex h-10 items-center gap-2 rounded-xl bg-violet-400 px-4 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
          >
            {busy === 'render' ? <Loader2 size={15} className="animate-spin" /> : renders.length ? <RefreshCw size={15} /> : <Film size={15} />}
            {busy === 'render' ? statusLabel(jobStatus) : renders.length ? 'Пересобрать' : 'Собрать итоговое видео'}
          </button>
          {busy === 'render' && jobId && (
            <button
              type="button"
              onClick={() => void handleCancel()}
              disabled={jobStatus === 'cancelling' || jobStatus === 'cancelled'}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] px-4 text-sm text-rose-200 disabled:opacity-40"
            >
              <Square size={13} /> Остановить
            </button>
          )}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Применено изменений" value={accepted.length} />
        <Stat label="Собрано версий" value={renders.length} />
        <Stat label="Состояние" value={!activeRender ? 'Не собрано' : currentRevision ? 'Актуально' : 'Нужно пересобрать'} tone={activeRender && currentRevision ? 'ok' : activeRender ? 'warn' : undefined} />
      </div>

      {accepted.length === 0 && (
        <div className="mt-4 rounded-xl border border-[var(--uv-border)] bg-black/10 px-4 py-3 text-sm text-zinc-600">
          Пока нет применённых изменений. Подготовьте изменение в «Монтаже», проверьте предпросмотр и примените его.
        </div>
      )}
      {notice && <div className="mt-4 rounded-xl border border-violet-400/15 bg-violet-400/[0.06] px-4 py-3 text-sm text-zinc-400">{notice}</div>}
      {error && <div className="mt-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] px-4 py-3 text-sm text-rose-200">{error}</div>}
      {previewError && <div className="mt-4 rounded-xl border border-amber-400/20 bg-amber-400/[0.06] px-4 py-3 text-sm text-amber-100">{previewError}</div>}

      {activeRender && (
        <div className={`mt-4 overflow-hidden rounded-2xl border ${currentRevision ? 'border-emerald-400/20' : 'border-amber-400/20'} bg-black/15`}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--uv-border)] px-4 py-3">
            <div>
              <p className={`text-sm font-medium ${currentRevision ? 'text-emerald-300' : 'text-amber-200'}`}>
                {currentRevision ? 'Итоговое видео актуально' : 'После последней сборки проект изменился'}
              </p>
              {durationUs !== null && <p className="mt-1 text-xs text-zinc-700">Длительность {formatTimelineTime(durationUs)}</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              {!activePreview && (
                <button type="button" onClick={() => void handlePreview()} disabled={busy !== null} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border)] px-3 text-xs text-zinc-400 transition hover:text-zinc-200 disabled:opacity-40">
                  {busy === 'preview' ? <Loader2 size={13} className="animate-spin" /> : <MonitorPlay size={13} />} Подготовить просмотр
                </button>
              )}
              <a href={projectArtifactMediaUrl(projectId, activeRender.id)} download={`${source.id}-uv-master.mkv`} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border-strong)] bg-[var(--uv-surface-1)] px-3 text-xs text-zinc-300">
                <Download size={13} /> Скачать файл
              </a>
            </div>
          </div>
          {activePreview ? (
            <video key={activePreview.id} src={projectArtifactMediaUrl(projectId, activePreview.id)} controls playsInline preload="metadata" className="aspect-video w-full bg-black object-contain" />
          ) : (
            <div className="flex min-h-52 flex-col items-center justify-center px-6 py-10 text-center">
              <MonitorPlay size={24} className="text-zinc-700" />
              <p className="mt-3 max-w-md text-sm leading-6 text-zinc-600">Итоговый файл сохранён. Подготовьте просмотр, если браузер не воспроизводит мастер напрямую.</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: string | number; tone?: 'ok' | 'warn' }) {
  return (
    <div className="rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-3">
      <p className="text-[10px] uppercase tracking-[0.12em] text-zinc-700">{label}</p>
      <p className={`mt-1.5 text-sm font-medium ${tone === 'ok' ? 'text-emerald-300' : tone === 'warn' ? 'text-amber-200' : 'text-zinc-300'}`}>{value}</p>
    </div>
  );
}
