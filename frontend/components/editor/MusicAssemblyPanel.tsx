'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { getUVProject, type ProjectReference } from '@/lib/projectsApi';
import {
  executeMusicAssemblyCommand,
  getMusicAssembly,
  getMusicDirection,
  projectVideoArtifactUrl,
  renderMusicVideo,
  uploadProjectVideoSource,
  type MusicAssemblyState,
  type MusicDirectionState,
} from '@/lib/musicVideoApi';

interface MusicAssemblyPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

interface AssignmentDraft {
  sourceId: string;
  sourceStart: string;
}

function seconds(us: number): string {
  return (us / 1_000_000).toFixed(3).replace(/\.000$/, '');
}

function secondsToUs(value: string, field: string): number {
  const parsed = Number(value.replace(',', '.'));
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${field}: укажите неотрицательное число секунд`);
  }
  return Math.round(parsed * 1_000_000);
}

function sourceLabel(source: ProjectReference): string {
  const original = source.metadata.original_name;
  const duration = source.metadata.duration_us;
  const name = typeof original === 'string' && original.trim() ? original : source.path;
  return typeof duration === 'number' ? `${name} · ${seconds(duration)} с` : name;
}

export function MusicAssemblyPanel({ projectId, onProjectChanged }: MusicAssemblyPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [sources, setSources] = useState<ProjectReference[]>([]);
  const [direction, setDirection] = useState<MusicDirectionState | null>(null);
  const [assembly, setAssembly] = useState<MusicAssemblyState | null>(null);
  const [drafts, setDrafts] = useState<Record<string, AssignmentDraft>>({});
  const [renderedArtifact, setRenderedArtifact] = useState<ProjectReference | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [assemblyWarning, setAssemblyWarning] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [project, currentDirection] = await Promise.all([
      getUVProject(projectId),
      getMusicDirection(projectId),
    ]);
    const videoSources = project.sources.filter(reference => reference.kind === 'video');
    setSources(videoSources);
    setDirection(currentDirection);

    let currentAssembly: MusicAssemblyState | null = null;
    try {
      currentAssembly = await getMusicAssembly(projectId);
      setAssemblyWarning(null);
    } catch (reason) {
      setAssemblyWarning(reason instanceof Error ? reason.message : 'Assembly Plan устарел');
    }
    setAssembly(currentAssembly);

    const currentRender = currentAssembly
      ? project.artifacts.filter(reference => (
          reference.kind === 'video'
          && reference.metadata.lifecycle === 'music_video_render'
          && reference.metadata.music_assembly_revision_sha256 === currentAssembly.revision_sha256
        )).at(-1) ?? null
      : null;
    setRenderedArtifact(currentRender);

    if (currentDirection) {
      const byShot = new Map((currentAssembly?.bindings ?? []).map(binding => [binding.shot_id, binding]));
      setDrafts(current => Object.fromEntries(currentDirection.shots.map(shot => {
        const bound = byShot.get(shot.shot_id);
        const existing = current[shot.shot_id];
        const preferredSource = bound?.source_id
          ?? (existing && videoSources.some(source => source.id === existing.sourceId) ? existing.sourceId : '')
          ?? '';
        return [shot.shot_id, {
          sourceId: preferredSource || videoSources[0]?.id || '',
          sourceStart: bound ? seconds(bound.source_start_us) : existing?.sourceStart ?? '0',
        }];
      })));
    } else {
      setDrafts({});
      setAssembly(null);
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void refresh().catch(reason => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Не удалось загрузить Music Assembly');
        }
      });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [refresh]);

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await operation();
      await refresh();
      await onProjectChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Операция Music Assembly не выполнена');
    } finally {
      setBusy(false);
    }
  };

  const uploadVisual = (file: File) => run(async () => {
    await uploadProjectVideoSource(projectId, file);
    setNotice('Видео зарегистрировано как project-owned source и доступно для кадров Music Director.');
  });

  const saveAssembly = () => run(async () => {
    if (!direction) throw new Error('Сначала сохраните Music Director');
    const assignments = direction.shots.map((shot, index) => {
      const draft = drafts[shot.shot_id];
      if (!draft?.sourceId) throw new Error(`Кадр ${index + 1}: выберите видеоисточник`);
      return {
        shot_id: shot.shot_id,
        source_id: draft.sourceId,
        source_start_us: secondsToUs(draft.sourceStart, `Кадр ${index + 1}, начало в источнике`),
      };
    });
    const result = await executeMusicAssemblyCommand(projectId, {
      command: 'set_music_assembly',
      music_direction_revision_sha256: direction.revision_sha256,
      assignments,
    });
    if (!result.payload) throw new Error('Music Assembly Plan не был сохранён');
    setAssembly(result.payload);
    setRenderedArtifact(null);
    setNotice('Assembly Plan сохранён с точной привязкой к Music Director и SHA видеоматериалов.');
  });

  const renderCurrent = () => run(async () => {
    if (!assembly) throw new Error('Сначала сохраните текущий Music Assembly Plan');
    const envelope = await renderMusicVideo(projectId, assembly.revision_sha256);
    if (!envelope.result.artifact) throw new Error('Рендер завершился без зарегистрированного артефакта');
    setRenderedArtifact(envelope.result.artifact);
    setNotice('Музыкальный клип собран: видеоисточники без собственного звука + единственная master-песня.');
  });

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-cyan-900/60 bg-slate-900/60 p-6">
      <p className="text-xs uppercase tracking-wider text-cyan-400">Stage 7 · Music Assembly</p>
      <h2 className="mt-2 text-xl font-medium">Визуальные материалы → Assembly Plan → master-render</h2>
      <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">
        Каждый кадр Music Director связывается с проверенным project-owned видео и точным интервалом источника. Рендер игнорирует звук визуальных клипов и использует только подтверждённый excerpt master-песни.
      </p>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept="video/*,.mp4,.mov,.mkv,.webm,.avi,.m4v"
          aria-label="Видео для Music Assembly"
          className="hidden"
          onChange={event => {
            const file = event.target.files?.[0];
            if (file) void uploadVisual(file);
          }}
        />
        <button
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
          className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
        >
          Загрузить видео
        </button>
        <span className="text-xs text-slate-500">Доступно источников: {sources.length}</span>
      </div>

      {!direction ? (
        <p className="mt-5 rounded-lg border border-amber-900 bg-amber-950/20 p-4 text-sm text-amber-300">
          Сначала сохраните Music Map и Music Director выше. Assembly Plan строится только для точной текущей ревизии режиссёрского плана.
        </p>
      ) : (
        <div className="mt-6 space-y-3">
          {direction.shots.map((shot, index) => {
            const draft = drafts[shot.shot_id] ?? { sourceId: '', sourceStart: '0' };
            return (
              <div key={shot.shot_id} className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 lg:grid-cols-7">
                <div className="text-xs text-slate-500 lg:col-span-2">
                  <p className="font-mono text-slate-300">{shot.shot_id}</p>
                  <p className="mt-1">таймлайн: {seconds(shot.start_us)}–{seconds(shot.end_us)} с</p>
                  <p className="mt-1 text-slate-400">{shot.intent}</p>
                </div>
                <label className="text-xs text-slate-500 lg:col-span-3">
                  Видеоисточник
                  <select
                    aria-label={`Видеоисточник музыкального кадра ${index + 1}`}
                    value={draft.sourceId}
                    onChange={event => setDrafts(current => ({
                      ...current,
                      [shot.shot_id]: { ...draft, sourceId: event.target.value },
                    }))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                  >
                    <option value="">Выберите видео</option>
                    {sources.map(source => <option key={source.id} value={source.id}>{sourceLabel(source)}</option>)}
                  </select>
                </label>
                <label className="text-xs text-slate-500 lg:col-span-2">
                  Начало в источнике, с
                  <input
                    aria-label={`Начало источника музыкального кадра ${index + 1}`}
                    inputMode="decimal"
                    value={draft.sourceStart}
                    onChange={event => setDrafts(current => ({
                      ...current,
                      [shot.shot_id]: { ...draft, sourceStart: event.target.value },
                    }))}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                  />
                </label>
              </div>
            );
          })}

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              disabled={busy || sources.length === 0 || direction.shots.some(shot => !drafts[shot.shot_id]?.sourceId)}
              onClick={saveAssembly}
              className="rounded-lg bg-cyan-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            >
              Сохранить Assembly Plan
            </button>
            {assembly && <span className="font-mono text-xs text-slate-600">assembly {assembly.revision_sha256.slice(0, 12)}…</span>}
          </div>
        </div>
      )}

      {assemblyWarning && (
        <p className="mt-4 rounded-lg border border-amber-900 bg-amber-950/20 p-3 text-xs text-amber-300">
          Сохранённый Assembly Plan больше не текущий: {assemblyWarning}
        </p>
      )}

      {assembly && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-medium">Canonical master-render</h3>
              <p className="mt-1 text-xs text-slate-500">На сервер уходит только SHA текущего Assembly Plan; пути и таймкоды восстанавливаются из проверенного Project Store.</p>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={renderCurrent}
              className="rounded-lg bg-emerald-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            >
              Собрать клип
            </button>
          </div>
          {renderedArtifact && (
            <a
              href={projectVideoArtifactUrl(projectId, renderedArtifact.id)}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-block rounded border border-emerald-800 px-3 py-2 text-sm text-emerald-300 hover:border-emerald-600"
            >
              Открыть готовый рендер
            </a>
          )}
        </div>
      )}

      {notice && <p className="mt-5 text-sm text-emerald-300">{notice}</p>}
      {error && <p className="mt-5 text-sm text-red-300">{error}</p>}
    </section>
  );
}
