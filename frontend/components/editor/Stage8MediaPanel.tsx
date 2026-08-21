'use client';

import { useMemo, useState } from 'react';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  executeComposePhotosAction,
  executeRenderVisualizerAction,
  type WorkflowAction,
  type WorkflowPrerequisite,
} from '@/lib/productWorkflowApi';
import {
  projectStage8ArtifactUrl,
  uploadProjectImageSource,
  uploadStage8AudioSource,
} from '@/lib/stage8MediaApi';

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original ? original : source.path.split('/').pop() || source.id;
}

function actionSourceIds(action: WorkflowAction | undefined, propertyName: string): Set<string> | null {
  if (!action) return null;
  const properties = action.input_schema.properties;
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return null;
  const property = (properties as Record<string, unknown>)[propertyName];
  if (!property || typeof property !== 'object' || Array.isArray(property)) return null;
  const values = (property as Record<string, unknown>).enum;
  if (!Array.isArray(values)) return null;
  return new Set(values.filter((value): value is string => typeof value === 'string'));
}

interface Stage8MediaPanelProps {
  projectId: string;
  recipeId: 'photo_to_video' | 'visualizer';
  sources: ProjectReference[];
  workflowAction?: WorkflowAction;
  workflowPrerequisites?: WorkflowPrerequisite[];
  onProjectChanged: () => Promise<void> | void;
}

