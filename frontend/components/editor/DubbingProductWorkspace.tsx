'use client';

import {
  AudioLines,
  CheckCircle2,
  Download,
  FileAudio,
  Languages,
  Loader2,
  Mic2,
  MonitorPlay,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  acceptAsrTranscript,
  acceptDubbingReview,
  attachPreparedSpeech,
  getDubbingEditorState,
  preparedAudioMediaUrl,
  renderAcceptedDubbing,
  reviewPreparedSpeech,
  saveDubbingTranslation,
  transcribeProjectSource,
  uploadPreparedAudio,
  type AsrDraft,
  type DubbingEditorState,
  type DubbingTranscriptSegment,
} from '@/lib/dubbingApi';
import { projectArtifactMediaUrl, projectSourceMediaUrl } from '@/lib/editorApi';
import { createBrowserPreview } from '@/lib/renderApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface DubbingProductWorkspaceProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

type BusyAction = 'transcribe' | 'accept-text' | 'translation' | 'upload' | 'attach' | 'review' | 'accept' | 'render' | 'preview' | 'refresh';

function metadataText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function toUs(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value.replace(',', '.'));
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed * 1_000_000) : null;
}

function latestBy<T>(values: T[], pick: (value: T) => string): T | null {
  return values.length ? [...values].sort((a, b) => pick(a).localeCompare(pick(b))).at(-1) ?? null : null;
}

