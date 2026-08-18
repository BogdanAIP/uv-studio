'use client';

import { Download, Film, Loader2, MonitorPlay, ShieldCheck } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { EditorState } from '@/lib/editorApi';
import { projectArtifactMediaUrl } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import type { CapabilityJob, CapabilityJobStatus } from '@/lib/capabilityJobsApi';
import {
  cancelCapabilityJob,
  startCapabilityJob,
  waitForCapabilityJob,
} from '@/lib/capabilityJobsApi';
import {
  createBrowserPreview,
  type CapabilityVideoEnvelope,
  type RenderAcceptedEditsResult,
} from '@/lib/renderApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface EditorRenderPanelProps {
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

function metadataNumber(reference: ProjectReference, key: string): number | null {
  const value = reference.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(reference: ProjectReference, key: string): string | null {
  const value = reference.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function sameEditRevision(acceptedIds: string[], renderedIds: string[]): boolean {
  if (acceptedIds.length !== renderedIds.length) return false;
  return acceptedIds.every((id, index) => id === renderedIds[index]);
}

function renderJobLabel(status: CapabilityJobStatus | null): string {
  switch (status) {
    case 'queued': return 'Рендер поставлен в очередь';
    case 'running': return 'FFmpeg собирает мастер';
    case 'cancelling': return 'Останавливаем FFmpeg';
    case 'cancelled': return 'Рендер отменён';
    case 'failed': return 'Рендер завершился ошибкой';
    case 'succeeded': return 'Мастер собран';
    default: return 'Подготовка рендера';
  }
}

export function EditorRenderPanel({
  projectId,
  editorState,
  source,
  onStateChanged,
  onProjectChanged,
}: EditorRenderPanelProps) {
  const [busy, setBusy] = useState<'render' | 'preview' | null>(null);
  const [latestArtifactId, setLatestArtifactId] = useState<string | null>(null);
  const [latestPreviewId, setLatestPreviewId] = useState<string | null>(null);
  const [renderJobId, setRenderJobId] = useState<string | null>(null);
  const [renderJobStatus, setRenderJobStatus] = useState<CapabilityJobStatus | null>(null);
  const [renderNotice, setRenderNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const activeJobRef = useRef<string | null>(null);
  const pollingRef = useRef<AbortController | null>(null);

  useEffect(() => () => {
    pollingRef.current?.abort();
    const activeJobId = activeJobRef.current;
    if (activeJobId) {
      void cancelCapabilityJob(projectId, activeJobId).catch(() => undefined);
    }
  }, [projectId]);

  const accepted = useMemo(
    () => editorState.accepted_edits.filter(edit => edit.source_path === source.path),
    [editorState.accepted_edits, source.path],
  );
  const acceptedIds = useMemo(() => accepted.map(edit => edit.edit_id), [accepted]);
  const renders = useMemo(
    () =>
      editorState.artifacts.filter(
        artifact =>
          artifact.kind === 'video' &&
          artifact.metadata.lifecycle === 'render' &&
          artifact.metadata.source_path === source.path,
      ),
    [editorState.artifacts, source.path],
  );
  const activeRender =
    renders.find(artifact => artifact.id === latestArtifactId) ?? renders[renders.length - 1] ?? null;
  const previews = useMemo(
    () =>
      activeRender
        ? editorState.artifacts.filter(
            artifact =>
              artifact.kind === 'video' &&
              artifact.metadata.lifecycle === 'browser_preview' &&
              artifact.metadata.source_artifact_id === activeRender.id,
          )
        : [],
    [activeRender, editorState.artifacts],
  );
  const activePreview =
    previews.find(artifact => artifact.id === latestPreviewId) ?? previews[previews.length - 1] ?? null;
  const renderedIds = activeRender ? stringArray(activeRender.metadata.edit_ids) : [];
  const currentRevision = activeRender ? sameEditRevision(acceptedIds, renderedIds) : false;
  const actualDurationUs = activeRender
    ? metadataNumber(activeRender, 'actual_output_video_duration_us')
    : null;
  const compositionMode = activeRender ? metadataText(activeRender, 'composition_mode') : null;

  const refreshEverything = async () => {
    await onStateChanged();
    await onProjectChanged?.();
  };

  const makePreview = async (masterId: string) => {
    const preview = await createBrowserPreview(projectId, masterId);
    if (!preview.result.artifact?.id) {
      throw new Error('Preview завершился без зарегистрированного artifact ID.');
    }
    setLatestPreviewId(preview.result.artifact.id);
  };

  const acceptTerminalRenderJob = async (terminal: RenderJob) => {
    if (terminal.status === 'cancelled') {
      activeJobRef.current = null;
      setRenderJobStatus('cancelled');
      setRenderNotice('Рендер отменён. Частичный мастер не опубликован в проекте.');
      setBusy(null);
      return null;
    }
    if (terminal.status === 'failed') {
      activeJobRef.current = null;
      setRenderJobStatus('failed');
      setBusy(null);
      throw new Error(terminal.error?.message ?? 'Не удалось собрать мастер-рендер');
    }
    if (terminal.status !== 'succeeded' || !terminal.result) {
      throw new Error(`Неожиданное состояние рендера: ${terminal.status}`);
    }
    activeJobRef.current = null;
    setRenderJobStatus('succeeded');
    const envelope = terminal.result;
    if (!envelope.result.artifact?.id) {
      setBusy(null);
      throw new Error('Рендер завершился без зарегистрированного artifact ID.');
    }
    setLatestArtifactId(envelope.result.artifact.id);
    setLatestPreviewId(null);
    return envelope.result.artifact.id;
  };

  const handleCancelRender = async () => {
    const jobId = activeJobRef.current;
    if (!jobId) return;
    setError(null);
    setRenderNotice('Запрошена отмена. UV Studio ждёт фактической остановки FFmpeg и очистки частичного результата.');
    try {
      const requested = await cancelCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
        projectId,
        jobId,
      );
      setRenderJobStatus(requested.status);
      let terminal = requested;
      if (!['cancelled', 'failed', 'succeeded'].includes(requested.status)) {
        const polling = new AbortController();
        pollingRef.current?.abort();
        pollingRef.current = polling;
        terminal = await waitForCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
          projectId,
          jobId,
          {
            signal: polling.signal,
            onUpdate: job => setRenderJobStatus(job.status),
          },
        );
        if (pollingRef.current === polling) pollingRef.current = null;
      }
      const masterId = await acceptTerminalRenderJob(terminal);
      if (masterId) {
        setRenderNotice('Рендер успел завершиться до обработки отмены. Мастер сохранён в проекте.');
        await refreshEverything();
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      setError(err instanceof Error ? err.message : 'Не удалось подтвердить отмену рендера');
      if (activeJobRef.current === jobId) {
        setRenderNotice('Не удалось подтвердить состояние задачи. Кнопка отмены остаётся доступной; UV Studio не считает рендер завершённым без terminal state от backend.');
        setBusy('render');
      }
    }
  };

  const handleRender = async () => {
    if (accepted.length === 0) return;
    const polling = new AbortController();
    pollingRef.current?.abort();
    pollingRef.current = polling;
    setBusy('render');
    setError(null);
    setPreviewError(null);
    setRenderNotice(null);
    setRenderJobId(null);
    setRenderJobStatus('queued');
    let masterCreated = false;
    let keepJobControls = false;
    let startedJobId: string | null = null;
    try {
      const started = await startCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
        projectId,
        'video.render_edits',
        { source_path: source.path },
      );
      startedJobId = started.job_id;
      activeJobRef.current = started.job_id;
      setRenderJobId(started.job_id);
      setRenderJobStatus(started.status);

      const terminal = await waitForCapabilityJob<CapabilityVideoEnvelope<RenderAcceptedEditsResult>>(
        projectId,
        started.job_id,
        {
          signal: polling.signal,
          onUpdate: job => setRenderJobStatus(job.status),
          onPollError: (_, failures) => {
            setRenderNotice(`Временно потеряна связь со статусом рендера. Повтор проверки ${failures}/8; сам FFmpeg job не считается завершённым.`);
          },
        },
      );
      const masterId = await acceptTerminalRenderJob(terminal);
      if (!masterId) return;
      setRenderNotice('Мастер собран. Создаём browser preview.');
      masterCreated = true;
      try {
        await makePreview(masterId);
      } catch (err) {
        setPreviewError(
          err instanceof Error
            ? `Мастер сохранён, но browser preview не создан: ${err.message}`
            : 'Мастер сохранён, но browser preview не создан.',
        );
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      if (startedJobId && activeJobRef.current === startedJobId) {
        keepJobControls = true;
        setRenderNotice('Не удалось подтвердить состояние задачи после повторных попыток. UV Studio сохраняет job ID и кнопку отмены, пока backend не вернёт terminal state.');
        setError(err instanceof Error ? err.message : 'Потеряна связь со статусом рендера');
      } else {
        activeJobRef.current = null;
        setError(err instanceof Error ? err.message : 'Не удалось собрать мастер-рендер');
      }
    } finally {
      if (masterCreated) await refreshEverything();
      if (pollingRef.current === polling) pollingRef.current = null;
      if (!keepJobControls) setBusy(null);
    }
  };

  const handlePreview = async () => {
    if (!activeRender) return;
    setBusy('preview');
    setPreviewError(null);
    try {
      await makePreview(activeRender.id);
      await refreshEverything();
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : 'Не удалось создать browser preview');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-emerald-300" />
            <p className="text-xs uppercase tracking-[0.18em] text-emerald-400">Authoritative render / export</p>
          </div>
          <h3 className="mt-2 text-lg font-medium text-slate-100">Собрать принятые правки в один мастер</h3>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            Accept остаётся лёгкой записью non-destructive edit state. Только эта явная операция запускает локальный FFmpeg и одним проходом материализует все принятые диапазоны текущего исходника. Browser preview затем кодируется из этого мастера, а не повторяет монтаж.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <button
            type="button"
            onClick={() => void handleRender()}
            disabled={busy !== null || accepted.length === 0}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy === 'render' ? <Loader2 size={16} className="animate-spin" /> : <Film size={16} />}
            {busy === 'render' ? renderJobLabel(renderJobStatus) : renders.length ? 'Пересобрать мастер' : 'Собрать мастер'}
          </button>
          {busy === 'render' && renderJobId && (
            <button
              type="button"
              onClick={() => void handleCancelRender()}
              disabled={renderJobStatus === 'cancelling' || renderJobStatus === 'cancelled'}
              className="rounded-xl border border-red-800 bg-red-950/30 px-4 py-2.5 text-sm font-medium text-red-200 transition hover:border-red-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {renderJobStatus === 'cancelling' ? 'Останавливаем…' : 'Отменить рендер'}
            </button>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <RenderStat label="Принято правок" value={accepted.length} />
        <RenderStat label="Мастер-рендеров" value={renders.length} />
        <RenderStat
          label="Состояние"
          value={!activeRender ? 'не собран' : currentRevision ? 'актуален' : 'устарел'}
          accent={activeRender && currentRevision ? 'ok' : activeRender ? 'warn' : undefined}
        />
      </div>

      {accepted.length === 0 && (
        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-xs leading-5 text-slate-500">
          Сначала доведите хотя бы одно изменение через Brief → Plan → Candidate → Review → Accept. Рендер не создаёт или не принимает правки сам.
        </div>
      )}

      {renderNotice && (
        <div className="mt-4 rounded-xl border border-sky-900/70 bg-sky-950/30 p-3 text-xs leading-5 text-sky-200">
          {renderNotice}
          {renderJobId && busy === 'render' && (
            <span className="ml-2 font-mono text-[10px] text-sky-500">job {renderJobId.slice(-10)}</span>
          )}
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-xl border border-red-900/70 bg-red-950/40 p-3 text-xs leading-5 text-red-200">
          {error}
        </div>
      )}
      {previewError && (
        <div className="mt-4 rounded-xl border border-amber-900/70 bg-amber-950/30 p-3 text-xs leading-5 text-amber-200">
          {previewError}
        </div>
      )}

      {activeRender && (
        <div className={`mt-4 rounded-xl border p-4 ${
          currentRevision
            ? 'border-emerald-900/70 bg-emerald-950/20'
            : 'border-amber-900/70 bg-amber-950/20'
        }`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className={`text-xs font-medium ${currentRevision ? 'text-emerald-300' : 'text-amber-300'}`}>
                {currentRevision ? 'Мастер соответствует текущему Accepted state' : 'Мастер устарел — Accepted state изменился'}
              </p>
              <p className="mt-1 font-mono text-[10px] text-slate-600">{activeRender.id}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {!activePreview && (
                <button
                  type="button"
                  onClick={() => void handlePreview()}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-2 rounded-lg border border-sky-800 bg-sky-950/30 px-3 py-2 text-xs text-sky-200 transition hover:border-sky-600 disabled:opacity-40"
                >
                  {busy === 'preview' ? <Loader2 size={14} className="animate-spin" /> : <MonitorPlay size={14} />}
                  Создать preview
                </button>
              )}
              <a
                href={projectArtifactMediaUrl(projectId, activeRender.id)}
                download={`${source.id}-uv-master.mkv`}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500"
              >
                <Download size={14} />
                Скачать мастер
              </a>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[10px] text-slate-500">
            <span>edits: {renderedIds.length}</span>
            {actualDurationUs !== null && <span>duration: {formatTimelineTime(actualDurationUs)}</span>}
            {compositionMode && <span>{compositionMode}</span>}
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-slate-800 bg-black">
            {activePreview ? (
              <video
                key={activePreview.id}
                src={projectArtifactMediaUrl(projectId, activePreview.id)}
                controls
                playsInline
                preload="metadata"
                className="aspect-video w-full object-contain"
              />
            ) : (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-8 text-center">
                <MonitorPlay size={22} className="text-slate-600" />
                <p className="mt-3 text-xs leading-5 text-slate-400">
                  Authoritative master хранится в FFV1/FLAC. Для гарантированного просмотра в браузере создаётся отдельный MP4 preview непосредственно из мастера.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function RenderStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: 'ok' | 'warn';
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p>
      <p className={`mt-1.5 text-sm font-medium ${
        accent === 'ok' ? 'text-emerald-300' : accent === 'warn' ? 'text-amber-300' : 'text-slate-300'
      }`}>
        {value}
      </p>
    </div>
  );
}
