'use client';

import { Download, Film, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getEditorState, type EditorState } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import { EditorRenderPanel } from './EditorRenderPanel';

interface ProjectExportWorkspaceProps {
  projectId: string;
  archiveUrl: string;
  onProjectChanged?: () => void | Promise<void>;
}

function sourceName(source: ProjectReference): string {
  const originalName = source.metadata.original_name;
  return typeof originalName === 'string' && originalName.trim() ? originalName : source.path.split('/').at(-1) ?? source.id;
}

export function ProjectExportWorkspace({
  projectId,
  archiveUrl,
  onProjectChanged,
}: ProjectExportWorkspaceProps) {
  const [state, setState] = useState<EditorState | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const refresh = useCallback(async () => {
    const next = await getEditorState(projectId);
    setState(next);
    setSelectedSourceId(current => {
      if (current && next.sources.some(source => source.id === current && source.kind === 'video')) return current;
      return next.sources.find(source => source.kind === 'video')?.id ?? '';
    });
    return next;
  }, [projectId]);

  useEffect(() => {
    let active = true;
    getEditorState(projectId)
      .then(next => {
        if (!active) return;
        setState(next);
        setSelectedSourceId(next.sources.find(source => source.kind === 'video')?.id ?? '');
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить результаты проекта');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const videos = useMemo(() => state?.sources.filter(source => source.kind === 'video') ?? [], [state]);
  const selectedSource = videos.find(source => source.id === selectedSourceId) ?? videos[0] ?? null;

  const manualRefresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось обновить результаты');
    } finally {
      setRefreshing(false);
    }
  };

  if (!state) {
    return (
      <div className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-500">
        {error ?? 'Загрузка результатов…'}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-4 rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-600">Результат</p>
          <h2 className="mt-2 text-xl font-medium text-zinc-100">Сборка и экспорт</h2>
          <p className="mt-1 text-sm text-zinc-500">Соберите принятые изменения в мастер-файл или сохраните весь проект переносимым архивом.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void manualRefresh()}
            disabled={refreshing}
            className="inline-flex h-10 items-center gap-2 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] px-3 text-sm text-zinc-400 transition hover:text-zinc-200 disabled:opacity-40"
          >
            <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            Обновить
          </button>
          <a
            href={archiveUrl}
            download
            className="inline-flex h-10 items-center gap-2 rounded-xl border border-[var(--uv-border-strong)] bg-[var(--uv-surface-1)] px-3 text-sm text-zinc-300 transition hover:bg-[var(--uv-surface-2)]"
          >
            <Download size={15} />
            Архив проекта
          </a>
        </div>
      </section>

      {error && (
        <div className="rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      )}

      {videos.length === 0 ? (
        <section className="rounded-2xl border border-dashed border-[var(--uv-border-strong)] bg-[var(--uv-surface-0)] p-10 text-center">
          <Film size={28} className="mx-auto text-zinc-700" />
          <h3 className="mt-3 text-sm font-medium text-zinc-300">Пока нечего собирать</h3>
          <p className="mt-1 text-sm text-zinc-600">Добавьте видео в «Монтаже» или создайте результат в рабочем режиме проекта.</p>
        </section>
      ) : selectedSource ? (
        <>
          {videos.length > 1 && (
            <label className="block max-w-md text-xs text-zinc-600">
              Исходное видео
              <select
                value={selectedSource.id}
                onChange={event => setSelectedSourceId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] px-3 py-2.5 text-sm text-zinc-300"
              >
                {videos.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
          )}
          <EditorRenderPanel
            projectId={projectId}
            editorState={state}
            source={selectedSource}
            onStateChanged={refresh}
            onProjectChanged={onProjectChanged}
          />
        </>
      ) : null}
    </div>
  );
}
