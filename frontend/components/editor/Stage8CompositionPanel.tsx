'use client';

import { useEffect, useMemo, useState } from 'react';
import { uploadProjectSource } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  getStage8RecipeWorkspace,
  saveStage8RecipeWorkspace,
  type Stage8CompositionRecipeId,
} from '@/lib/stage8WorkspaceApi';
import {
  uploadProjectImageSource,
  uploadStage8AudioSource,
} from '@/lib/stage8MediaApi';

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original ? original : source.path.split('/').pop() || source.id;
}

const recipeCopy: Record<Stage8CompositionRecipeId, { title: string; description: string; briefLabel: string }> = {
  story_video: {
    title: 'Сюжетный workspace',
    description: 'Зафиксируйте задачу, сценарий и материалы истории. Сцены, continuity и generation остаются отдельными существующими UV capabilities.',
    briefLabel: 'Задача / идея истории',
  },
  commercial_product: {
    title: 'Продуктовый workspace',
    description: 'Зафиксируйте рекламную задачу, текст и точные продуктовые материалы до генерации или сборки.',
    briefLabel: 'Что рекламируем и какой результат нужен?',
  },
  free_project: {
    title: 'Свободный workspace',
    description: 'Соберите исходные материалы и заметки без навязанного pipeline. Дальше используются только выбранные semantic capabilities.',
    briefLabel: 'Задача / заметка (необязательно)',
  },
};

interface Stage8CompositionPanelProps {
  projectId: string;
  recipeId: Stage8CompositionRecipeId;
  sources: ProjectReference[];
  onProjectChanged: () => Promise<void> | void;
}

export function Stage8CompositionPanel({
  projectId,
  recipeId,
  sources,
  onProjectChanged,
}: Stage8CompositionPanelProps) {
  const copy = recipeCopy[recipeId];
  const mediaSources = useMemo(
    () => sources.filter(source => source.kind === 'image' || source.kind === 'video' || source.kind === 'audio'),
    [sources],
  );
  const [brief, setBrief] = useState('');
  const [script, setScript] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [revision, setRevision] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getStage8RecipeWorkspace(projectId)
      .then(workspace => {
        if (!active) return;
        if (workspace) {
          setBrief(workspace.brief);
          setScript(workspace.script);
          setSelectedIds(workspace.sources.map(source => source.source_id));
          setRevision(workspace.revision_sha256);
        }
        setLoaded(true);
      })
      .catch(err => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Не удалось загрузить workspace');
        setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const selectNewSource = (sourceId: string) => {
    setSelectedIds(current => current.includes(sourceId) ? current : [...current, sourceId]);
  };

  const uploadImage = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const source = await uploadProjectImageSource(projectId, file);
      selectNewSource(source.id);
      await onProjectChanged();
      setMessage('Изображение добавлено в project-owned материалы.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить изображение');
    } finally {
      setBusy(false);
    }
  };

  const uploadVideo = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const source = await uploadProjectSource(projectId, file);
      selectNewSource(source.id);
      await onProjectChanged();
      setMessage('Видео добавлено в project-owned материалы.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить видео');
    } finally {
      setBusy(false);
    }
  };

  const uploadAudio = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const source = await uploadStage8AudioSource(projectId, file);
      selectNewSource(source.id);
      await onProjectChanged();
      setMessage('Аудио добавлено в project-owned материалы.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить аудио');
    } finally {
      setBusy(false);
    }
  };

  const toggleSource = (sourceId: string) => {
    setSelectedIds(current =>
      current.includes(sourceId)
        ? current.filter(item => item !== sourceId)
        : [...current, sourceId],
    );
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const workspace = await saveStage8RecipeWorkspace(projectId, {
        brief,
        script,
        source_ids: selectedIds.filter(id => mediaSources.some(source => source.id === id)),
      });
      setRevision(workspace.revision_sha256);
      setSelectedIds(workspace.sources.map(source => source.source_id));
      setMessage('Workspace сохранён с точной SHA-привязкой выбранных материалов.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить workspace');
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) {
    return (
      <section className="mb-6 mt-8 rounded-2xl border border-cyan-900/60 bg-cyan-950/20 p-6 text-sm text-slate-400">
        Загрузка recipe workspace…
      </section>
    );
  }

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-cyan-900/60 bg-cyan-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-cyan-400">Stage 8 · composition-first</p>
      <h2 className="mt-2 text-xl font-medium">{copy.title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{copy.description}</p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-sm text-slate-300">
          {copy.briefLabel}
          <textarea
            aria-label="Stage 8 brief"
            value={brief}
            required={recipeId !== 'free_project'}
            onChange={event => setBrief(event.target.value)}
            rows={6}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
        <label className="text-sm text-slate-300">
          Сценарий / текст (необязательно)
          <textarea
            aria-label="Stage 8 script"
            value={script}
            onChange={event => setScript(event.target.value)}
            rows={6}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить изображение</span>
          <input aria-label="Stage 8 workspace image" type="file" accept="image/*" disabled={busy} onChange={event => void uploadImage(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
        </label>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить видео</span>
          <input aria-label="Stage 8 workspace video" type="file" accept="video/*" disabled={busy} onChange={event => void uploadVideo(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
        </label>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить аудио</span>
          <input aria-label="Stage 8 workspace audio" type="file" accept="audio/*" disabled={busy} onChange={event => void uploadAudio(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
        </label>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-sm font-medium text-slate-200">Материалы workspace</h3>
          <span className="text-xs text-slate-500">Выбрано: {selectedIds.length}</span>
        </div>
        {mediaSources.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Материалов пока нет.</p>
        ) : (
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {mediaSources.map(source => (
              <label key={source.id} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-300">
                <input
                  aria-label={`Использовать ${sourceName(source)}`}
                  type="checkbox"
                  checked={selectedIds.includes(source.id)}
                  onChange={() => toggleSource(source.id)}
                />
                <span className="min-w-0 flex-1 truncate">{sourceName(source)}</span>
                <span className="text-xs text-slate-600">{source.kind}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      <button
        type="button"
        disabled={busy || (recipeId !== 'free_project' && !brief.trim())}
        onClick={() => void save()}
        className="mt-6 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        Сохранить workspace
      </button>

      {revision && (
        <p className="mt-4 break-all font-mono text-xs text-slate-500">
          revision {revision}
        </p>
      )}
      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </section>
  );
}
