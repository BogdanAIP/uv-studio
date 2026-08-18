'use client';

import { Bot, Film, Pause, Play, Scissors, Upload } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getEditorState,
  projectSourceMediaUrl,
  selectProjectRange,
  uploadProjectSource,
} from '@/lib/editorApi';
import type { RangeContinuityBrief, SelectRangeResult } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import { formatTimelineTime } from '@/lib/timelineMath';
import { RangeTimeline } from './RangeTimeline';
import type { TimelineSelection } from './RangeTimeline';
import { ReplacementWorkflowPanel } from './ReplacementWorkflowPanel';

interface ProjectEditorProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

function metadataNumber(source: ProjectReference | null, key: string): number | null {
  if (!source) return null;
  const value = source.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(source: ProjectReference, key: string): string | null {
  const value = source.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

export function ProjectEditor({ projectId, onProjectChanged }: ProjectEditorProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [editorState, setEditorState] = useState<Awaited<ReturnType<typeof getEditorState>> | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selection, setSelection] = useState<TimelineSelection | null>(null);
  const [playheadUs, setPlayheadUs] = useState(0);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [changeRequest, setChangeRequest] = useState('');
  const [contextBeforeSeconds, setContextBeforeSeconds] = useState(5);
  const [contextAfterSeconds, setContextAfterSeconds] = useState(5);
  const [latestResult, setLatestResult] = useState<SelectRangeResult | null>(null);
  const [loadedProjectId, setLoadedProjectId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const refreshState = useCallback(async () => {
    const next = await getEditorState(projectId);
    setEditorState(next);
    setSelectedSourceId(current =>
      current && next.sources.some(source => source.id === current)
        ? current
        : next.sources[0]?.id ?? null,
    );
    return next;
  }, [projectId]);

  useEffect(() => {
    let active = true;
    getEditorState(projectId)
      .then(next => {
        if (!active) return;
        setEditorState(next);
        setSelectedSourceId(next.sources[0]?.id ?? null);
        setLoadedProjectId(projectId);
      })
      .catch(err => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Не удалось открыть редактор');
        setLoadedProjectId(projectId);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const activeSource = useMemo(
    () => editorState?.sources.find(source => source.id === selectedSourceId) ?? null,
    [editorState, selectedSourceId],
  );
  const durationUs = metadataNumber(activeSource, 'duration_us') ?? 0;
  const sourceName = activeSource ? metadataText(activeSource, 'original_name') ?? activeSource.id : '';
  const activeBriefs = useMemo(
    () => activeSource ? (editorState?.briefs ?? []).filter(brief => brief.source_path === activeSource.path) : [],
    [activeSource, editorState],
  );
  const activeAccepted = useMemo(
    () => activeSource ? (editorState?.accepted_edits ?? []).filter(edit => edit.source_path === activeSource.path) : [],
    [activeSource, editorState],
  );

  const activateSource = (sourceId: string) => {
    if (sourceId === selectedSourceId) return;
    videoRef.current?.pause();
    setSelectedSourceId(sourceId);
    setSelection(null);
    setPlayheadUs(0);
    setLatestResult(null);
    setPreviewError(null);
    setPlaying(false);
  };

  const seekTo = (timeUs: number) => {
    const safeUs = Math.min(durationUs, Math.max(0, Math.round(timeUs)));
    setPlayheadUs(safeUs);
    if (videoRef.current) videoRef.current.currentTime = safeUs / 1_000_000;
  };

  const togglePlayback = async () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      await video.play().catch(err => {
        setPreviewError(err instanceof Error ? err.message : 'Не удалось воспроизвести этот файл в окне просмотра');
      });
    } else {
      video.pause();
    }
  };

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const imported = await uploadProjectSource(projectId, file);
      await refreshState();
      activateSource(imported.id);
      await onProjectChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить видео');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handlePrepareRange = async () => {
    if (!activeSource || !selection || selection.endUs <= selection.startUs || !changeRequest.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await selectProjectRange(projectId, {
        source_id: activeSource.id,
        start_us: selection.startUs,
        end_us: selection.endUs,
        change_request: changeRequest.trim(),
        context_before_us: Math.round(contextBeforeSeconds * 1_000_000),
        context_after_us: Math.round(contextAfterSeconds * 1_000_000),
      });
      setLatestResult(result);
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось подготовить изменение');
    } finally {
      setSubmitting(false);
    }
  };

  const loading = loadedProjectId !== projectId;
  if (loading) {
    return (
      <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-500">
        Открываем монтаж…
      </section>
    );
  }

  const actionHint = !activeSource
    ? 'Сначала добавьте видео.'
    : !selection || selection.endUs <= selection.startUs
      ? 'Выделите нужный фрагмент на таймлайне.'
      : !changeRequest.trim()
        ? 'Опишите, что нужно изменить.'
        : null;

  return (
    <section className="overflow-hidden rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] shadow-2xl shadow-black/20">
      <div className="flex flex-col gap-3 border-b border-[var(--uv-border)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-medium text-zinc-200">Монтаж</h2>
          <p className="mt-0.5 text-xs text-zinc-600">Материалы, просмотр, выделение и точечные AI-изменения.</p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mkv,.mxf,.mts,.m2ts"
            className="hidden"
            onChange={event => void handleUpload(event.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border-strong)] bg-[var(--uv-surface-1)] px-3 text-xs font-medium text-zinc-300 transition hover:bg-[var(--uv-surface-2)] disabled:opacity-40"
          >
            <Upload size={14} />
            {uploading ? 'Добавляем…' : 'Добавить видео'}
          </button>
        </div>
      </div>

      {error && (
        <div className="m-4 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      )}

      {!editorState || editorState.sources.length === 0 ? (
        <div className="flex min-h-[560px] items-center justify-center p-6">
          <div className="max-w-md text-center">
            <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] text-zinc-600">
              <Film size={24} />
            </span>
            <h3 className="mt-5 text-base font-medium text-zinc-200">Добавьте первое видео</h3>
            <p className="mt-2 text-sm leading-6 text-zinc-600">Оно появится в медиатеке и сразу откроется в окне просмотра.</p>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="mt-5 inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:opacity-40"
            >
              <Upload size={16} />
              Выбрать видео
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid min-h-[520px] xl:grid-cols-[230px_minmax(0,1fr)_340px]">
            <aside className="border-b border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-3 xl:border-b-0 xl:border-r">
              <div className="flex items-center justify-between px-2 py-2">
                <h3 className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-500">Медиатека</h3>
                <span className="rounded-md bg-black/20 px-2 py-0.5 text-[10px] text-zinc-600">{editorState.sources.length}</span>
              </div>
              <div className="mt-1 space-y-1.5">
                {editorState.sources.map(source => {
                  const name = metadataText(source, 'original_name') ?? source.id;
                  const sourceDuration = metadataNumber(source, 'duration_us') ?? 0;
                  const dimensions = [metadataNumber(source, 'width'), metadataNumber(source, 'height')]
                    .filter((value): value is number => value !== null)
                    .join('×');
                  return (
                    <button
                      type="button"
                      key={source.id}
                      onClick={() => activateSource(source.id)}
                      className={`w-full rounded-xl border p-3 text-left transition ${
                        source.id === selectedSourceId
                          ? 'border-violet-400/35 bg-violet-400/10'
                          : 'border-transparent bg-black/10 hover:border-[var(--uv-border)] hover:bg-white/[0.025]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Film size={14} className={source.id === selectedSourceId ? 'text-violet-300' : 'text-zinc-700'} />
                        <p className="min-w-0 flex-1 truncate text-xs font-medium text-zinc-300">{name}</p>
                      </div>
                      <p className="mt-2 text-[10px] text-zinc-700">
                        {formatTimelineTime(sourceDuration, false)}{dimensions ? ` · ${dimensions}` : ''}
                      </p>
                    </button>
                  );
                })}
              </div>
            </aside>

            <div className="min-w-0 bg-[#050506] p-3 sm:p-4">
              <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-xl bg-black shadow-inner">
                {activeSource && (
                  <video
                    key={activeSource.id}
                    ref={videoRef}
                    src={projectSourceMediaUrl(projectId, activeSource.id)}
                    className="h-full w-full object-contain"
                    playsInline
                    preload="metadata"
                    onTimeUpdate={event => setPlayheadUs(Math.round(event.currentTarget.currentTime * 1_000_000))}
                    onPlay={() => setPlaying(true)}
                    onPause={() => setPlaying(false)}
                    onEnded={() => setPlaying(false)}
                    onError={() => setPreviewError('Этот формат нельзя показать прямо в окне просмотра. Файл остаётся доступен для обработки и экспорта.')}
                  />
                )}
                {previewError && (
                  <div className="absolute inset-x-5 bottom-5 rounded-xl border border-amber-400/20 bg-amber-950/90 p-3 text-xs leading-5 text-amber-100">{previewError}</div>
                )}
              </div>
              <div className="mt-3 flex items-center gap-3 px-1">
                <button
                  type="button"
                  onClick={() => void togglePlayback()}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-zinc-100 text-zinc-950 transition hover:bg-white"
                  aria-label={playing ? 'Пауза' : 'Воспроизвести'}
                >
                  {playing ? <Pause size={15} /> : <Play size={15} className="ml-0.5" />}
                </button>
                <span className="font-mono text-xs text-zinc-300">{formatTimelineTime(playheadUs)}</span>
                <span className="text-xs text-zinc-800">/</span>
                <span className="font-mono text-xs text-zinc-600">{formatTimelineTime(durationUs)}</span>
                {selection && selection.endUs > selection.startUs && (
                  <button
                    type="button"
                    onClick={() => seekTo(selection.startUs)}
                    className="ml-auto rounded-lg border border-[var(--uv-border)] px-3 py-1.5 text-xs text-zinc-500 transition hover:text-zinc-300"
                  >
                    К выделению
                  </button>
                )}
              </div>
            </div>

            <aside className="border-t border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 xl:border-l xl:border-t-0">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-400/10 text-violet-300">
                  <Bot size={16} />
                </span>
                <div>
                  <h3 className="text-sm font-medium text-zinc-200">AI-изменение</h3>
                  <p className="text-[10px] text-zinc-700">Работает с выбранным диапазоном</p>
                </div>
              </div>

              <label className="mt-5 block text-xs text-zinc-500" htmlFor="uv-change-request">Что нужно изменить?</label>
              <textarea
                id="uv-change-request"
                value={changeRequest}
                onChange={event => setChangeRequest(event.target.value)}
                rows={6}
                maxLength={4000}
                placeholder="Например: заменить объект в кадре, сохранив движение камеры и освещение…"
                className="mt-2 w-full resize-y rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-3 text-sm leading-5 text-zinc-200 placeholder:text-zinc-700 transition focus:border-violet-400/50"
              />

              <details className="mt-3 rounded-xl border border-[var(--uv-border)] bg-black/10 px-3 py-2.5 text-xs text-zinc-600">
                <summary className="cursor-pointer select-none text-zinc-500">Контекст вокруг фрагмента</summary>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <ContextInput label="До, с" value={contextBeforeSeconds} onChange={setContextBeforeSeconds} />
                  <ContextInput label="После, с" value={contextAfterSeconds} onChange={setContextAfterSeconds} />
                </div>
              </details>

              <div className="mt-3 rounded-xl border border-[var(--uv-border)] bg-black/15 p-3 text-xs leading-5 text-zinc-600">
                {selection && selection.endUs > selection.startUs ? (
                  <>Выбрано <span className="font-mono text-violet-300">{formatTimelineTime(selection.startUs)}</span> — <span className="font-mono text-violet-300">{formatTimelineTime(selection.endUs)}</span></>
                ) : 'Протяните мышью по таймлайну, чтобы выбрать фрагмент.'}
              </div>

              <button
                type="button"
                disabled={Boolean(actionHint) || submitting}
                onClick={() => void handlePrepareRange()}
                className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
              >
                <Scissors size={15} />
                {submitting ? 'Подготавливаем…' : 'Подготовить изменение'}
              </button>
              {actionHint && <p className="mt-2 text-center text-[11px] text-zinc-700">{actionHint}</p>}

              <ChangeSummary briefs={activeBriefs} acceptedCount={activeAccepted.length} latestResult={latestResult} />
            </aside>
          </div>

          {activeSource && durationUs > 0 && (
            <div className="border-t border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-3 sm:p-4">
              <RangeTimeline
                durationUs={durationUs}
                sourceName={sourceName}
                sourcePath={activeSource.path}
                playheadUs={playheadUs}
                selection={selection}
                zoomLevel={zoomLevel}
                briefs={activeBriefs}
                acceptedEdits={activeAccepted}
                onSeek={seekTo}
                onSelectionChange={setSelection}
                onZoomChange={setZoomLevel}
              />
            </div>
          )}

          {activeSource && activeBriefs.length > 0 && (
            <div className="border-t border-[var(--uv-border)] p-3 sm:p-4">
              <ReplacementWorkflowPanel
                projectId={projectId}
                editorState={editorState}
                sourcePath={activeSource.path}
                preferredEditId={latestResult?.edit_id}
                onStateChanged={refreshState}
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ContextInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="text-[11px] text-zinc-600">
      {label}
      <input
        type="number"
        min={0}
        max={30}
        step={0.5}
        value={value}
        onChange={event => onChange(Math.min(30, Math.max(0, Number(event.target.value) || 0)))}
        className="mt-1.5 w-full rounded-lg border border-[var(--uv-border)] bg-[var(--uv-surface-0)] px-2 py-2 font-mono text-xs text-zinc-300 focus:border-violet-400/50"
      />
    </label>
  );
}

function ChangeSummary({
  briefs,
  acceptedCount,
  latestResult,
}: {
  briefs: RangeContinuityBrief[];
  acceptedCount: number;
  latestResult: SelectRangeResult | null;
}) {
  const latestBrief = latestResult?.brief ?? briefs[briefs.length - 1] ?? null;
  const requestedChange = latestBrief?.constraints.find(item => item.constraint_id === 'requested_change');

  return (
    <div className="mt-5 border-t border-[var(--uv-border)] pt-4">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-zinc-600">Изменения</span>
        <span className="text-zinc-500">{briefs.length} подготовлено · {acceptedCount} применено</span>
      </div>
      {latestBrief && (
        <div className="mt-3 rounded-xl border border-violet-400/15 bg-violet-400/[0.06] p-3">
          <p className="text-[11px] font-medium text-violet-200">Последняя задача подготовлена</p>
          {requestedChange && <p className="mt-1.5 line-clamp-3 text-xs leading-5 text-zinc-500">{requestedChange.requirement}</p>}
          <p className="mt-2 text-[10px] text-zinc-700">Ниже таймлайна можно создать предпросмотр, проверить его и применить.</p>
        </div>
      )}
    </div>
  );
}