export function DubbingProductWorkspace({ projectId, onProjectChanged }: DubbingProductWorkspaceProps) {
  const [state, setState] = useState<DubbingEditorState | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [selectedDubbingId, setSelectedDubbingId] = useState('');
  const [selectedTranslationId, setSelectedTranslationId] = useState('');
  const [selectedAudioId, setSelectedAudioId] = useState('');
  const [selectedSegmentId, setSelectedSegmentId] = useState('');
  const [selectedTakeId, setSelectedTakeId] = useState('');
  const [language, setLanguage] = useState('auto');
  const [startSec, setStartSec] = useState('');
  const [endSec, setEndSec] = useState('');
  const [draft, setDraft] = useState<AsrDraft | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('ru');
  const [translationDraft, setTranslationDraft] = useState<Record<string, string>>({});
  const [useTranslation, setUseTranslation] = useState(true);
  const [contentOk, setContentOk] = useState(false);
  const [syncOk, setSyncOk] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [latestRenderId, setLatestRenderId] = useState<string | null>(null);
  const [latestPreviewId, setLatestPreviewId] = useState<string | null>(null);
  const [busy, setBusy] = useState<BusyAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = async () => {
    const next = await getDubbingEditorState(projectId);
    setState(next);
    return next;
  };

  useEffect(() => {
    let active = true;
    getDubbingEditorState(projectId)
      .then(value => { if (active) setState(value); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Не удалось загрузить дубляж'); });
    return () => { active = false; };
  }, [projectId]);

  const source = useMemo(() => state?.sources.find(item => item.id === selectedSourceId) ?? state?.sources[0] ?? null, [selectedSourceId, state]);
  const transcripts = useMemo(() => state && source ? state.dubbing.transcripts.filter(item => item.source_id === source.id) : [], [source, state]);
  const transcript = useMemo(() => transcripts.find(item => item.dubbing_id === selectedDubbingId) ?? transcripts.at(-1) ?? null, [selectedDubbingId, transcripts]);
  const translations = useMemo(() => state && transcript ? state.dubbing.translations.filter(item => item.dubbing_id === transcript.dubbing_id) : [], [state, transcript]);
  const translation = useMemo(() => translations.find(item => item.translation_id === selectedTranslationId) ?? translations.at(-1) ?? null, [selectedTranslationId, translations]);
  const audio = useMemo(() => state?.prepared_audio.find(item => item.id === selectedAudioId) ?? state?.prepared_audio.at(-1) ?? null, [selectedAudioId, state]);
  const segmentId = selectedSegmentId && transcript?.segments.some(item => item.segment_id === selectedSegmentId) ? selectedSegmentId : '';
  const takes = useMemo(() => state && transcript ? state.prepared_speech.takes.filter(item => item.dubbing_id === transcript.dubbing_id) : [], [state, transcript]);
  const take = useMemo(() => takes.find(item => item.take_id === selectedTakeId) ?? takes.at(-1) ?? null, [selectedTakeId, takes]);
  const currentReview = useMemo(() => state && take ? latestBy(state.dubbing_reviews.filter(item => item.take_id === take.take_id), item => item.review_id) : null, [state, take]);
  const acceptedForSource = useMemo(() => state && source ? state.accepted_dubbing.filter(item => item.source_id === source.id) : [], [source, state]);
  const acceptedCurrentTake = Boolean(take && acceptedForSource.some(item => item.take_id === take.take_id));
  const renders = useMemo(() => state && source ? state.artifacts.filter(item => item.kind === 'video' && item.metadata.lifecycle === 'dubbing_render' && item.metadata.source_id === source.id) : [], [source, state]);
  const activeRender = renders.find(item => item.id === latestRenderId) ?? renders.at(-1) ?? null;
  const previews = useMemo(() => state && activeRender ? state.artifacts.filter(item => item.kind === 'video' && item.metadata.lifecycle === 'browser_preview' && item.metadata.source_artifact_id === activeRender.id) : [], [activeRender, state]);
  const activePreview = previews.find(item => item.id === latestPreviewId) ?? previews.at(-1) ?? null;

  const run = async (action: BusyAction, work: () => Promise<void>) => {
    setBusy(action); setError(null); setNotice(null);
    try { await work(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Операция дубляжа не выполнена'); }
    finally { setBusy(null); }
  };

  const transcriptText = (segment: DubbingTranscriptSegment): string => translationDraft[segment.segment_id] ?? translation?.segments.find(item => item.segment_id === segment.segment_id)?.text ?? segment.text;

  const handleTranscribe = () => {
    if (!source) return;
    void run('transcribe', async () => {
      const startUs = toUs(startSec);
      const endUs = toUs(endSec);
      if ((startUs === null) !== (endUs === null)) throw new Error('Для частичного распознавания укажите и начало, и конец.');
      if (startUs !== null && endUs !== null && endUs <= startUs) throw new Error('Конец диапазона должен быть позже начала.');
      const value = await transcribeProjectSource(projectId, { source_id: source.id, language: language.trim() || 'auto', ...(startUs !== null && endUs !== null ? { start_us: startUs, end_us: endUs } : {}) });
      setDraft(value);
      setNotice('Речь распознана. Проверьте текст перед сохранением.');
    });
  };

  const updateDraftText = (segmentIdValue: string, text: string) => {
    setDraft(current => current ? { ...current, segments: current.segments.map(item => item.segment_id === segmentIdValue ? { ...item, text } : item) } : current);
  };

  const handleAcceptText = () => {
    if (!draft) return;
    void run('accept-text', async () => {
      if (draft.segments.some(item => !item.text.trim())) throw new Error('Заполните текст каждого фрагмента.');
      const accepted = await acceptAsrTranscript(projectId, draft);
      setSelectedDubbingId(accepted.dubbing_id); setDraft(null);
      await refresh(); await onProjectChanged?.();
      setNotice('Проверенный текст сохранён в проекте.');
    });
  };

  const handleSaveTranslation = () => {
    if (!transcript) return;
    void run('translation', async () => {
      const segments = transcript.segments.map(item => ({ segment_id: item.segment_id, text: transcriptText(item).trim() }));
      if (segments.some(item => !item.text)) throw new Error('Перевод каждого фрагмента должен быть заполнен.');
      const saved = await saveDubbingTranslation(projectId, { dubbing_id: transcript.dubbing_id, target_language: targetLanguage, segments, ...(translation ? { translation_id: translation.translation_id } : {}) });
      setSelectedTranslationId(saved.payload.translation.translation_id); setTranslationDraft({});
      await refresh(); setNotice('Перевод сохранён.');
    });
  };

  const handleAudioUpload = (file: File | null) => {
    if (!file) return;
    void run('upload', async () => {
      const uploaded = await uploadPreparedAudio(projectId, file, 'imported');
      setSelectedAudioId(uploaded.id); await refresh(); await onProjectChanged?.();
      setNotice('Речевая дорожка добавлена.');
    });
  };

  const handleAttach = () => {
    if (!transcript || !audio) return;
    void run('attach', async () => {
      if (useTranslation && !translation) throw new Error('Сохраните перевод или отключите использование перевода.');
      const result = await attachPreparedSpeech(projectId, { dubbing_id: transcript.dubbing_id, audio_id: audio.id, ...(useTranslation && translation ? { translation_id: translation.translation_id } : {}), ...(segmentId ? { segment_id: segmentId } : {}) });
      setSelectedTakeId(result.payload.prepared_speech.take_id); setContentOk(false); setSyncOk(false);
      await refresh(); setNotice('Речевая дорожка привязана к выбранному тексту.');
    });
  };

  const handleReview = (verdict: 'approved' | 'needs_revision' | 'rejected') => {
    if (!take) return;
    void run('review', async () => {
      await reviewPreparedSpeech(projectId, { take_id: take.take_id, verdict, content_fidelity_confirmed: contentOk, synchronization_confirmed: syncOk, ...(reviewNote.trim() ? { note: reviewNote.trim() } : {}) });
      await refresh();
      setNotice(verdict === 'approved' ? 'Проверка сохранена. Теперь озвучку можно применить.' : 'Результат проверки сохранён.');
    });
  };

  const handleAccept = () => {
    if (!currentReview || currentReview.verdict !== 'approved') return;
    void run('accept', async () => {
      await acceptDubbingReview(projectId, currentReview.review_id); await refresh(); await onProjectChanged?.();
      setNotice('Озвучка применена к проекту.');
    });
  };

  const handleRender = () => {
    if (!source || acceptedForSource.length === 0) return;
    void run('render', async () => {
      const rendered = await renderAcceptedDubbing(projectId, source.id);
      const artifactId = rendered.result.artifact?.id;
      if (!artifactId) throw new Error('Готовый файл не был сохранён.');
      setLatestRenderId(artifactId); setLatestPreviewId(null);
      try {
        const preview = await createBrowserPreview(projectId, artifactId);
        if (preview.result.artifact?.id) setLatestPreviewId(preview.result.artifact.id);
      } catch { setNotice('Видео собрано. Просмотр можно подготовить отдельно.'); }
      await refresh(); await onProjectChanged?.();
    });
  };

  const handlePreview = () => {
    if (!activeRender) return;
    void run('preview', async () => {
      const preview = await createBrowserPreview(projectId, activeRender.id);
      if (!preview.result.artifact?.id) throw new Error('Не удалось подготовить просмотр.');
      setLatestPreviewId(preview.result.artifact.id); await refresh();
    });
  };

  if (!state) return <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-600">Загрузка дубляжа…</section>;

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><Mic2 size={18} /></span>
          <div><h2 className="text-lg font-medium text-zinc-100">Дубляж</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Проверьте текст, при необходимости переведите его, добавьте речевую дорожку и примените только после просмотра и проверки.</p></div>
        </div>
        <button type="button" disabled={busy !== null} onClick={() => void run('refresh', async () => { await refresh(); setNotice('Данные проекта обновлены.'); })} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border)] px-3 text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-40"><RefreshCw size={13} /> Обновить</button>
      </div>

      {error && <Message tone="error">{error}</Message>}
      {notice && <Message tone="ok">{notice}</Message>}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <StepCard number="1" title="Видео и распознавание" icon={<AudioLines size={16} />}>
          {state.sources.length === 0 ? <Hint>Сначала добавьте видео в «Монтаже».</Hint> : <>
            <Field label="Видео"><select aria-label="Видео для дубляжа" value={source?.id ?? ''} onChange={event => { setSelectedSourceId(event.target.value); setSelectedDubbingId(''); setSelectedTranslationId(''); setSelectedTakeId(''); setDraft(null); }} className="field">{state.sources.map(item => <option key={item.id} value={item.id}>{metadataText(item.metadata.original_name) ?? 'Видео проекта'}</option>)}</select></Field>
            {source && <video src={projectSourceMediaUrl(projectId, source.id)} controls playsInline preload="metadata" className="mt-3 aspect-video w-full rounded-xl bg-black object-contain" />}
            <div className="mt-3 grid grid-cols-3 gap-2"><SmallInput label="Язык" value={language} onChange={setLanguage} placeholder="auto" /><SmallInput label="Начало, с" value={startSec} onChange={setStartSec} placeholder="всё" /><SmallInput label="Конец, с" value={endSec} onChange={setEndSec} placeholder="всё" /></div>
            <button type="button" disabled={busy !== null || !source} onClick={handleTranscribe} className="primary mt-3">{busy === 'transcribe' ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} Распознать речь</button>
          </>}
          {draft && <div className="mt-4 rounded-xl border border-violet-400/15 bg-violet-400/[0.05] p-3"><p className="text-xs font-medium text-violet-200">Проверьте распознанный текст</p><div className="mt-3 max-h-72 space-y-2 overflow-y-auto">{draft.segments.map(item => <div key={item.segment_id} className="rounded-lg border border-[var(--uv-border)] bg-black/15 p-2"><p className="text-[10px] text-zinc-700">{formatTimelineTime(item.start_us)} → {formatTimelineTime(item.end_us)}</p><textarea aria-label={`Распознанный текст ${item.segment_id}`} value={item.text} onChange={event => updateDraftText(item.segment_id, event.target.value)} rows={2} className="mt-1 field" /></div>)}</div><button type="button" disabled={busy !== null} onClick={handleAcceptText} className="primary mt-3"><CheckCircle2 size={14} /> Сохранить проверенный текст</button></div>}
        </StepCard>

        <StepCard number="2" title="Текст и перевод" icon={<Languages size={16} />}>
          {!transcript ? <Hint>Распознайте речь или используйте уже сохранённый текст проекта.</Hint> : <>
            {transcripts.length > 1 && <Field label="Сохранённый текст"><select aria-label="Текст дубляжа" value={transcript.dubbing_id} onChange={event => { setSelectedDubbingId(event.target.value); setSelectedTranslationId(''); setTranslationDraft({}); setSelectedTakeId(''); }} className="field">{transcripts.map((item, index) => <option key={item.dubbing_id} value={item.dubbing_id}>Версия {index + 1} · {item.language} · {item.segments.length} фрагм.</option>)}</select></Field>}
            <div className="mt-3 flex items-end gap-2"><div className="flex-1"><SmallInput label="Язык перевода" value={targetLanguage} onChange={setTargetLanguage} placeholder="ru" /></div><span className="pb-2 text-[10px] text-zinc-700">Текст можно отредактировать вручную.</span></div>
            <div className="mt-3 max-h-80 space-y-2 overflow-y-auto">{transcript.segments.map(item => <div key={item.segment_id} className="grid gap-2 rounded-lg border border-[var(--uv-border)] bg-black/10 p-3 sm:grid-cols-2"><div><p className="text-[10px] text-zinc-700">Исходный текст</p><p className="mt-1 text-xs leading-5 text-zinc-300">{item.text}</p></div><div><p className="text-[10px] text-zinc-700">Перевод</p><textarea aria-label={`Перевод ${item.segment_id}`} value={transcriptText(item)} onChange={event => setTranslationDraft(current => ({ ...current, [item.segment_id]: event.target.value }))} rows={2} className="mt-1 field" /></div></div>)}</div>
            <button type="button" disabled={busy !== null || !targetLanguage.trim()} onClick={handleSaveTranslation} className="secondary mt-3">Сохранить перевод</button>
          </>}
        </StepCard>

        <StepCard number="3" title="Речевая дорожка" icon={<FileAudio size={16} />}>
          {!transcript ? <Hint>Сначала нужен сохранённый текст.</Hint> : <>
            <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-[var(--uv-border-strong)] bg-black/10 p-4 text-sm text-zinc-500 hover:text-zinc-300"><FileAudio size={17} /><span className="flex-1">Добавить готовую речевую дорожку</span><input type="file" accept="audio/*" className="hidden" onChange={event => handleAudioUpload(event.target.files?.[0] ?? null)} disabled={busy !== null} /></label>
            {state.prepared_audio.length > 0 && <Field label="Аудио"><select aria-label="Речевая дорожка" value={audio?.id ?? ''} onChange={event => setSelectedAudioId(event.target.value)} className="field">{state.prepared_audio.map(item => <option key={item.id} value={item.id}>{metadataText(item.metadata.original_name) ?? 'Речевая дорожка'}</option>)}</select></Field>}
            {audio && <audio controls src={preparedAudioMediaUrl(projectId, audio.id)} className="mt-2 w-full" />}
            {translation && <label className="mt-3 flex items-center gap-2 text-xs text-zinc-600"><input type="checkbox" checked={useTranslation} onChange={event => setUseTranslation(event.target.checked)} /> Использовать сохранённый перевод</label>}
            {transcript.segments.length > 1 && <Field label="Диапазон"><select aria-label="Фрагмент дубляжа" value={segmentId} onChange={event => setSelectedSegmentId(event.target.value)} className="field"><option value="">Весь выбранный текст</option>{transcript.segments.map((item, index) => <option key={item.segment_id} value={item.segment_id}>Фрагмент {index + 1} · {formatTimelineTime(item.start_us)}–{formatTimelineTime(item.end_us)}</option>)}</select></Field>}
            <button type="button" disabled={busy !== null || !audio || (useTranslation && !translation)} onClick={handleAttach} className="primary mt-3">Привязать дорожку к тексту</button>
            {takes.length > 1 && <Field label="Подготовленный вариант"><select aria-label="Вариант озвучки" value={take?.take_id ?? ''} onChange={event => { setSelectedTakeId(event.target.value); setContentOk(false); setSyncOk(false); }} className="field">{takes.map((item, index) => <option key={item.take_id} value={item.take_id}>Вариант {index + 1}</option>)}</select></Field>}
          </>}
        </StepCard>

        <StepCard number="4" title="Проверка и применение" icon={<CheckCircle2 size={16} />}>
          {!take ? <Hint>Сначала привяжите речевую дорожку.</Hint> : <>
            <label className="flex items-start gap-2 rounded-lg border border-[var(--uv-border)] bg-black/10 p-3 text-xs text-zinc-500"><input aria-label="Содержание и произношение проверены" type="checkbox" checked={contentOk} onChange={event => setContentOk(event.target.checked)} className="mt-0.5" /><span>Содержание и произношение соответствуют выбранному тексту.</span></label>
            <label className="mt-2 flex items-start gap-2 rounded-lg border border-[var(--uv-border)] bg-black/10 p-3 text-xs text-zinc-500"><input aria-label="Синхронизация с видео проверена" type="checkbox" checked={syncOk} onChange={event => setSyncOk(event.target.checked)} className="mt-0.5" /><span>Синхронизация с видео проверена.</span></label>
            <Field label="Примечание (необязательно)"><textarea value={reviewNote} onChange={event => setReviewNote(event.target.value)} rows={2} className="field" /></Field>
            <div className="grid grid-cols-3 gap-2"><button type="button" disabled={busy !== null || !contentOk || !syncOk} onClick={() => handleReview('approved')} className="rounded-lg bg-emerald-400 px-2 py-2 text-[11px] font-semibold text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-600">Одобрить</button><button type="button" disabled={busy !== null} onClick={() => handleReview('needs_revision')} className="rounded-lg border border-amber-400/20 px-2 py-2 text-[11px] text-amber-200">На доработку</button><button type="button" disabled={busy !== null} onClick={() => handleReview('rejected')} className="rounded-lg border border-rose-400/20 px-2 py-2 text-[11px] text-rose-200">Отклонить</button></div>
            {currentReview && <div className={`mt-3 rounded-xl border p-3 text-xs ${currentReview.verdict === 'approved' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : currentReview.verdict === 'needs_revision' ? 'border-amber-400/20 bg-amber-400/[0.06] text-amber-100' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}><p>{currentReview.verdict === 'approved' ? 'Проверка пройдена' : currentReview.verdict === 'needs_revision' ? 'Нужна доработка' : 'Вариант отклонён'}</p><p className="mt-1 opacity-70">Синхронизация: {currentReview.timing_pass ? 'норма' : 'проверьте'} · Аудио: {currentReview.audio_safety_pass ? 'норма' : 'проверьте'}</p></div>}
            {currentReview?.verdict === 'approved' && !acceptedCurrentTake && <button type="button" disabled={busy !== null} onClick={handleAccept} className="primary mt-3"><CheckCircle2 size={14} /> Применить озвучку</button>}
            {acceptedCurrentTake && <div className="mt-3 flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-3 text-sm text-emerald-200"><CheckCircle2 size={15} /> Озвучка применена.</div>}
          </>}
        </StepCard>
      </div>

      <div className="mt-4 rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div><p className="text-xs font-medium uppercase tracking-[0.14em] text-zinc-700">Результат</p><h3 className="mt-1 text-sm font-medium text-zinc-200">Видео с применённой озвучкой</h3><p className="mt-1 text-xs leading-5 text-zinc-600">Сборка доступна после применения хотя бы одной проверенной речевой дорожки.</p></div><button type="button" disabled={busy !== null || !source || acceptedForSource.length === 0} onClick={handleRender} className="primary">{busy === 'render' ? <Loader2 size={14} className="animate-spin" /> : <Mic2 size={14} />} {renders.length ? 'Пересобрать видео' : 'Собрать видео'}</button></div>
        {activeRender && <div className="mt-4 overflow-hidden rounded-xl border border-[var(--uv-border)] bg-black"><div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--uv-border)] px-3 py-2"><span className="text-xs text-emerald-300">Видео готово</span><div className="flex gap-2">{!activePreview && <button type="button" disabled={busy !== null} onClick={handlePreview} className="secondary"><MonitorPlay size={13} /> Подготовить просмотр</button>}<a href={projectArtifactMediaUrl(projectId, activeRender.id)} download className="secondary"><Download size={13} /> Скачать</a></div></div>{activePreview ? <video src={projectArtifactMediaUrl(projectId, activePreview.id)} controls playsInline preload="metadata" className="aspect-video w-full object-contain" /> : <div className="flex min-h-40 items-center justify-center p-6 text-center text-sm text-zinc-700">Итоговый файл сохранён. При необходимости подготовьте браузерный просмотр.</div>}</div>}
      </div>

      <style jsx global>{`
        .field { width:100%; border:1px solid var(--uv-border); border-radius:10px; background:rgba(0,0,0,.18); padding:9px 11px; color:#d4d4d8; font-size:12px; }
        .field:focus { border-color:rgba(139,124,246,.55); }
        .primary { display:inline-flex; align-items:center; justify-content:center; gap:6px; border-radius:10px; background:var(--uv-accent); padding:9px 13px; color:#090a0d; font-size:12px; font-weight:650; }
        .primary:disabled { cursor:not-allowed; background:#27272a; color:#52525b; }
        .secondary { display:inline-flex; align-items:center; justify-content:center; gap:6px; border:1px solid var(--uv-border-strong); border-radius:9px; background:var(--uv-surface-0); padding:8px 11px; color:#a1a1aa; font-size:11px; }
      `}</style>
    </section>
  );
}

function StepCard({ number, title, icon, children }: { number: string; title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><div className="flex items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-400/10 text-xs text-violet-300">{number}</span><span className="text-violet-300">{icon}</span><h3 className="text-sm font-medium text-zinc-200">{title}</h3></div><div className="mt-4">{children}</div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="mt-3 block text-[11px] text-zinc-600"><span className="mb-1.5 block">{label}</span>{children}</label>; }
function SmallInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="block text-[10px] text-zinc-700">{label}<input value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} className="mt-1 field" /></label>; }
function Hint({ children }: { children: React.ReactNode }) { return <div className="rounded-xl border border-dashed border-[var(--uv-border)] p-4 text-xs leading-5 text-zinc-700">{children}</div>; }
function Message({ tone, children }: { tone: 'ok' | 'error'; children: React.ReactNode }) { return <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${tone === 'ok' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}>{children}</div>; }
