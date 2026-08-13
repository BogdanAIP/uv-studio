'use client';

import { Bot, Film, Pause, Play, Scissors, Upload } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  getEditorState,
  projectSourceMediaUrl,
  RangeContinuityBrief,
  selectProjectRange,
  SelectRangeResult,
  uploadProjectSource,
} from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import { formatTimelineTime } from '@/lib/timelineMath';
import { RangeTimeline, TimelineSelection } from './RangeTimeline';

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
  const [loading, setLoading] = useState(true);
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
    setLoading(true);
    getEditorState(projectId)
      .then(next => {
        if (!active) return;
        setEditorState(next);
        setSelectedSourceId(next.sources[0]?.id ?? null);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить редактор');
      })
      .finally(() => {
        if (active) setLoading(false);
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
    () =>
      activeSource
        ? (editorState?.briefs ?? []).filter(brief => brief.source_path === activeSource.path)
        : [],
    [activeSource, editorState],
  );
  const activeAccepted = useMemo(
    () =>
      activeSource
        ? (editorState?.accepted_edits ?? []).filter(edit => edit.source_path === activeSource.path)
        : [],
    [activeSource, editorState],
  );

  useEffect(() => {
    setSelection(null);
    setPlayheadUs(0);
    setLatestResult(null);
    setPreviewError(null);
    setPlaying(false);
  }, [selectedSourceId]);

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
        setPreviewError(err instanceof Error ? err.message : 'Браузер не смог воспроизвести файл');
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
      setSelectedSourceId(imported.id);
      await onProjectChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать видео');
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
      setError(err instanceof Error ? err.message : 'Не удалось сохранить задачу изменения');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 text-sm text-slate-400">
        Загрузка редактора…
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-slate-800 bg-slate-900/30 p-4 shadow-2xl shadow-black/20 sm:p-6">
      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-sky-400">Stage 4C · UV Editor</p>
          <h2 className="mt-2 text-2xl font-semibold">Точечное редактирование исходного видео</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Плеер, timeline и AI работают через один проектный контур. Выделение хранится в точных микросекундах и превращается в канонический Brief, а не в локальный JSON интерфейса.
          </p>
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
            className="inline-flex items-center gap-2 rounded-xl bg-sky-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Upload size={16} />
            {uploading ? 'Импорт и проверка…' : 'Импортировать видео'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-900/70 bg-red-950/50 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {!editorState || editorState.sources.length === 0 ? (
        <div className="flex min-h-72 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-950/60 px-6 text-center">
          <Film className="text-slate-600" size={40} />
          <h3 className="mt-4 text-lg font-medium">Добавьте исходное видео</h3>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
            Файл будет потоково сохранён в Project Store, проверен FFprobe и зарегистрирован под project-owned ID. Путь вашего компьютера в API не передаётся.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)_360px]">
            <aside className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
              <div className="flex items-center justify-between px-2 py-2">
                <h3 className="text-sm font-medium">Медиатека</h3>
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">
                  {editorState.sources.length}
                </span>
              </div>
              <div className="mt-1 space-y-2">
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
                      onClick={() => setSelectedSourceId(source.id)}
                      className={`w-full rounded-xl border p-3 text-left transition ${
                        source.id === selectedSourceId
                          ? 'border-sky-500/70 bg-sky-950/40'
                          : 'border-slate-800 bg-slate-900/50 hover:border-slate-700'
                      }`}
                    >
                      <p className="truncate text-sm text-slate-200">{name}</p>
                      <p className="mt-2 font-mono text-[10px] text-slate-500">
                        {formatTimelineTime(sourceDuration, false)}{dimensions ? ` · ${dimensions}` : ''}
                      </p>
                      <p className="mt-1 truncate text-[10px] text-slate-600">{metadataText(source, 'video_codec') ?? 'video'}</p>
                    </button>
                  );
                })}
              </div>
            </aside>

            <div className="min-w-0 rounded-2xl border border-slate-800 bg-black p-3">
              <div className="relative flex aspect-video items-center justify-center overflow-hidden rounded-xl bg-black">
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
                    onError={() => setPreviewError('Браузер не смог декодировать этот формат для интерактивного preview. Исходник остаётся зарегистрирован в проекте и доступен media engine.')}
                  />
                )}
                {previewError && (
                  <div className="absolute inset-x-6 bottom-6 rounded-xl border border-amber-700/70 bg-amber-950/90 p-3 text-xs leading-5 text-amber-200">
                    {previewError}
                  </div>
                )}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 px-1">
                <button
                  type="button"
                  onClick={() => void togglePlayback()}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-950 hover:bg-white"
                  aria-label={playing ? 'Пауза' : 'Воспроизвести'}
                >
                  {playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
                </button>
                <span className="font-mono text-xs text-slate-300">{formatTimelineTime(playheadUs)}</span>
                <span className="text-xs text-slate-600">/</span>
                <span className="font-mono text-xs text-slate-500">{formatTimelineTime(durationUs)}</span>
                {selection && selection.endUs > selection.startUs && (
                  <button
                    type="button"
                    onClick={() => seekTo(selection.startUs)}
                    className="ml-auto rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-500"
                  >
                    К началу выделения
                  </button>
                )}
              </div>
            </div>

            <aside className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <div className="flex items-center gap-2">
                <Bot size={18} className="text-violet-300" />
                <div>
                  <h3 className="text-sm font-medium">AI / задача изменения</h3>
                  <p className="mt-0.5 text-[10px] text-slate-500">тот же Command API, что для скриптов и MCP</p>
                </div>
              </div>

              <label className="mt-5 block text-xs text-slate-400" htmlFor="uv-change-request">
                Что должно измениться в выделенном фрагменте
              </label>
              <textarea
                id="uv-change-request"
                value={changeRequest}
                onChange={event => setChangeRequest(event.target.value)}
                rows={5}
                maxLength={4000}
                placeholder="Например: заменить объект в кадре, сохранив движение камеры, свет, звук и бесшовные границы сцены…"
                className="mt-2 w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm leading-5 text-slate-200 outline-none transition placeholder:text-slate-600 focus:border-violet-500"
              />

              <div className="mt-4 grid grid-cols-2 gap-3">
                <ContextInput
                  label="Контекст до, с"
                  value={contextBeforeSeconds}
                  onChange={setContextBeforeSeconds}
                />
                <ContextInput
                  label="Контекст после, с"
                  value={contextAfterSeconds}
                  onChange={setContextAfterSeconds}
                />
              </div>

              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs leading-5 text-slate-400">
                {selection && selection.endUs > selection.startUs ? (
                  <>
                    Выбрано <span className="font-mono text-sky-300">{formatTimelineTime(selection.startUs)}</span> —{' '}
                    <span className="font-mono text-sky-300">{formatTimelineTime(selection.endUs)}</span>.
                  </>
                ) : (
                  'Перетащите по дорожке timeline, чтобы задать диапазон.'
                )}
              </div>

              <button
                type="button"
                disabled={!selection || selection.endUs <= selection.startUs || !changeRequest.trim() || submitting}
                onClick={() => void handlePrepareRange()}
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <Scissors size={16} />
                {submitting ? 'Фиксация Brief…' : 'Подготовить изменение'}
              </button>

              <WorkflowSummary
                briefs={activeBriefs}
                acceptedCount={activeAccepted.length}
                latestResult={latestResult}
              />
            </aside>
          </div>

          {activeSource && durationUs > 0 && (
            <div className="mt-4">
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
        </>
      )}
    </section>
  );
}

function ContextInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-[11px] text-slate-500">
      {label}
      <input
        type="number"
        min={0}
        max={30}
        step={0.5}
        value={value}
        onChange={event => onChange(Math.min(30, Math.max(0, Number(event.target.value) || 0)))}
        className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 font-mono text-xs text-slate-200 outline-none focus:border-violet-500"
      />
    </label>
  );
}

function WorkflowSummary({
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
    <div className="mt-5 border-t border-slate-800 pt-4">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">Каноническое состояние</span>
        <span className="font-mono text-slate-400">Brief {briefs.length} · Accepted {acceptedCount}</span>
      </div>
      {latestBrief ? (
        <div className="mt-3 rounded-xl border border-violet-900/70 bg-violet-950/30 p-3">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-violet-200">Brief сохранён</span>
            <span className="font-mono text-[9px] text-slate-600">{latestBrief.edit_id}</span>
          </div>
          {requestedChange && (
            <p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-400">{requestedChange.requirement}</p>
          )}
          <div className="mt-3 space-y-1.5">
            {latestBrief.review_targets.map(target => (
              <div key={target.target_id} className="flex gap-2 text-[10px] leading-4 text-slate-500">
                <span className="text-violet-400">✓</span>
                <span>{target.criterion}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[10px] leading-4 text-slate-600">
            Следующие Plan → Candidate → Review используют этот же edit_id; принятие кандидата остаётся только через D-032 gate.
          </p>
        </div>
      ) : (
        <p className="mt-3 text-[11px] leading-5 text-slate-600">
          После фиксации выделения здесь появятся требования и критерии проверки для следующей части существующего workflow.
        </p>
      )}
    </div>
  );
}
