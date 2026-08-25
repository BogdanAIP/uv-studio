'use client';

import Image from 'next/image';
import Link from 'next/link';
import {
  AudioLines,
  Bot,
  Film,
  ImageIcon,
  Loader2,
  MonitorPlay,
  Plus,
  Redo2,
  Scissors,
  Trash2,
  Undo2,
  Upload,
  Video,
} from 'lucide-react';
import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getUVProject, type ProjectReference, type UVProject } from '@/lib/projectsApi';
import {
  executeStudioTimelineCommand,
  getProjectHistory,
  getStudioMLTProjection,
  getStudioTimeline,
  inferStudioMediaKind,
  renderStudioTimeline,
  redoProjectHistory,
  studioExportMediaUrl,
  studioSourceMediaUrl,
  type StudioMLTProjection,
  type ProjectHistoryState,
  type StudioRenderResult,
  type StudioTimeline,
  type StudioTimelineClip,
  type StudioTimelineTrack,
  undoProjectHistory,
  uploadStudioMedia,
} from '@/lib/timelineApi';

const IMAGE_DEFAULT_DURATION_US = 3_000_000;
const EMPTY_TIMELINE_SCALE_US = 10_000_000;

function metadataNumber(reference: ProjectReference | null, key: string): number | null {
  if (!reference) return null;
  const value = reference.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(reference: ProjectReference | null, key: string): string | null {
  if (!reference) return null;
  const value = reference.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function seconds(us: number): string {
  return (us / 1_000_000).toFixed(us % 1_000_000 === 0 ? 0 : 2);
}

function clock(us: number): string {
  const total = Math.max(0, us) / 1_000_000;
  const minutes = Math.floor(total / 60);
  const secs = total - minutes * 60;
  return `${String(minutes).padStart(2, '0')}:${secs.toFixed(2).padStart(5, '0')}`;
}

function sourceLabel(reference: ProjectReference): string {
  return metadataText(reference, 'original_name') ?? reference.id;
}

function compatibleTrackKind(reference: ProjectReference | null): 'video' | 'audio' | null {
  if (!reference) return null;
  if (reference.kind === 'audio') return 'audio';
  if (reference.kind === 'video' || reference.kind === 'image') return 'video';
  return null;
}

function defaultClipDuration(reference: ProjectReference): number | null {
  if (reference.kind === 'image') return IMAGE_DEFAULT_DURATION_US;
  const duration = metadataNumber(reference, 'duration_us');
  return duration && duration > 0 ? Math.round(duration) : null;
}

function trackEnd(track: StudioTimelineTrack): number {
  return track.clips.reduce(
    (maximum, clip) => Math.max(maximum, clip.timeline_start_us + clip.duration_us),
    0,
  );
}

function mediaIcon(kind: string) {
  if (kind === 'image') return <ImageIcon size={16} />;
  if (kind === 'audio') return <AudioLines size={16} />;
  return <Video size={16} />;
}

interface LocatedClip {
  track: StudioTimelineTrack;
  clip: StudioTimelineClip;
}

function locateClip(timeline: StudioTimeline | null, clipId: string | null): LocatedClip | null {
  if (!timeline || !clipId) return null;
  for (const track of timeline.tracks) {
    const clip = track.clips.find(item => item.clip_id === clipId);
    if (clip) return { track, clip };
  }
  return null;
}

export function StudioWorkspace({ projectId }: { projectId: string }) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [project, setProject] = useState<UVProject | null>(null);
  const [timeline, setTimeline] = useState<StudioTimeline | null>(null);
  const [engine, setEngine] = useState<StudioMLTProjection | null>(null);
  const [history, setHistory] = useState<ProjectHistoryState | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null);
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [preferredTrackId, setPreferredTrackId] = useState('');
  const [moveStartSec, setMoveStartSec] = useState('0');
  const [trimSourceSec, setTrimSourceSec] = useState('0');
  const [trimDurationSec, setTrimDurationSec] = useState('1');
  const [latestRender, setLatestRender] = useState<StudioRenderResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [projectValue, timelineValue, historyValue] = await Promise.all([
      getUVProject(projectId),
      getStudioTimeline(projectId),
      getProjectHistory(projectId),
    ]);
    setProject(projectValue);
    setTimeline(timelineValue);
    setHistory(historyValue);
    setLatestRender(current =>
      current && projectValue.artifacts.some(artifact => artifact.id === current.artifact.id)
        ? current
        : null,
    );
    setSelectedSourceId(current =>
      current && projectValue.sources.some(source => source.id === current)
        ? current
        : projectValue.sources[0]?.id ?? null,
    );
    setSelectedClipId(current =>
      current && locateClip(timelineValue, current) ? current : null,
    );
    try {
      const engineValue = await getStudioMLTProjection(projectId);
      setEngine(engineValue);
      setEngineError(null);
    } catch (err) {
      setEngine(null);
      setEngineError(err instanceof Error ? err.message : 'MLT-проекция недоступна');
    }
    return { project: projectValue, timeline: timelineValue };
  }, [projectId]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void refresh()
        .catch(err => {
          if (active) setError(err instanceof Error ? err.message : 'Не удалось открыть Studio');
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [refresh]);

  const selectedSource = useMemo(
    () => project?.sources.find(source => source.id === selectedSourceId) ?? null,
    [project, selectedSourceId],
  );
  const locatedClip = useMemo(
    () => locateClip(timeline, selectedClipId),
    [timeline, selectedClipId],
  );
  const selectedClipReference = useMemo(() => {
    if (!project || !locatedClip) return null;
    return project.sources.find(source => source.id === locatedClip.clip.reference_id)
      ?? project.artifacts.find(artifact => artifact.id === locatedClip.clip.reference_id)
      ?? null;
  }, [locatedClip, project]);
  const previewReference = selectedClipReference ?? selectedSource;

  const compatibleTracks = useMemo(() => {
    const kind = compatibleTrackKind(selectedSource);
    if (!timeline || !kind) return [];
    return timeline.tracks.filter(track => track.kind === kind);
  }, [selectedSource, timeline]);

  const targetTrackId = useMemo(() => {
    if (preferredTrackId && compatibleTracks.some(track => track.track_id === preferredTrackId)) {
      return preferredTrackId;
    }
    return compatibleTracks[0]?.track_id ?? '';
  }, [compatibleTracks, preferredTrackId]);

  const timelineDuration = useMemo(() => {
    if (!timeline) return 0;
    return timeline.tracks.reduce((maximum, track) => Math.max(maximum, trackEnd(track)), 0);
  }, [timeline]);
  const timelineScale = Math.max(timelineDuration, EMPTY_TIMELINE_SCALE_US);

  const persistedStudioExport = useMemo(() => {
    if (!project) return null;
    return project.artifacts
      .filter(artifact => artifact.kind === 'video' && artifact.metadata.role === 'studio-export')
      .at(-1) ?? null;
  }, [project]);
  const visibleExport = latestRender?.artifact ?? persistedStudioExport;

  const previewUrl = useMemo(() => {
    if (!project || !previewReference) return null;
    if (project.sources.some(source => source.id === previewReference.id)) {
      return studioSourceMediaUrl(projectId, previewReference);
    }
    if (previewReference.kind === 'video' && previewReference.metadata.role === 'studio-export') {
      return studioExportMediaUrl(projectId, previewReference.id);
    }
    return null;
  }, [previewReference, project, projectId]);

  async function mutate(operation: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await operation();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить проект');
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    event.target.value = '';
    if (!file || busy) return;
    const kind = inferStudioMediaKind(file);
    if (!kind) {
      setError('Не удалось определить тип файла. Поддерживаются видео, изображения и аудио.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const reference = await uploadStudioMedia(projectId, file, kind);
      await refresh();
      setSelectedSourceId(reference.id);
      setSelectedClipId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать файл');
    } finally {
      setBusy(false);
    }
  }

  function chooseClip(track: StudioTimelineTrack, clip: StudioTimelineClip, reference: ProjectReference | null) {
    setSelectedClipId(clip.clip_id);
    if (reference && project?.sources.some(source => source.id === reference.id)) {
      setSelectedSourceId(reference.id);
    }
    setMoveStartSec(seconds(clip.timeline_start_us));
    setTrimSourceSec(seconds(clip.source_start_us));
    setTrimDurationSec(seconds(clip.duration_us));
    setPreferredTrackId(track.track_id);
  }

  function createTrack(kind: 'video' | 'audio') {
    void mutate(async () => {
      const result = await executeStudioTimelineCommand(projectId, {
        command: 'create_track',
        kind,
      });
      if (result.track_id) setPreferredTrackId(result.track_id);
    });
  }

  function addSelectedSource() {
    if (!selectedSource || !targetTrackId || busy || !timeline) return;
    const duration = defaultClipDuration(selectedSource);
    if (!duration) {
      setError('У этого медиа нет корректной длительности для добавления на timeline.');
      return;
    }
    const track = timeline.tracks.find(item => item.track_id === targetTrackId);
    if (!track) return;
    const startUs = trackEnd(track);
    void mutate(async () => {
      const result = await executeStudioTimelineCommand(projectId, {
        command: 'add_clip',
        track_id: targetTrackId,
        reference_id: selectedSource.id,
        timeline_start_us: startUs,
        source_start_us: 0,
        duration_us: duration,
      });
      if (result.clip_id) {
        setSelectedClipId(result.clip_id);
        setMoveStartSec(seconds(startUs));
        setTrimSourceSec('0');
        setTrimDurationSec(seconds(duration));
      }
    });
  }

  function saveMove() {
    if (!locatedClip || busy) return;
    const value = Number(moveStartSec);
    if (!Number.isFinite(value) || value < 0) {
      setError('Начало клипа должно быть неотрицательным числом секунд.');
      return;
    }
    void mutate(() =>
      executeStudioTimelineCommand(projectId, {
        command: 'move_clip',
        clip_id: locatedClip.clip.clip_id,
        timeline_start_us: Math.round(value * 1_000_000),
      }),
    );
  }

  function saveTrim() {
    if (!locatedClip || busy) return;
    const start = Number(trimSourceSec);
    const duration = Number(trimDurationSec);
    if (!Number.isFinite(start) || start < 0 || !Number.isFinite(duration) || duration <= 0) {
      setError('Начало исходника должно быть ≥ 0, а длительность — больше нуля.');
      return;
    }
    void mutate(() =>
      executeStudioTimelineCommand(projectId, {
        command: 'trim_clip',
        clip_id: locatedClip.clip.clip_id,
        source_start_us: Math.round(start * 1_000_000),
        duration_us: Math.round(duration * 1_000_000),
      }),
    );
  }

  function removeSelectedClip() {
    if (!locatedClip || busy) return;
    void mutate(async () => {
      await executeStudioTimelineCommand(projectId, {
        command: 'remove_clip',
        clip_id: locatedClip.clip.clip_id,
      });
      setSelectedClipId(null);
    });
  }

  function undo() {
    if (!history?.can_undo || busy) return;
    void mutate(() => undoProjectHistory(projectId));
  }

  function redo() {
    if (!history?.can_redo || busy) return;
    void mutate(() => redoProjectHistory(projectId));
  }

  async function renderTimeline() {
    if (rendering || busy) return;
    setRendering(true);
    setError(null);
    try {
      const result = await renderStudioTimeline(projectId);
      setLatestRender(result);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось экспортировать ролик');
    } finally {
      setRendering(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100">
        <div className="flex min-h-screen items-center justify-center gap-3 text-slate-400">
          <Loader2 className="animate-spin" size={20} /> Открываем Studio…
        </div>
      </main>
    );
  }

  if (!project || !timeline) {
    return (
      <main className="min-h-screen bg-slate-950 p-8 text-slate-100">
        <div className="mx-auto max-w-3xl rounded-2xl border border-red-900/70 bg-red-950/30 p-6 text-red-200">
          {error ?? 'Не удалось загрузить Studio-проект.'}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1800px] px-3 py-4 sm:px-5">
        <header className="mb-4 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <Link href="/projects" className="text-sm text-slate-400 hover:text-sky-300">← Проекты</Link>
              <span className="text-slate-700">/</span>
              <span className="text-xs uppercase tracking-[0.18em] text-sky-400">Studio</span>
            </div>
            <h1 className="mt-1 truncate text-xl font-semibold">{project.title}</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <div className="inline-flex overflow-hidden rounded-lg border border-slate-700 bg-slate-950">
              <button
                type="button"
                onClick={undo}
                disabled={busy || !history?.can_undo}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-slate-300 transition hover:bg-slate-800 hover:text-sky-300 disabled:cursor-not-allowed disabled:opacity-35"
                title="Отменить последнее действие проекта"
                aria-label="Отменить последнее действие проекта"
              >
                <Undo2 size={15} /> Отменить
              </button>
              <button
                type="button"
                onClick={redo}
                disabled={busy || !history?.can_redo}
                className="inline-flex items-center gap-1.5 border-l border-slate-700 px-3 py-2 text-slate-300 transition hover:bg-slate-800 hover:text-sky-300 disabled:cursor-not-allowed disabled:opacity-35"
                title="Повторить отменённое действие проекта"
                aria-label="Повторить отменённое действие проекта"
              >
                <Redo2 size={15} /> Повторить
              </button>
            </div>
            <span className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1.5 text-slate-400">
              timeline/main.json · v{timeline.schema_version}
            </span>
            {engine ? (
              <span className="rounded-full border border-emerald-900/70 bg-emerald-950/40 px-3 py-1.5 text-emerald-300">
                MLT {engine.frame_rate} · {engine.width}×{engine.height}
              </span>
            ) : (
              <span className="rounded-full border border-amber-900/70 bg-amber-950/40 px-3 py-1.5 text-amber-300">
                MLT projection blocked
              </span>
            )}
            <button
              type="button"
              onClick={() => void renderTimeline()}
              disabled={rendering || busy}
              className="inline-flex items-center gap-2 rounded-lg bg-sky-400 px-4 py-2 font-semibold text-slate-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {rendering ? <Loader2 size={15} className="animate-spin" /> : <MonitorPlay size={15} />}
              {rendering ? 'Экспорт…' : 'Экспортировать'}
            </button>
          </div>
        </header>

        {error && (
          <div className="mb-4 rounded-xl border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}
        {engineError && (
          <div className="mb-4 rounded-xl border border-amber-900/70 bg-amber-950/30 px-4 py-3 text-xs text-amber-200">
            MLT: {engineError}
          </div>
        )}

        <div className="grid min-h-[520px] gap-3 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
          <aside className="rounded-2xl border border-slate-800 bg-slate-900/50 p-3">
            <div className="flex items-center justify-between gap-3 px-1 py-1">
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">Media Bin</p>
                <p className="mt-1 text-sm text-slate-300">{project.sources.length} файлов</p>
              </div>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
                className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-950 text-slate-300 hover:border-sky-600 hover:text-sky-300 disabled:opacity-40"
                title="Импортировать медиа"
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              </button>
              <input
                ref={fileInputRef}
                aria-label="Импортировать медиа в Studio"
                type="file"
                accept="video/*,image/*,audio/*,.mkv,.mxf,.mts,.m2ts,.flac,.wav"
                className="hidden"
                onChange={event => void handleUpload(event)}
              />
            </div>

            <div className="mt-3 max-h-[440px] space-y-2 overflow-y-auto pr-1">
              {project.sources.length === 0 ? (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex w-full flex-col items-center rounded-xl border border-dashed border-slate-700 bg-slate-950/50 px-4 py-8 text-center hover:border-sky-700"
                >
                  <Upload size={24} className="text-slate-600" />
                  <span className="mt-3 text-sm text-slate-300">Добавить медиа</span>
                  <span className="mt-1 text-xs leading-5 text-slate-600">Видео, изображения или аудио</span>
                </button>
              ) : (
                project.sources.map(source => {
                  const selected = source.id === selectedSourceId && !selectedClipId;
                  const duration = metadataNumber(source, 'duration_us');
                  return (
                    <button
                      type="button"
                      key={source.id}
                      onClick={() => {
                        setSelectedSourceId(source.id);
                        setSelectedClipId(null);
                      }}
                      className={`w-full rounded-xl border p-3 text-left transition ${
                        selected
                          ? 'border-sky-500/70 bg-sky-950/35'
                          : 'border-slate-800 bg-slate-950/55 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-slate-300">
                        <span className={source.kind === 'audio' ? 'text-violet-300' : 'text-sky-300'}>
                          {mediaIcon(source.kind)}
                        </span>
                        <span className="min-w-0 flex-1 truncate text-sm">{sourceLabel(source)}</span>
                      </div>
                      <div className="mt-2 flex items-center justify-between gap-2 font-mono text-[10px] text-slate-600">
                        <span>{source.kind}</span>
                        {duration ? <span>{clock(duration)}</span> : null}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </aside>

          <section className="min-w-0 rounded-2xl border border-slate-800 bg-black p-3">
            <div className="relative flex min-h-[440px] items-center justify-center overflow-hidden rounded-xl bg-black">
              {!previewReference ? (
                <div className="text-center text-slate-600">
                  <Film size={42} className="mx-auto" />
                  <p className="mt-3 text-sm">Выберите медиа или клип на timeline</p>
                </div>
              ) : !previewUrl ? (
                <div className="max-w-lg px-8 text-center text-sm leading-6 text-slate-500">
                  Этот зарегистрированный артефакт пока не имеет безопасного Studio preview endpoint.
                </div>
              ) : previewReference.kind === 'image' ? (
                <div className="relative h-[440px] w-full">
                  <Image
                    src={previewUrl}
                    alt={sourceLabel(previewReference)}
                    fill
                    unoptimized
                    className="object-contain"
                  />
                </div>
              ) : previewReference.kind === 'audio' ? (
                <div className="w-full max-w-xl px-8 text-center">
                  <AudioLines size={48} className="mx-auto text-violet-400" />
                  <p className="mt-4 truncate text-sm text-slate-300">{sourceLabel(previewReference)}</p>
                  <audio key={previewReference.id} controls className="mt-6 w-full" src={previewUrl} />
                </div>
              ) : (
                <video
                  key={previewReference.id}
                  controls
                  playsInline
                  preload="metadata"
                  className="max-h-[440px] w-full object-contain"
                  src={previewUrl}
                />
              )}
            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 px-1 text-xs text-slate-500">
              <span>{previewReference ? sourceLabel(previewReference) : 'Preview'}</span>
              {locatedClip ? (
                <span className="font-mono">
                  clip {clock(locatedClip.clip.timeline_start_us)} → {clock(locatedClip.clip.timeline_start_us + locatedClip.clip.duration_us)}
                </span>
              ) : null}
            </div>
          </section>

          <aside className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
            <div className="flex items-center gap-2">
              <Scissors size={16} className="text-sky-300" />
              <div>
                <p className="text-xs uppercase tracking-wider text-slate-500">Inspector</p>
                <p className="mt-0.5 text-sm text-slate-300">
                  {locatedClip ? 'Клип на timeline' : selectedSource ? 'Медиафайл' : 'Ничего не выбрано'}
                </p>
              </div>
            </div>

            {locatedClip ? (
              <div className="mt-5 space-y-5">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs">
                  <p className="truncate text-slate-300">
                    {selectedClipReference ? sourceLabel(selectedClipReference) : locatedClip.clip.reference_id}
                  </p>
                  <p className="mt-1 font-mono text-slate-600">{locatedClip.clip.clip_id}</p>
                  <p className="mt-2 text-slate-500">Track: {locatedClip.track.title}</p>
                </div>

                <label className="block text-xs text-slate-500">
                  Позиция на timeline, сек
                  <div className="mt-2 flex gap-2">
                    <input
                      aria-label="Позиция клипа на timeline"
                      value={moveStartSec}
                      onChange={event => setMoveStartSec(event.target.value)}
                      inputMode="decimal"
                      className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-sky-500"
                    />
                    <button
                      type="button"
                      onClick={saveMove}
                      disabled={busy}
                      className="rounded-lg border border-slate-700 px-3 text-xs hover:border-sky-600 disabled:opacity-40"
                    >
                      Переместить
                    </button>
                  </div>
                </label>

                <div>
                  <p className="text-xs text-slate-500">Обрезка исходника</p>
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    <label className="text-[10px] text-slate-600">
                      начало, сек
                      <input
                        aria-label="Начало исходника"
                        value={trimSourceSec}
                        onChange={event => setTrimSourceSec(event.target.value)}
                        inputMode="decimal"
                        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
                      />
                    </label>
                    <label className="text-[10px] text-slate-600">
                      длительность, сек
                      <input
                        aria-label="Длительность клипа"
                        value={trimDurationSec}
                        onChange={event => setTrimDurationSec(event.target.value)}
                        inputMode="decimal"
                        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
                      />
                    </label>
                  </div>
                  <button
                    type="button"
                    onClick={saveTrim}
                    disabled={busy}
                    className="mt-2 w-full rounded-lg border border-slate-700 py-2 text-xs hover:border-sky-600 disabled:opacity-40"
                  >
                    Применить trim
                  </button>
                </div>

                <button
                  type="button"
                  onClick={removeSelectedClip}
                  disabled={busy}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-red-900/70 bg-red-950/30 py-2 text-xs text-red-300 hover:bg-red-950/50 disabled:opacity-40"
                >
                  <Trash2 size={14} /> Удалить клип
                </button>
              </div>
            ) : selectedSource ? (
              <div className="mt-5 space-y-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="break-words text-sm text-slate-300">{sourceLabel(selectedSource)}</p>
                  <p className="mt-2 font-mono text-[10px] text-slate-600">{selectedSource.id}</p>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
                    <span>Тип</span><span className="text-right text-slate-300">{selectedSource.kind}</span>
                    {metadataNumber(selectedSource, 'duration_us') ? (
                      <><span>Длительность</span><span className="text-right text-slate-300">{clock(metadataNumber(selectedSource, 'duration_us') ?? 0)}</span></>
                    ) : null}
                    {metadataNumber(selectedSource, 'width') ? (
                      <><span>Размер</span><span className="text-right text-slate-300">{metadataNumber(selectedSource, 'width')}×{metadataNumber(selectedSource, 'height')}</span></>
                    ) : null}
                  </div>
                </div>

                {compatibleTracks.length === 0 ? (
                  <div className="rounded-xl border border-amber-900/60 bg-amber-950/25 p-3 text-xs leading-5 text-amber-200">
                    Создайте {compatibleTrackKind(selectedSource) === 'audio' ? 'Audio' : 'Video'} track, затем добавьте файл на timeline.
                  </div>
                ) : (
                  <>
                    <label className="block text-xs text-slate-500">
                      Добавить на дорожку
                      <select
                        aria-label="Дорожка для добавления"
                        value={targetTrackId}
                        onChange={event => setPreferredTrackId(event.target.value)}
                        className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
                      >
                        {compatibleTracks.map(track => (
                          <option key={track.track_id} value={track.track_id}>{track.title}</option>
                        ))}
                      </select>
                    </label>
                    <button
                      type="button"
                      onClick={addSelectedSource}
                      disabled={busy}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-400 py-2.5 text-sm font-semibold text-slate-950 hover:bg-sky-300 disabled:opacity-40"
                    >
                      <Plus size={15} /> Добавить в конец дорожки
                    </button>
                  </>
                )}
              </div>
            ) : null}

            <div className="mt-6 border-t border-slate-800 pt-5">
              <div className="flex items-center gap-2">
                <Bot size={16} className="text-violet-300" />
                <p className="text-sm font-medium text-slate-300">AI Tools</p>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Здесь появятся генерация и AI-редактирование после backend Model Registry. Конкретная модель будет выбираться здесь, а не скрываться настройками capability.
              </p>
              <div className="mt-3 rounded-lg border border-dashed border-slate-700 px-3 py-2 text-[11px] text-slate-600">
                Model Registry ещё не подключён — кнопки генерации намеренно не имитируются.
              </div>
            </div>
          </aside>
        </div>

        <section className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/55 p-3">
          <div className="mb-3 flex flex-col gap-3 px-1 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500">Timeline</p>
              <p className="mt-1 font-mono text-xs text-slate-400">{clock(timelineDuration)} · {timeline.tracks.length} tracks</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => createTrack('video')}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs hover:border-sky-600 disabled:opacity-40"
              >
                <Video size={14} /> <Plus size={12} /> Video track
              </button>
              <button
                type="button"
                onClick={() => createTrack('audio')}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs hover:border-violet-600 disabled:opacity-40"
              >
                <AudioLines size={14} /> <Plus size={12} /> Audio track
              </button>
            </div>
          </div>

          {timeline.tracks.length === 0 ? (
            <div className="flex min-h-28 items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-5 text-center text-sm text-slate-500">
              Timeline пуст. Создайте Video или Audio track — это каноническое состояние проекта, а не локальная разметка браузера.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
              <div className="min-w-[900px]">
                <div className="grid grid-cols-[150px_minmax(0,1fr)] border-b border-slate-800 text-[10px] text-slate-600">
                  <div className="border-r border-slate-800 px-3 py-2">TRACK</div>
                  <div className="flex justify-between px-2 py-2 font-mono">
                    <span>00:00</span>
                    <span>{clock(timelineScale / 4)}</span>
                    <span>{clock(timelineScale / 2)}</span>
                    <span>{clock((timelineScale * 3) / 4)}</span>
                    <span>{clock(timelineScale)}</span>
                  </div>
                </div>
                {timeline.tracks.map(track => (
                  <div key={track.track_id} className="grid grid-cols-[150px_minmax(0,1fr)] border-b border-slate-800 last:border-b-0">
                    <div className="flex min-h-16 items-center gap-2 border-r border-slate-800 px-3">
                      {track.kind === 'video' ? <Video size={14} className="text-sky-300" /> : <AudioLines size={14} className="text-violet-300" />}
                      <div className="min-w-0">
                        <p className="truncate text-xs text-slate-300">{track.title}</p>
                        <p className="mt-1 truncate font-mono text-[9px] text-slate-700">{track.track_id}</p>
                      </div>
                    </div>
                    <div className="relative min-h-16 overflow-hidden bg-[linear-gradient(to_right,rgba(51,65,85,0.18)_1px,transparent_1px)] bg-[length:25%_100%]">
                      {track.clips.map(clip => {
                        const reference = project.sources.find(item => item.id === clip.reference_id)
                          ?? project.artifacts.find(item => item.id === clip.reference_id)
                          ?? null;
                        const left = (clip.timeline_start_us / timelineScale) * 100;
                        const width = Math.max((clip.duration_us / timelineScale) * 100, 1.2);
                        const selected = clip.clip_id === selectedClipId;
                        const label = reference ? sourceLabel(reference) : clip.reference_id;
                        return (
                          <button
                            type="button"
                            key={clip.clip_id}
                            aria-label={`Клип ${label}`}
                            onClick={() => chooseClip(track, clip, reference)}
                            className={`absolute top-2 h-12 overflow-hidden rounded-md border px-2 text-left text-[10px] transition ${
                              selected
                                ? 'z-10 border-white/80 bg-sky-500/35 ring-2 ring-sky-400/30'
                                : track.kind === 'audio'
                                  ? 'border-violet-700/70 bg-violet-950/60 hover:border-violet-500'
                                  : 'border-sky-800/70 bg-sky-950/60 hover:border-sky-600'
                            }`}
                            style={{ left: `${left}%`, width: `${width}%` }}
                            title={`${label} · ${clock(clip.duration_us)}`}
                          >
                            <span className="block truncate text-slate-200">{label}</span>
                            <span className="mt-1 block font-mono text-slate-500">{clock(clip.duration_us)}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="mt-3 grid gap-3 lg:grid-cols-[1fr_360px]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
            <p className="text-xs uppercase tracking-wider text-slate-500">Export truth</p>
            <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
              Первый Studio renderer намеренно ограничен: одна активная непрерывная Video-дорожка и максимум одна Audio-дорожка, покрывающая весь ролик. Gaps, overlays и несколько активных visual tracks блокируются вместо скрытого упрощения.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
            {visibleExport ? (
              <div>
                <p className="text-xs uppercase tracking-wider text-emerald-400">Последний экспорт</p>
                <p className="mt-2 truncate font-mono text-[10px] text-slate-600">{visibleExport.id}</p>
                <Link
                  href={studioExportMediaUrl(projectId, visibleExport.id)}
                  target="_blank"
                  className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-sky-300 hover:text-sky-200"
                >
                  <MonitorPlay size={15} /> Открыть экспорт
                </Link>
              </div>
            ) : (
              <div className="text-sm text-slate-600">Экспортов ещё нет.</div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