export function Stage8MediaPanel({ projectId, recipeId, sources, workflowAction, workflowPrerequisites, onProjectChanged }: Stage8MediaPanelProps) {
  const images = useMemo(() => sources.filter(source => source.kind === 'image'), [sources]);
  const audios = useMemo(() => sources.filter(source => source.kind === 'audio'), [sources]);
  const composableImages = useMemo(() => {
    if (recipeId !== 'photo_to_video' || !workflowAction) return images;
    const suggestedIds = workflowAction.suggested_input.image_source_ids;
    if (!Array.isArray(suggestedIds)) return [];
    const verifiedIds = new Set(suggestedIds.filter((value): value is string => typeof value === 'string'));
    return images.filter(source => verifiedIds.has(source.id));
  }, [images, recipeId, workflowAction]);
  const visualizerAudios = useMemo(() => {
    if (recipeId !== 'visualizer') return audios;
    const allowedIds = actionSourceIds(workflowAction, 'audio_source_id');
    if (allowedIds === null) return [];
    return audios.filter(source => allowedIds.has(source.id));
  }, [audios, recipeId, workflowAction]);
  const visualizerArtworks = useMemo(() => {
    if (recipeId !== 'visualizer') return images;
    const allowedIds = actionSourceIds(workflowAction, 'artwork_source_id');
    if (allowedIds === null) return [];
    return images.filter(source => allowedIds.has(source.id));
  }, [images, recipeId, workflowAction]);
  const suggestedVisualizerAudioId =
    typeof workflowAction?.suggested_input.audio_source_id === 'string'
      ? workflowAction.suggested_input.audio_source_id
      : '';

  const [imageOrder, setImageOrder] = useState(() => composableImages.map(source => source.id));
  const [photoAudioId, setPhotoAudioId] = useState('');
  const [durationSeconds, setDurationSeconds] = useState('2');
  const [visualizerAudioId, setVisualizerAudioId] = useState(
    () => suggestedVisualizerAudioId || visualizerAudios[0]?.id || '',
  );
  const [artworkId, setArtworkId] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);

  const orderedImageIds = useMemo(() => {
    const availableIds = new Set(composableImages.map(source => source.id));
    const preserved = imageOrder.filter(sourceId => availableIds.has(sourceId));
    const preservedIds = new Set(preserved);
    const appended = composableImages
      .map(source => source.id)
      .filter(sourceId => !preservedIds.has(sourceId));
    return [...preserved, ...appended];
  }, [imageOrder, composableImages]);
  const selectedPhotoAudioId = audios.some(source => source.id === photoAudioId) ? photoAudioId : '';
  const selectedVisualizerAudioId = visualizerAudios.some(source => source.id === visualizerAudioId)
    ? visualizerAudioId
    : visualizerAudios[0]?.id ?? '';
  const selectedArtworkId = visualizerArtworks.some(source => source.id === artworkId) ? artworkId : '';
  const unsatisfiedPrerequisites = (workflowPrerequisites ?? []).filter(
    prerequisite => !prerequisite.satisfied,
  );

  const uploadImages = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      for (const file of Array.from(files)) await uploadProjectImageSource(projectId, file);
      await onProjectChanged();
      setMessage(`Загружено изображений: ${files.length}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить изображения');
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
      await uploadStage8AudioSource(projectId, file);
      await onProjectChanged();
      setMessage('Аудио зарегистрировано в проекте.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить аудио');
    } finally {
      setBusy(false);
    }
  };

  const moveImage = (index: number, delta: -1 | 1) => {
    const target = index + delta;
    if (target < 0 || target >= orderedImageIds.length) return;
    const next = [...orderedImageIds];
    [next[index], next[target]] = [next[target], next[index]];
    setImageOrder(next);
  };

  const renderPhotos = async () => {
    const duration = Number(durationSeconds);
    if (!orderedImageIds.length) {
      setError('Сначала загрузите хотя бы одно изображение.');
      return;
    }
    if (!Number.isFinite(duration) || duration < 0.25 || duration > 30) {
      setError('Длительность фотографии должна быть от 0,25 до 30 секунд.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await executeComposePhotosAction(projectId, {
        image_source_ids: orderedImageIds,
        duration_per_image_us: Math.round(duration * 1_000_000),
        ...(selectedPhotoAudioId ? { audio_source_id: selectedPhotoAudioId } : {}),
      });
      setArtifactId(response.execution.result.artifact.id);
      setMessage('Видео собрано через Product Orchestrator и локальный FFmpeg capability.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать видео');
    } finally {
      setBusy(false);
    }
  };

  const renderVisualizer = async () => {
    if (!workflowAction || workflowAction.action_id !== 'render_visualizer') {
      setError('Product Orchestrator не предоставил действие визуализатора.');
      return;
    }
    if (!selectedVisualizerAudioId) {
      setError('Сначала выберите проверенное master-аудио.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await executeRenderVisualizerAction(projectId, {
        audio_source_id: selectedVisualizerAudioId,
        ...(selectedArtworkId ? { artwork_source_id: selectedArtworkId } : {}),
      });
      setArtifactId(response.execution.result.artifact.id);
      setMessage('Аудиовизуализатор собран через Product Orchestrator и локальный FFmpeg capability.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать визуализатор');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-indigo-900/60 bg-indigo-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-indigo-400">Product workflow · локальная сборка</p>
      <h2 className="mt-2 text-xl font-medium">
        {recipeId === 'photo_to_video' ? 'Фотографии → видео' : 'Аудио → визуализатор'}
      </h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
        Исходники регистрируются в Project Store с SHA/размером. Рендер получает только их project source ID;
        браузер не передаёт FFmpeg пути или произвольные параметры.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить изображения</span>
          <input
            aria-label="Изображения Stage 8"
            className="mt-3 block w-full text-xs text-slate-400"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff"
            multiple
            disabled={busy}
            onChange={event => void uploadImages(event.target.files)}
          />
        </label>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить аудио</span>
          <input
            aria-label="Аудио Stage 8"
            className="mt-3 block w-full text-xs text-slate-400"
            type="file"
            accept="audio/*"
            disabled={busy}
            onChange={event => void uploadAudio(event.target.files?.[0])}
          />
        </label>
      </div>

      {recipeId === 'photo_to_video' ? (
        <div className="mt-6 space-y-5">
          <div>
            <h3 className="text-sm font-medium text-slate-200">Порядок фотографий</h3>
            {orderedImageIds.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">
                {images.length > 0
                  ? 'Нет проверенных изображений. Загрузите новую копию.'
                  : 'Изображений пока нет.'}
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {orderedImageIds.map((sourceId, index) => {
                  const source = composableImages.find(item => item.id === sourceId);
                  if (!source) return null;
                  return (
                    <div key={sourceId} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                      <span className="text-sm text-slate-300">{index + 1}. {sourceName(source)}</span>
                      <div className="flex gap-2">
                        <button type="button" disabled={busy || index === 0} onClick={() => moveImage(index, -1)} className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30">↑</button>
                        <button type="button" disabled={busy || index === orderedImageIds.length - 1} onClick={() => moveImage(index, 1)} className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30">↓</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-300">
              Секунд на фотографию
              <input aria-label="Секунд на фотографию" type="number" min="0.25" max="30" step="0.25" value={durationSeconds} onChange={event => setDurationSeconds(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2" />
            </label>
            <label className="text-sm text-slate-300">
              Аудиодорожка (необязательно)
              <select aria-label="Аудио для фото-видео" value={selectedPhotoAudioId} onChange={event => setPhotoAudioId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Без аудио</option>
                {audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
          </div>
          {workflowAction && !workflowAction.enabled && unsatisfiedPrerequisites.length > 0 && (
            <div className="space-y-1 text-sm text-amber-300">
              {unsatisfiedPrerequisites.map(prerequisite => (
                <p key={prerequisite.prerequisite_id}>
                  {prerequisite.resolution ?? prerequisite.explanation}
                </p>
              ))}
            </div>
          )}
          <button type="button" disabled={busy || orderedImageIds.length === 0 || workflowAction?.enabled === false} onClick={() => void renderPhotos()} className="rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40">
            Собрать видео из фотографий
          </button>
        </div>
      ) : (
        <div className="mt-6 space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-300">
              Master-аудио
              <select aria-label="Master-аудио визуализатора" value={selectedVisualizerAudioId} onChange={event => setVisualizerAudioId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Выберите аудио</option>
                {visualizerAudios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Обложка (необязательно)
              <select aria-label="Обложка визуализатора" value={selectedArtworkId} onChange={event => setArtworkId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Только waveform</option>
                {visualizerArtworks.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
          </div>
          {workflowAction && !workflowAction.enabled && unsatisfiedPrerequisites.length > 0 && (
            <div className="space-y-1 text-sm text-amber-300">
              {unsatisfiedPrerequisites.map(prerequisite => (
                <p key={prerequisite.prerequisite_id}>
                  {prerequisite.resolution ?? prerequisite.explanation}
                </p>
              ))}
            </div>
          )}
          <button type="button" disabled={busy || !selectedVisualizerAudioId || workflowAction?.enabled !== true} onClick={() => void renderVisualizer()} className="rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40">
            Собрать аудиовизуализатор
          </button>
        </div>
      )}

      {message && <p className="mt-5 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-5 text-sm text-red-300">{error}</p>}
      {artifactId && (
        <a href={projectStage8ArtifactUrl(projectId, artifactId)} target="_blank" rel="noreferrer" className="mt-5 inline-block text-sm text-sky-300 hover:text-sky-200">
          Открыть готовый рендер
        </a>
      )}
    </section>
  );
}
