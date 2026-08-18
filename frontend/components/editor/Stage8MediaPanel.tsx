'use client';

import { ArrowDown, ArrowUp, Image as ImageIcon, Music2, Play, Upload } from 'lucide-react';
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

  const orderedImageIds = useMemo(() => {
    const availableIds = new Set(images.map(source => source.id));
    const preserved = imageOrder.filter(sourceId => availableIds.has(sourceId));
    const preservedIds = new Set(preserved);
    const appended = images.map(source => source.id).filter(sourceId => !preservedIds.has(sourceId));
    return [...preserved, ...appended];
  }, [imageOrder, images]);
  const selectedPhotoAudioId = audios.some(source => source.id === photoAudioId) ? photoAudioId : '';
  const selectedVisualizerAudioId = audios.some(source => source.id === visualizerAudioId) ? visualizerAudioId : audios[0]?.id ?? '';
  const selectedArtworkId = images.some(source => source.id === artworkId) ? artworkId : '';

  const uploadImages = async (files: FileList | null) => {
    if (!files?.length) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      for (const file of Array.from(files)) await uploadProjectImageSource(projectId, file);
      await onProjectChanged();
      setMessage(`Добавлено изображений: ${files.length}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить изображения');
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
      setMessage('Аудио добавлено в проект.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить аудио');
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
      setError('Сначала добавьте хотя бы одно изображение.');
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
      const response = await renderPhotoToVideo(projectId, orderedImageIds, Math.round(duration * 1_000_000), selectedPhotoAudioId || undefined);
      setArtifactId(response.result.artifact.id);
      setMessage('Видео собрано и сохранено в результатах проекта.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать видео');
    } finally {
      setBusy(false);
    }
  };

  const renderVisualizer = async () => {
    if (!selectedVisualizerAudioId) {
      setError('Сначала выберите аудио.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await renderAudioVisualizer(projectId, selectedVisualizerAudioId, selectedArtworkId || undefined);
      setArtifactId(response.result.artifact.id);
      setMessage('Визуализатор собран и сохранён в результатах проекта.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать визуализатор');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300">
          {recipeId === 'photo_to_video' ? <ImageIcon size={17} /> : <Music2 size={17} />}
        </span>
        <div>
          <h2 className="text-lg font-medium text-zinc-100">{recipeId === 'photo_to_video' ? 'Собрать видео из фотографий' : 'Собрать аудиовизуализатор'}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">
            {recipeId === 'photo_to_video'
              ? 'Задайте порядок изображений, длительность кадров и при желании добавьте аудиодорожку.'
              : 'Выберите аудио и при желании обложку. Сборка выполняется локально на этом компьютере.'}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 text-sm text-zinc-400 transition hover:border-[var(--uv-border-strong)] hover:text-zinc-200">
          <ImageIcon size={17} className="text-zinc-600" />
          <span className="flex-1">Добавить изображения</span>
          <Upload size={14} className="text-zinc-700" />
          <input aria-label="Изображения Stage 8" className="hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" multiple disabled={busy} onChange={event => void uploadImages(event.target.files)} />
        </label>
        <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 text-sm text-zinc-400 transition hover:border-[var(--uv-border-strong)] hover:text-zinc-200">
          <Music2 size={17} className="text-zinc-600" />
          <span className="flex-1">Добавить аудио</span>
          <Upload size={14} className="text-zinc-700" />
          <input aria-label="Аудио Stage 8" className="hidden" type="file" accept="audio/*" disabled={busy} onChange={event => void uploadAudio(event.target.files?.[0])} />
        </label>
      </div>

      {recipeId === 'photo_to_video' ? (
        <div className="mt-6 space-y-5">
          <div>
            <h3 className="text-sm font-medium text-zinc-300">Порядок фотографий</h3>
            {orderedImageIds.length === 0 ? (
              <div className="mt-3 rounded-xl border border-dashed border-[var(--uv-border)] px-4 py-7 text-center text-sm text-zinc-700">Добавьте изображения, чтобы собрать последовательность.</div>
            ) : (
              <div className="mt-3 space-y-2">
                {orderedImageIds.map((sourceId, index) => {
                  const source = images.find(item => item.id === sourceId);
                  if (!source) return null;
                  return (
                    <div key={sourceId} className="flex items-center justify-between rounded-xl border border-[var(--uv-border)] bg-black/10 px-3 py-2.5">
                      <span className="min-w-0 truncate text-sm text-zinc-400"><span className="mr-2 text-zinc-700">{index + 1}</span>{sourceName(source)}</span>
                      <div className="flex gap-1">
                        <button aria-label={`Поднять изображение ${index + 1}`} type="button" disabled={busy || index === 0} onClick={() => moveImage(index, -1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--uv-border)] text-zinc-600 hover:text-zinc-300 disabled:opacity-25"><ArrowUp size={13} /></button>
                        <button aria-label={`Опустить изображение ${index + 1}`} type="button" disabled={busy || index === orderedImageIds.length - 1} onClick={() => moveImage(index, 1)} className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--uv-border)] text-zinc-600 hover:text-zinc-300 disabled:opacity-25"><ArrowDown size={13} /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-xs text-zinc-500">Секунд на фотографию<input aria-label="Секунд на фотографию" type="number" min="0.25" max="30" step="0.25" value={durationSeconds} onChange={event => setDurationSeconds(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300" /></label>
            <label className="text-xs text-zinc-500">Аудиодорожка (необязательно)<select aria-label="Аудио для фото-видео" value={selectedPhotoAudioId} onChange={event => setPhotoAudioId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300"><option value="">Без аудио</option>{audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select></label>
          </div>
          <button type="button" disabled={busy || orderedImageIds.length === 0} onClick={() => void renderPhotos()} className="inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"><Play size={15} />{busy ? 'Собираем…' : 'Собрать видео'}</button>
        </div>
      ) : (
        <div className="mt-6 space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="text-xs text-zinc-500">Аудио<select aria-label="Master-аудио визуализатора" value={selectedVisualizerAudioId} onChange={event => setVisualizerAudioId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300"><option value="">Выберите аудио</option>{audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select></label>
            <label className="text-xs text-zinc-500">Обложка (необязательно)<select aria-label="Обложка визуализатора" value={selectedArtworkId} onChange={event => setArtworkId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300"><option value="">Только визуализатор</option>{images.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select></label>
          </div>
          <button type="button" disabled={busy || !selectedVisualizerAudioId} onClick={() => void renderVisualizer()} className="inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"><Play size={15} />{busy ? 'Собираем…' : 'Собрать визуализатор'}</button>
        </div>
      )}

      {message && <p className="mt-5 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-5 text-sm text-rose-300">{error}</p>}
      {artifactId && <a href={projectStage8ArtifactUrl(projectId, artifactId)} target="_blank" rel="noreferrer" className="mt-5 inline-flex text-sm text-violet-300 hover:text-violet-200">Открыть готовый рендер</a>}
    </section>
  );
}
