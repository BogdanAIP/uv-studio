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

type RecipeCopy = {
  title: string;
  description: string;
  briefLabel: string;
  startHint: string;
};

const recipeCopy: Record<Stage8CompositionRecipeId, RecipeCopy> = {
  general_video: {
    title: 'Обычный видеоролик',
    description: 'Соберите простой ролик из собственных изображений и видео. Отдельную аудиодорожку можно добавить как звук итогового ролика.',
    briefLabel: 'Что нужно показать в ролике?',
    startHint: 'Начните с описания задачи. Для итоговой локальной сборки нужен хотя бы один собственный визуальный материал — изображение или видео. Эта сборка пока не создаёт кадры автоматически только из текста.',
  },
  story_video: {
    title: 'Подготовка сюжетного видео',
    description: 'Здесь фиксируются идея, сценарий и материалы будущей истории.',
    briefLabel: 'Задача / идея истории',
    startHint: 'Начать можно без файлов: опишите идею и сохраните задачу. Изображения, видео и аудио ниже — необязательные собственные референсы или готовые материалы. В текущей сборке этот режим подготавливает историю, но ещё не создаёт финальный сюжетный ролик целиком.',
  },
  commercial_product: {
    title: 'Подготовка рекламного ролика',
    description: 'Зафиксируйте рекламную задачу, текст и точные материалы продукта до дальнейшей генерации или сборки.',
    briefLabel: 'Что рекламируем и какой результат нужен?',
    startHint: 'Начать можно с одного описания задачи. Фото, видео и аудио ниже нужны только если у вас уже есть исходники или референсы, которые обязательно надо использовать.',
  },
  free_project: {
    title: 'Свободный проект',
    description: 'Соберите заметки и исходные материалы без обязательного сценария производства.',
    briefLabel: 'Задача / заметка (необязательно)',
    startHint: 'Все поля и файлы в этом режиме необязательны. Используйте его как контейнер проекта, если пока не хотите выбирать конкретный путь производства.',
  },
  narrated_video: {
    title: 'Видео с дикторской дорожкой',
    description: 'Зафиксируйте задачу и точный текст диктора, затем добавьте нужные визуальные материалы.',
    briefLabel: 'Тема / задача ролика',
    startHint: 'Для начала нужны задача и текст диктора. Изображения используются как визуальный ряд; загруженное видео пока сохраняется как материал проекта, но не включается в итоговый мастер автоматически.',
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
  const sourceById = useMemo(
    () => new Map(mediaSources.map(source => [source.id, source])),
    [mediaSources],
  );
  const narrated = recipeId === 'narrated_video';
  const general = recipeId === 'general_video';
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
        setError(err instanceof Error ? err.message : 'Не удалось загрузить данные задачи');
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
      setMessage('Изображение добавлено в материалы проекта.');
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
      setMessage(
        narrated
          ? 'Видео сохранено как материал проекта. Этот режим пока не включает его в итоговый мастер автоматически.'
          : 'Видео добавлено в материалы проекта.',
      );
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
      setMessage('Аудио добавлено в материалы проекта.');
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

  const moveSelected = (sourceId: string, offset: -1 | 1) => {
    setSelectedIds(current => {
      const index = current.indexOf(sourceId);
      const target = index + offset;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
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
      setMessage('Задача и выбранные материалы сохранены.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить задачу');
    } finally {
      setBusy(false);
    }
  };

  if (!loaded) {
    return (
      <section className="mb-6 mt-8 rounded-2xl border border-cyan-900/60 bg-cyan-950/20 p-6 text-sm text-slate-400">
        Загрузка задачи…
      </section>
    );
  }

  const orderedVisualIds = selectedIds.filter(id => {
    const kind = sourceById.get(id)?.kind;
    return kind === 'image' || kind === 'video';
  });

  const mediaAreOptional = !general;

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-cyan-900/60 bg-cyan-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-cyan-400">Начните здесь</p>
      <h2 className="mt-2 text-xl font-medium">{copy.title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{copy.description}</p>
      <div className="mt-4 max-w-4xl rounded-xl border border-sky-900/70 bg-sky-950/30 px-4 py-3 text-sm leading-6 text-sky-100">
        {copy.startHint}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="text-sm text-slate-300">
          {copy.briefLabel}
          <textarea
            aria-label="Описание задачи"
            value={brief}
            required={recipeId !== 'free_project'}
            onChange={event => setBrief(event.target.value)}
            rows={6}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
        <label className="text-sm text-slate-300">
          {narrated ? 'Текст диктора (обязательно)' : 'Сценарий / текст (необязательно)'}
          <textarea
            aria-label="Сценарий или текст"
            value={script}
            required={narrated}
            onChange={event => setScript(event.target.value)}
            rows={6}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          />
        </label>
      </div>

      <div className="mt-6">
        <h3 className="text-sm font-medium text-slate-200">Свои материалы</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          {mediaAreOptional
            ? 'Необязательно. Добавляйте только те исходники или референсы, которые уже есть у вас и должны использоваться в проекте.'
            : 'Для локальной сборки обычного видеоролика нужен хотя бы один визуальный исходник — изображение или видео. Аудио необязательно.'}
        </p>
      </div>

      <div className={`mt-3 grid gap-3 ${narrated ? 'sm:grid-cols-2' : 'sm:grid-cols-3'}`}>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить своё изображение{mediaAreOptional ? ' · необязательно' : ''}</span>
          <span className="mt-1 block text-xs leading-5 text-slate-500">Готовый кадр, фото продукта, референс или другое изображение.</span>
          <input aria-label="Добавить своё изображение" type="file" accept="image/*" disabled={busy} onChange={event => void uploadImage(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
        </label>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить своё видео{mediaAreOptional ? ' · необязательно' : ''}</span>
          <span className="mt-1 block text-xs leading-5 text-slate-500">
            {narrated ? 'Сохранится как материал проекта; автоматическое включение в мастер пока не поддерживается.' : 'Готовый клип или видео-референс.'}
          </span>
          <input aria-label="Добавить своё видео" type="file" accept="video/*" disabled={busy} onChange={event => void uploadVideo(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
        </label>
        {!narrated && (
          <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
            <span className="block font-medium">Добавить своё аудио · необязательно</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Музыка, речь или другая готовая аудиодорожка.</span>
            <input aria-label="Добавить своё аудио" type="file" accept="audio/*" disabled={busy} onChange={event => void uploadAudio(event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
          </label>
        )}
      </div>

      {general && orderedVisualIds.length > 0 && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
          <h3 className="text-sm font-medium text-slate-200">Порядок визуального ряда</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Изображение занимает 2 секунды; видео используется целиком. Стрелками задайте последовательность первого локального ролика.
          </p>
          <div className="mt-3 space-y-2">
            {orderedVisualIds.map((sourceId, visualIndex) => {
              const source = sourceById.get(sourceId);
              if (!source) return null;
              const selectedIndex = selectedIds.indexOf(sourceId);
              return (
                <div key={sourceId} className="flex items-center gap-3 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300">
                  <span className="w-6 text-right font-mono text-xs text-slate-600">{visualIndex + 1}</span>
                  <span className="min-w-0 flex-1 truncate">{sourceName(source)}</span>
                  <span className="text-xs text-slate-600">{source.kind}</span>
                  <button
                    type="button"
                    aria-label={`Поднять ${sourceName(source)}`}
                    disabled={busy || selectedIndex <= 0}
                    onClick={() => moveSelected(sourceId, -1)}
                    className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30"
                  >↑</button>
                  <button
                    type="button"
                    aria-label={`Опустить ${sourceName(source)}`}
                    disabled={busy || selectedIndex < 0 || selectedIndex >= selectedIds.length - 1}
                    onClick={() => moveSelected(sourceId, 1)}
                    className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30"
                  >↓</button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-6">
        <div className="flex items-center justify-between gap-4">
          <h3 className="text-sm font-medium text-slate-200">Материалы проекта</h3>
          <span className="text-xs text-slate-500">Выбрано: {selectedIds.length}</span>
        </div>
        {mediaSources.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">Вы пока не добавляли свои материалы.</p>
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
        disabled={busy || (recipeId !== 'free_project' && !brief.trim()) || (narrated && !script.trim())}
        onClick={() => void save()}
        className="mt-6 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        Сохранить задачу
      </button>

      {revision && (
        <details className="mt-4 text-xs text-slate-500">
          <summary className="cursor-pointer select-none">Технические данные сохранённой версии</summary>
          <p className="mt-2 break-all font-mono">revision {revision}</p>
        </details>
      )}
      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </section>
  );
}
