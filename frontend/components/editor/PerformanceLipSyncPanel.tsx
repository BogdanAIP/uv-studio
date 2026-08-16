'use client';

import { useEffect, useMemo, useState } from 'react';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  getPerformanceLipSyncOffers,
  renderPerformanceLipSync,
  type PerformanceLipSyncOffer,
} from '@/lib/performanceLipSyncApi';
import {
  projectStage8ArtifactUrl,
  uploadProjectImageSource,
  uploadStage8AudioSource,
} from '@/lib/stage8MediaApi';

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original ? original : source.path.split('/').pop() || source.id;
}

interface PerformanceLipSyncPanelProps {
  projectId: string;
  sources: ProjectReference[];
  onProjectChanged: () => Promise<void> | void;
}

export function PerformanceLipSyncPanel({
  projectId,
  sources,
  onProjectChanged,
}: PerformanceLipSyncPanelProps) {
  const images = useMemo(() => sources.filter(source => source.kind === 'image'), [sources]);
  const audios = useMemo(() => sources.filter(source => source.kind === 'audio'), [sources]);
  const [portraitId, setPortraitId] = useState(() => images[0]?.id ?? '');
  const [speechId, setSpeechId] = useState(() => audios[0]?.id ?? '');
  const [offer, setOffer] = useState<PerformanceLipSyncOffer | null>(null);
  const [offerError, setOfferError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);

  const selectedPortraitId = images.some(source => source.id === portraitId)
    ? portraitId
    : images[0]?.id ?? '';
  const selectedSpeechId = audios.some(source => source.id === speechId)
    ? speechId
    : audios[0]?.id ?? '';

  useEffect(() => {
    let active = true;
    void getPerformanceLipSyncOffers()
      .then(offers => {
        if (!active) return;
        const local = offers.find(item => item.offer_id === 'local_musetalk.video_digital_human') ?? null;
        setOffer(local);
        setOfferError(local ? null : 'Локальный MuseTalk offer не зарегистрирован.');
      })
      .catch(err => {
        if (!active) return;
        setOfferError(err instanceof Error ? err.message : 'Не удалось проверить MuseTalk pack');
      });
    return () => {
      active = false;
    };
  }, []);

  const uploadPortrait = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await uploadProjectImageSource(projectId, file);
      await onProjectChanged();
      setMessage('Портрет зарегистрирован в Project Store.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить портрет');
    } finally {
      setBusy(false);
    }
  };

  const uploadSpeech = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await uploadStage8AudioSource(projectId, file);
      await onProjectChanged();
      setMessage('Готовая речь зарегистрирована в Project Store.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить готовую речь');
    } finally {
      setBusy(false);
    }
  };

  const render = async () => {
    if (!selectedPortraitId || !selectedSpeechId) {
      setError('Выберите портрет и готовую речь.');
      return;
    }
    if (offer?.availability !== 'available') {
      setError(offer?.reason || offerError || 'MuseTalk optional pack пока недоступен.');
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await renderPerformanceLipSync(projectId, selectedPortraitId, selectedSpeechId);
      setArtifactId(response.result.artifact.id);
      setMessage('Lip-sync выполнен локальным MuseTalk capability.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось выполнить lip-sync');
    } finally {
      setBusy(false);
    }
  };

  const available = offer?.availability === 'available';

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-fuchsia-900/60 bg-fuchsia-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-fuchsia-400">Stage 8 · Performance / lip-sync</p>
      <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-xl font-medium">Портрет + готовая речь → lip-sync</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Локальный путь использует optional MuseTalk 1.5 pack. UV Studio не включает CUDA/PyTorch/модели
            в обязательную установку и передаёт движку только проверенные project source ID.
          </p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-xs ${available ? 'bg-emerald-950 text-emerald-300' : 'bg-amber-950 text-amber-300'}`}>
          {offer?.availability ?? 'проверка…'}
        </span>
      </div>

      <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400">
          <span>Движок: MuseTalk 1.5</span>
          <span>Локальность: {offer?.locality ?? 'local'}</span>
          <span>Стоимость capability: {offer?.cost_class ?? 'free'}</span>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          {offerError ?? offer?.reason ?? 'Проверяется состояние optional pack…'}
        </p>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить портрет</span>
          <input
            aria-label="Портрет lip-sync"
            className="mt-3 block w-full text-xs text-slate-400"
            type="file"
            accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff"
            disabled={busy}
            onChange={event => void uploadPortrait(event.target.files?.[0])}
          />
        </label>
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Добавить готовую речь</span>
          <input
            aria-label="Готовая речь lip-sync"
            className="mt-3 block w-full text-xs text-slate-400"
            type="file"
            accept="audio/*"
            disabled={busy}
            onChange={event => void uploadSpeech(event.target.files?.[0])}
          />
        </label>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <label className="text-sm text-slate-300">
          Портрет/персонаж
          <select
            aria-label="Выбранный портрет lip-sync"
            value={selectedPortraitId}
            onChange={event => setPortraitId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="">Выберите изображение</option>
            {images.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
          </select>
        </label>
        <label className="text-sm text-slate-300">
          Готовая речь
          <select
            aria-label="Выбранная речь lip-sync"
            value={selectedSpeechId}
            onChange={event => setSpeechId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            <option value="">Выберите аудио</option>
            {audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}
          </select>
        </label>
      </div>

      <button
        type="button"
        disabled={busy || !available || !selectedPortraitId || !selectedSpeechId}
        onClick={() => void render()}
        className="mt-6 rounded-lg bg-fuchsia-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        Выполнить lip-sync
      </button>

      {!available && (
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Без optional pack режим остаётся доступен как проект и не ломает остальные функции UV Studio.
          Установка/диагностика тяжёлого GPU-пака относится к Stage 9 productization.
        </p>
      )}
      {message && <p className="mt-5 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-5 text-sm text-red-300">{error}</p>}
      {artifactId && (
        <a
          href={projectStage8ArtifactUrl(projectId, artifactId)}
          target="_blank"
          rel="noreferrer"
          className="mt-5 inline-block text-sm text-sky-300 hover:text-sky-200"
        >
          Открыть готовый lip-sync рендер
        </a>
      )}
    </section>
  );
}
