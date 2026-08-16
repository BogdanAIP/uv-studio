'use client';

import { useMemo, useState } from 'react';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  projectStage8ArtifactUrl,
  renderAudioVisualizer,
  renderPhotoToVideo,
  uploadProjectImageSource,
  uploadStage8AudioSource,
} from '@/lib/stage8MediaApi';

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original ? original : source.path.split('/').pop() || source.id;
}

interface Stage8MediaPanelProps {
  projectId: string;
  recipeId: 'photo_to_video' | 'visualizer';
  sources: ProjectReference[];
  onProjectChanged: () => Promise<void> | void;
}

export function Stage8MediaPanel({ projectId, recipeId, sources, onProjectChanged }: Stage8MediaPanelProps) {
  const images = useMemo(() => sources.filter(source => source.kind === 'image'), [sources]);
  const audios = useMemo(() => sources.filter(source => source.kind === 'audio'), [sources]);
  const [imageOrder, setImageOrder] = useState(() => images.map(source => source.id));
  const [photoAudioId, setPhotoAudioId] = useState('');
  const [durationSeconds, setDurationSeconds] = useState('2');
  const [visualizerAudioId, setVisualizerAudioId] = useState(() => audios[0]?.id ?? '');
  const [artworkId, setArtworkId] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);

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
    if (target < 0 || target >= imageOrder.length) return;
    setImageOrder(current => {
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const renderPhotos = async () => {
    const duration = Number(durationSeconds);
    if (!imageOrder.length) {
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
      const response = await renderPhotoToVideo(
        projectId,
        imageOrder,
        Math.round(duration * 1_000_000),
        photoAudioId || undefined,
      );
      setArtifactId(response.result.artifact.id);
      setMessage('Видео из фотографий собрано локальным FFmpeg capability.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать видео');
    } finally {
      setBusy(false);
    }
  };

  const renderVisualizer = async () => {
    if (!visualizerAudioId) {
      setError('Сначала выберите master-аудио.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await renderAudioVisualizer(projectId, visualizerAudioId, artworkId || undefined);
      setArtifactId(response.result.artifact.id);
      setMessage('Аудиовизуализатор собран локальным FFmpeg capability.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать визуализатор');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-indigo-900/60 bg-indigo-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-indigo-400">Stage 8 · локальная сборка</p>
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
            {imageOrder.length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">Изображений пока нет.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {imageOrder.map((sourceId, index) => {
                  const source = images.find(item => item.id === sourceId);
                  if (!source) return null;
                  return (
                    <div key={sourceId} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2">
                      <span className="text-sm text-slate-300">{index + 1}. {sourceName(source)}</span>
                      <div className="flex gap-2">
                        <button type="button" disabled={busy || index === 0} onClick={() => moveImage(index, -1)} className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30">↑</button>
                        <button type="button" disabled={busy || index === imageOrder.length - 1} onClick={() => moveImage(index, 1)} className="rounded border border-slate-700 px-2 py-1 text-xs disabled:opacity-30">↓</button>
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
              <select aria-label="Аудио для фото-видео" value={photoAudioId} onChange={event => setPhotoAudioId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Без аудио</option>
                {audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
          </div>
          <button type="button" disabled={busy || imageOrder.length === 0} onClick={() => void renderPhotos()} className="rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40">
            Собрать видео из фотографий
          </button>
        </div>
      ) : (
        <div className="mt-6 space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-sm text-slate-300">
              Master-аудио
              <select aria-label="Master-аудио визуализатора" value={visualizerAudioId} onChange={event => setVisualizerAudioId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Выберите аудио</option>
                {audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
            <label className="text-sm text-slate-300">
              Обложка (необязательно)
              <select aria-label="Обложка визуализатора" value={artworkId} onChange={event => setArtworkId(event.target.value)} className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
                <option value="">Только waveform</option>
                {images.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
              </select>
            </label>
          </div>
          <button type="button" disabled={busy || !visualizerAudioId} onClick={() => void renderVisualizer()} className="rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40">
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
