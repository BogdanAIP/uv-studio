'use client';

import { FileText, Image as ImageIcon, Music2, Upload, Video } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { uploadProjectSource } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  getStage8RecipeWorkspace,
  saveStage8RecipeWorkspace,
  type Stage8CompositionRecipeId,
} from '@/lib/stage8WorkspaceApi';
import { uploadProjectImageSource, uploadStage8AudioSource } from '@/lib/stage8MediaApi';

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original ? original : source.path.split('/').pop() || source.id;
}

const recipeCopy: Record<Stage8CompositionRecipeId, { title: string; description: string; briefLabel: string }> = {
  story_video: {
    title: 'История и материалы',
    description: 'Сформулируйте идею, при необходимости добавьте сценарий и выберите материалы, которые относятся к этой истории.',
    briefLabel: 'Идея или задача истории',
  },
  commercial_product: {
    title: 'Задача и материалы продукта',
    description: 'Зафиксируйте рекламную задачу, текст и точные материалы продукта до дальнейшей сборки или генерации.',
    briefLabel: 'Что рекламируем и какой результат нужен?',
  },
  free_project: {
    title: 'Материалы и заметки',
    description: 'Соберите исходники и заметки без навязанного процесса. Используйте только те инструменты, которые нужны в этом проекте.',
    briefLabel: 'Задача или заметка (необязательно)',
  },
};

interface Stage8CompositionPanelProps {
  projectId: string;
  recipeId: Stage8CompositionRecipeId;
  sources: ProjectReference[];
  onProjectChanged: () => Promise<void> | void;
}

export function Stage8CompositionPanel({ projectId, recipeId, sources, onProjectChanged }: Stage8CompositionPanelProps) {
  const copy = recipeCopy[recipeId];
  const mediaSources = useMemo(
    () => sources.filter(source => source.kind === 'image' || source.kind === 'video' || source.kind === 'audio'),
    [sources],
  );
  const [brief, setBrief] = useState('');
  const [script, setScript] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
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
        }
        setLoaded(true);
      })
      .catch(err => {
        if (!active) return;
        setError(err instanceof Error ? err.message : 'Не удалось загрузить подготовку проекта');
        setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const selectNewSource = (sourceId: string) => {
    setSelectedIds(current => current.includes(sourceId) ? current : [...current, sourceId]);
  };

  const upload = async (kind: 'image' | 'video' | 'audio', file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const source = kind === 'image'
        ? await uploadProjectImageSource(projectId, file)
        : kind === 'audio'
          ? await uploadStage8AudioSource(projectId, file)
          : await uploadProjectSource(projectId, file);
      selectNewSource(source.id);
      await onProjectChanged();
      setMessage('Материал добавлен в проект.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить материал');
    } finally {
      setBusy(false);
    }
  };

  const toggleSource = (sourceId: string) => {
    setSelectedIds(current => current.includes(sourceId) ? current.filter(item => item !== sourceId) : [...current, sourceId]);
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
      setSelectedIds(workspace.sources.map(source => source.source_id));
      setMessage('Подготовка проекта сохранена.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить подготовку проекта');
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) {
    return <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-600">Загрузка материалов…</section>;
  }

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><FileText size={17} /></span>
        <div>
          <h2 className="text-lg font-medium text-zinc-100">{copy.title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">{copy.description}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-xs text-zinc-500">
          {copy.briefLabel}
          <textarea
            aria-label="Stage 8 brief"
            value={brief}
            required={recipeId !== 'free_project'}
            onChange={event => setBrief(event.target.value)}
            rows={6}
            placeholder="Опишите задачу понятным языком…"
            className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-3 text-sm leading-6 text-zinc-200 placeholder:text-zinc-700 focus:border-violet-400/50"
          />
        </label>
        <label className="text-xs text-zinc-500">
          Сценарий или текст (необязательно)
          <textarea
            aria-label="Stage 8 script"
            value={script}
            onChange={event => setScript(event.target.value)}
            rows={6}
            placeholder="Текст, сценарий, реплики или дополнительные заметки…"
            className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-3 text-sm leading-6 text-zinc-200 placeholder:text-zinc-700 focus:border-violet-400/50"
          />
        </label>
      </div>

      <div className="mt-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3 className="text-sm font-medium text-zinc-300">Материалы</h3>
            <p className="mt-1 text-xs text-zinc-700">Добавьте исходники и отметьте те, которые относятся к этой задаче.</p>
          </div>
          <span className="text-xs text-zinc-700">Выбрано: {selectedIds.length}</span>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <UploadTile icon={ImageIcon} label="Изображение" accept="image/*" ariaLabel="Stage 8 workspace image" disabled={busy} onFile={file => void upload('image', file)} />
          <UploadTile icon={Video} label="Видео" accept="video/*" ariaLabel="Stage 8 workspace video" disabled={busy} onFile={file => void upload('video', file)} />
          <UploadTile icon={Music2} label="Аудио" accept="audio/*" ariaLabel="Stage 8 workspace audio" disabled={busy} onFile={file => void upload('audio', file)} />
        </div>

        {mediaSources.length === 0 ? (
          <div className="mt-4 rounded-xl border border-dashed border-[var(--uv-border)] px-4 py-7 text-center text-sm text-zinc-700">Материалов пока нет.</div>
        ) : (
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {mediaSources.map(source => (
              <label key={source.id} className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-black/10 px-3 py-2.5 text-sm text-zinc-400 transition hover:bg-white/[0.02]">
                <input aria-label={`Использовать ${sourceName(source)}`} type="checkbox" checked={selectedIds.includes(source.id)} onChange={() => toggleSource(source.id)} />
                <span className="min-w-0 flex-1 truncate">{sourceName(source)}</span>
                <span className="text-[10px] text-zinc-700">{source.kind === 'image' ? 'изображение' : source.kind === 'video' ? 'видео' : 'аудио'}</span>
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={busy || (recipeId !== 'free_project' && !brief.trim())}
          onClick={() => void save()}
          className="rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
        >
          {busy ? 'Сохраняем…' : 'Сохранить подготовку'}
        </button>
        {recipeId !== 'free_project' && !brief.trim() && <span className="text-xs text-zinc-700">Сначала опишите задачу.</span>}
      </div>

      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
    </section>
  );
}

function UploadTile({ icon: Icon, label, accept, ariaLabel, disabled, onFile }: { icon: typeof Upload; label: string; accept: string; ariaLabel: string; disabled: boolean; onFile: (file: File | undefined) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] px-3 py-3 text-sm text-zinc-400 transition hover:border-[var(--uv-border-strong)] hover:text-zinc-200">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-black/15 text-zinc-600"><Icon size={15} /></span>
      <span className="flex-1">Добавить {label.toLowerCase()}</span>
      <Upload size={14} className="text-zinc-700" />
      <input aria-label={ariaLabel} type="file" accept={accept} disabled={disabled} onChange={event => onFile(event.target.files?.[0])} className="hidden" />
    </label>
  );
}
