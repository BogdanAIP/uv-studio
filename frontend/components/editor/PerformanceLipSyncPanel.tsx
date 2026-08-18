'use client';

import { Image as ImageIcon, Loader2, Mic2, Play, Upload, UserRound } from 'lucide-react';
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

export function PerformanceLipSyncPanel({ projectId, sources, onProjectChanged }: PerformanceLipSyncPanelProps) {
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

  const selectedPortraitId = images.some(source => source.id === portraitId) ? portraitId : images[0]?.id ?? '';
  const selectedSpeechId = audios.some(source => source.id === speechId) ? speechId : audios[0]?.id ?? '';

  useEffect(() => {
    let active = true;
    void getPerformanceLipSyncOffers()
      .then(offers => {
        if (!active) return;
        const local = offers.find(item => item.offer_id === 'local_musetalk.video_digital_human') ?? null;
        setOffer(local);
        setOfferError(local ? null : 'Локальный модуль lip-sync не установлен или не зарегистрирован.');
      })
      .catch(err => {
        if (active) setOfferError(err instanceof Error ? err.message : 'Не удалось проверить локальный модуль lip-sync');
      });
    return () => { active = false; };
  }, []);

  const uploadPortrait = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      await uploadProjectImageSource(projectId, file); await onProjectChanged();
      setMessage('Портрет добавлен в проект.');
    } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось добавить портрет'); }
    finally { setBusy(false); }
  };

  const uploadSpeech = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true); setError(null); setMessage(null);
    try {
      await uploadStage8AudioSource(projectId, file); await onProjectChanged();
      setMessage('Речевая дорожка добавлена в проект.');
    } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось добавить речь'); }
    finally { setBusy(false); }
  };

  const render = async () => {
    if (!selectedPortraitId || !selectedSpeechId) {
      setError('Выберите портрет и готовую речь.');
      return;
    }
    if (offer?.availability !== 'available') {
      setError('Для lip-sync требуется установленный локальный модуль. Остальные функции проекта продолжают работать без него.');
      return;
    }
    setBusy(true); setError(null); setMessage(null);
    try {
      const response = await renderPerformanceLipSync(projectId, selectedPortraitId, selectedSpeechId);
      setArtifactId(response.result.artifact.id);
      setMessage('Lip-sync готов.');
      await onProjectChanged();
    } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось выполнить lip-sync'); }
    finally { setBusy(false); }
  };

  const available = offer?.availability === 'available';

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><UserRound size={18} /></span>
          <div>
            <h2 className="text-lg font-medium text-zinc-100">Портрет + речь → lip-sync</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Выберите изображение персонажа и готовую речевую дорожку. Обработка выполняется локально, если дополнительный модуль установлен на этом компьютере.</p>
          </div>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-xs ${available ? 'bg-emerald-400/10 text-emerald-300' : 'bg-amber-400/10 text-amber-200'}`}>{available ? 'Готов к работе' : 'Нужен локальный модуль'}</span>
      </div>

      {!available && (
        <div className="mt-5 rounded-xl border border-amber-400/15 bg-amber-400/[0.05] p-4 text-sm leading-6 text-zinc-500">
          Lip-sync сейчас недоступен, потому что тяжёлый локальный модуль не установлен. Проект, материалы и остальные инструменты UV Studio от этого не блокируются.
          {(offerError || offer?.reason) && <details className="mt-2 text-xs text-zinc-700"><summary className="cursor-pointer">Техническая причина</summary><p className="mt-2 break-words">{offerError ?? offer?.reason}</p></details>}
        </div>
      )}

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 text-sm text-zinc-400 transition hover:border-[var(--uv-border-strong)] hover:text-zinc-200">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-black/15 text-zinc-600"><ImageIcon size={16} /></span><span className="flex-1">Добавить портрет</span><Upload size={14} className="text-zinc-700" />
          <input aria-label="Портрет lip-sync" className="hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/tiff" disabled={busy} onChange={event => void uploadPortrait(event.target.files?.[0])} />
        </label>
        <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 text-sm text-zinc-400 transition hover:border-[var(--uv-border-strong)] hover:text-zinc-200">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-black/15 text-zinc-600"><Mic2 size={16} /></span><span className="flex-1">Добавить готовую речь</span><Upload size={14} className="text-zinc-700" />
          <input aria-label="Готовая речь lip-sync" className="hidden" type="file" accept="audio/*" disabled={busy} onChange={event => void uploadSpeech(event.target.files?.[0])} />
        </label>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <label className="text-xs text-zinc-600">Портрет<select aria-label="Выбранный портрет lip-sync" value={selectedPortraitId} onChange={event => setPortraitId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300"><option value="">Выберите изображение</option>{images.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select></label>
        <label className="text-xs text-zinc-600">Речевая дорожка<select aria-label="Выбранная речь lip-sync" value={selectedSpeechId} onChange={event => setSpeechId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300"><option value="">Выберите аудио</option>{audios.map(source => <option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select></label>
      </div>

      <button type="button" disabled={busy || !available || !selectedPortraitId || !selectedSpeechId} onClick={() => void render()} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600">{busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} Выполнить lip-sync</button>

      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-rose-300">{error}</p>}
      {artifactId && <a href={projectStage8ArtifactUrl(projectId, artifactId)} target="_blank" rel="noreferrer" className="mt-4 inline-flex text-sm text-violet-300 hover:text-violet-200">Открыть готовое видео</a>}
    </section>
  );
}
