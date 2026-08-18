'use client';

import {
  AlignHorizontalJustifyCenter,
  CheckCircle2,
  Languages,
  Loader2,
  MicVocal,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  getDubbingEditorState,
  type DubbingEditorState,
  type DubbingTranscript,
  type DubbingTranslation,
  type PreparedSpeechTake,
} from '@/lib/dubbingApi';
import {
  acceptForcedAlignment,
  attachGeneratedPreparedSpeech,
  createForcedAlignmentDraft,
  createLocalTranslationDraft,
  promoteGeneratedSpeechArtifact,
  saveTranslatedDraft,
  synthesizeSpeechWithExplicitRemoteConsent,
  type AlignmentDraft,
  type DubbingAlignmentState,
  type TranslationDraft,
} from '@/lib/dubbingPrecisionApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface DubbingPrecisionProductPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

type PrecisionState = DubbingEditorState & { dubbing_alignments?: DubbingAlignmentState };
type Busy = 'refresh' | 'translate' | 'save-translation' | 'tts' | 'align' | 'accept-align';

function transcriptLabel(item: DubbingTranscript, index: number): string {
  return `Текст ${index + 1} · ${item.language} · ${item.segments.length} фрагм.`;
}

function translationLabel(item: DubbingTranslation, index: number): string {
  return `Перевод ${index + 1} · ${item.target_language}`;
}

function takeLabel(item: PreparedSpeechTake, index: number): string {
  return `Озвучка ${index + 1} · ${(item.duration_us / 1_000_000).toFixed(2)} с`;
}

function secondsToUs(value: string): number | null {
  const parsed = Number(value.replace(',', '.'));
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed * 1_000_000) : null;
}

function usToSeconds(value: number): string {
  return (value / 1_000_000).toFixed(3);
}

export function DubbingPrecisionProductPanel({ projectId, onProjectChanged }: DubbingPrecisionProductPanelProps) {
  const [state, setState] = useState<PrecisionState | null>(null);
  const [selectedDubbingId, setSelectedDubbingId] = useState('');
  const [selectedTranslationId, setSelectedTranslationId] = useState('');
  const [targetLanguage, setTargetLanguage] = useState('ru');
  const [translationDraft, setTranslationDraft] = useState<TranslationDraft | null>(null);
  const [ttsUseTranslation, setTtsUseTranslation] = useState(true);
  const [ttsSegmentId, setTtsSegmentId] = useState('');
  const [ttsVoice, setTtsVoice] = useState('');
  const [ttsSpeed, setTtsSpeed] = useState('1.0');
  const [remoteConsent, setRemoteConsent] = useState(false);
  const [selectedTakeId, setSelectedTakeId] = useState('');
  const [alignmentDraft, setAlignmentDraft] = useState<AlignmentDraft | null>(null);
  const [busy, setBusy] = useState<Busy | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = async (): Promise<PrecisionState> => {
    const next = (await getDubbingEditorState(projectId)) as PrecisionState;
    setState(next);
    return next;
  };

  useEffect(() => {
    let active = true;
    getDubbingEditorState(projectId)
      .then(value => { if (active) setState(value as PrecisionState); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить инструменты точности'); });
    return () => { active = false; };
  }, [projectId]);

  const transcripts = state?.dubbing.transcripts ?? [];
  const transcript = useMemo(() => transcripts.find(item => item.dubbing_id === selectedDubbingId) ?? transcripts.at(-1) ?? null, [selectedDubbingId, transcripts]);
  const translations = useMemo(() => transcript && state ? state.dubbing.translations.filter(item => item.dubbing_id === transcript.dubbing_id) : [], [state, transcript]);
  const translation = useMemo(() => translations.find(item => item.translation_id === selectedTranslationId) ?? translations.at(-1) ?? null, [selectedTranslationId, translations]);
  const takes = useMemo(() => transcript && state ? state.prepared_speech.takes.filter(item => item.dubbing_id === transcript.dubbing_id) : [], [state, transcript]);
  const selectedTake = useMemo(() => takes.find(item => item.take_id === selectedTakeId) ?? takes.at(-1) ?? null, [selectedTakeId, takes]);
  const currentAlignment = useMemo(() => selectedTake ? state?.dubbing_alignments?.alignments.find(item => item.take_id === selectedTake.take_id) ?? null : null, [selectedTake, state]);
  const ttsSegment = useMemo(() => transcript?.segments.find(item => item.segment_id === ttsSegmentId) ?? transcript?.segments[0] ?? null, [transcript, ttsSegmentId]);
  const ttsText = useMemo(() => {
    if (!ttsSegment) return '';
    if (!ttsUseTranslation) return ttsSegment.text;
    return translation?.segments.find(item => item.segment_id === ttsSegment.segment_id)?.text ?? '';
  }, [translation, ttsSegment, ttsUseTranslation]);

  const run = async (action: Busy, work: () => Promise<void>) => {
    setBusy(action); setError(null); setNotice(null);
    try { await work(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Операция не выполнена'); }
    finally { setBusy(null); }
  };

  const handleAutoTranslate = () => {
    if (!transcript) return;
    void run('translate', async () => {
      const draft = await createLocalTranslationDraft(projectId, {
        source_language: transcript.language,
        target_language: targetLanguage,
        segments: transcript.segments.map(item => ({ segment_id: item.segment_id, text: item.text })),
      });
      setTranslationDraft(draft);
      setNotice('Черновик перевода готов. Проверьте его перед сохранением.');
    });
  };

  const handleSaveTranslation = () => {
    if (!transcript || !translationDraft) return;
    void run('save-translation', async () => {
      if (translationDraft.segments.some(item => !item.text.trim())) throw new Error('Заполните каждый фрагмент перевода.');
      const result = await saveTranslatedDraft(projectId, {
        dubbing_id: transcript.dubbing_id,
        target_language: translationDraft.target_language,
        segments: translationDraft.segments.map(item => ({ segment_id: item.segment_id, text: item.text.trim() })),
        ...(translation ? { translation_id: translation.translation_id } : {}),
      });
      setSelectedTranslationId(result.payload.translation.translation_id);
      setTranslationDraft(null);
      await refresh();
      setNotice('Проверенный перевод сохранён.');
    });
  };

  const handleTts = () => {
    if (!transcript || !ttsSegment) return;
    void run('tts', async () => {
      if (!remoteConsent) throw new Error('Подтвердите отправку выбранного текста во внешний сервис синтеза речи.');
      if (!ttsVoice.trim()) throw new Error('Укажите ID голоса.');
      if (!ttsText.trim()) throw new Error(ttsUseTranslation ? 'Для выбранного фрагмента нет сохранённого перевода.' : 'Выбранный фрагмент пуст.');
      const speed = Number(ttsSpeed.replace(',', '.'));
      if (!Number.isFinite(speed) || speed <= 0) throw new Error('Скорость должна быть положительным числом.');
      const synthesized = await synthesizeSpeechWithExplicitRemoteConsent(projectId, { text: ttsText, voice: ttsVoice.trim(), speed });
      const generatedArtifact = synthesized.result.artifact;
      if (!generatedArtifact?.id) throw new Error('Синтез завершился без готового аудиофайла.');
      const prepared = await promoteGeneratedSpeechArtifact(projectId, generatedArtifact.id);
      const attached = await attachGeneratedPreparedSpeech(projectId, {
        dubbing_id: transcript.dubbing_id,
        audio_id: prepared.id,
        segment_id: ttsSegment.segment_id,
        ...(ttsUseTranslation && translation ? { translation_id: translation.translation_id } : {}),
      });
      setSelectedTakeId(attached.payload.prepared_speech.take_id);
      setAlignmentDraft(null);
      setRemoteConsent(false);
      await refresh(); await onProjectChanged?.();
      setNotice('Синтезированная речь добавлена как новый вариант озвучки.');
    });
  };

  const handleAlign = () => {
    if (!selectedTake) return;
    void run('align', async () => {
      setAlignmentDraft(await createForcedAlignmentDraft(projectId, selectedTake.take_id));
      setNotice('Черновик выравнивания готов. Проверьте слова и таймкоды перед применением.');
    });
  };

  const handleAcceptAlignment = () => {
    if (!alignmentDraft) return;
    void run('accept-align', async () => {
      await acceptForcedAlignment(projectId, alignmentDraft);
      setAlignmentDraft(null);
      await refresh();
      setNotice('Проверенное выравнивание применено.');
    });
  };

  const updateAlignmentMark = (markId: string, field: 'text' | 'audio_start_us' | 'audio_end_us', value: string) => {
    setAlignmentDraft(current => {
      if (!current) return current;
      return {
        ...current,
        marks: current.marks.map(mark => {
          if (mark.mark_id !== markId) return mark;
          if (field === 'text') return { ...mark, text: value };
          const parsed = secondsToUs(value);
          return parsed === null ? mark : { ...mark, [field]: parsed };
        }),
      };
    });
  };

  if (!state) return <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-600">Загрузка инструментов точности…</section>;

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><AlignHorizontalJustifyCenter size={17} /></span>
          <div><h2 className="text-lg font-medium text-zinc-100">Точность речи</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Дополнительный перевод, синтез речи и точная привязка слов ко времени. Черновики не меняют проект, пока вы их явно не сохраните или не примените.</p></div>
        </div>
        <button type="button" disabled={busy !== null} onClick={() => void run('refresh', async () => { await refresh(); setNotice('Данные обновлены.'); })} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border)] px-3 text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-40">{busy === 'refresh' ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} Обновить</button>
      </div>

      {error && <Banner tone="error">{error}</Banner>}
      {notice && <Banner tone="ok">{notice}</Banner>}

      {transcripts.length === 0 ? <div className="mt-5 rounded-xl border border-dashed border-[var(--uv-border)] p-5 text-sm text-zinc-700">Сначала сохраните проверенный текст в разделе «Дубляж».</div> : (
        <>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <label className="text-xs text-zinc-600">Проверенный текст<select value={transcript?.dubbing_id ?? ''} onChange={event => { setSelectedDubbingId(event.target.value); setSelectedTranslationId(''); setTranslationDraft(null); setTtsSegmentId(''); setSelectedTakeId(''); setAlignmentDraft(null); }} className="field mt-2">{transcripts.map((item, index) => <option key={item.dubbing_id} value={item.dubbing_id}>{transcriptLabel(item, index)}</option>)}</select></label>
            <label className="text-xs text-zinc-600">Сохранённый перевод<select value={translation?.translation_id ?? ''} onChange={event => setSelectedTranslationId(event.target.value)} className="field mt-2"><option value="">Нет / выбрать позже</option>{translations.map((item, index) => <option key={item.translation_id} value={item.translation_id}>{translationLabel(item, index)}</option>)}</select></label>
          </div>

          <div className="mt-5 grid gap-4 xl:grid-cols-3">
            <ToolCard icon={<Languages size={16} />} title="Локальный перевод" description="Создать черновик перевода без отправки текста во внешний сервис.">
              <label className="text-[11px] text-zinc-600">Язык перевода<input value={targetLanguage} onChange={event => setTargetLanguage(event.target.value)} className="field mt-1.5" /></label>
              <button type="button" disabled={busy !== null || !transcript || !targetLanguage.trim()} onClick={handleAutoTranslate} className="secondary mt-3">{busy === 'translate' ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />} Создать черновик</button>
              {translationDraft && <div className="mt-3 max-h-80 space-y-2 overflow-y-auto">{translationDraft.segments.map(item => <textarea key={item.segment_id} aria-label={`Черновик перевода ${item.segment_id}`} value={item.text} onChange={event => setTranslationDraft(current => current ? { ...current, segments: current.segments.map(segment => segment.segment_id === item.segment_id ? { ...segment, text: event.target.value } : segment) } : current)} rows={2} className="field" />)}<button type="button" disabled={busy !== null} onClick={handleSaveTranslation} className="primary w-full"><CheckCircle2 size={13} /> Сохранить перевод</button></div>}
            </ToolCard>

            <ToolCard icon={<MicVocal size={16} />} title="Синтез речи" description="Создать новый голосовой вариант для выбранного фрагмента. Текст отправляется во внешний сервис только после явного подтверждения.">
              {transcript && <label className="text-[11px] text-zinc-600">Фрагмент<select value={ttsSegment?.segment_id ?? ''} onChange={event => setTtsSegmentId(event.target.value)} className="field mt-1.5">{transcript.segments.map((item, index) => <option key={item.segment_id} value={item.segment_id}>Фрагмент {index + 1} · {formatTimelineTime(item.start_us)}–{formatTimelineTime(item.end_us)}</option>)}</select></label>}
              {translation && <label className="mt-2 flex items-center gap-2 text-[11px] text-zinc-600"><input type="checkbox" checked={ttsUseTranslation} onChange={event => setTtsUseTranslation(event.target.checked)} /> Использовать перевод</label>}
              <label className="mt-2 block text-[11px] text-zinc-600">ID голоса<input aria-label="ID голоса синтеза" value={ttsVoice} onChange={event => setTtsVoice(event.target.value)} className="field mt-1.5" placeholder="например, ru-RU-…" /></label>
              <label className="mt-2 block text-[11px] text-zinc-600">Скорость<input aria-label="Скорость синтеза" value={ttsSpeed} onChange={event => setTtsSpeed(event.target.value)} className="field mt-1.5" /></label>
              <div className="mt-3 rounded-xl border border-amber-400/15 bg-amber-400/[0.05] p-3"><label className="flex items-start gap-2 text-[11px] leading-5 text-amber-100/80"><input type="checkbox" checked={remoteConsent} onChange={event => setRemoteConsent(event.target.checked)} className="mt-0.5" /> Разрешить однократную отправку выбранного текста во внешний сервис синтеза речи.</label></div>
              <button type="button" disabled={busy !== null || !ttsSegment || !ttsVoice.trim() || !remoteConsent || !ttsText.trim()} onClick={handleTts} className="primary mt-3 w-full">{busy === 'tts' ? <Loader2 size={13} className="animate-spin" /> : <MicVocal size={13} />} Создать речь</button>
            </ToolCard>

            <ToolCard icon={<AlignHorizontalJustifyCenter size={16} />} title="Точное выравнивание" description="Проверить, где именно слова звучат в выбранном варианте озвучки, и при необходимости поправить таймкоды.">
              {takes.length === 0 ? <p className="text-xs leading-5 text-zinc-700">Сначала подготовьте речевую дорожку в «Дубляже» или создайте её здесь.</p> : <>
                <label className="text-[11px] text-zinc-600">Озвучка<select aria-label="Озвучка для выравнивания" value={selectedTake?.take_id ?? ''} onChange={event => { setSelectedTakeId(event.target.value); setAlignmentDraft(null); }} className="field mt-1.5">{takes.map((item, index) => <option key={item.take_id} value={item.take_id}>{takeLabel(item, index)}</option>)}</select></label>
                <button type="button" disabled={busy !== null || !selectedTake} onClick={handleAlign} className="secondary mt-3">Создать черновик выравнивания</button>
                {currentAlignment && !alignmentDraft && <div className="mt-3 rounded-xl border border-emerald-400/15 bg-emerald-400/[0.05] p-3 text-xs text-emerald-200">Для выбранной озвучки уже сохранено проверенное выравнивание: {currentAlignment.marks.length} отметок.</div>}
              </>}
            </ToolCard>
          </div>

          {alignmentDraft && <div className="mt-4 rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><div className="flex items-center justify-between gap-3"><div><h3 className="text-sm font-medium text-zinc-200">Проверка выравнивания</h3><p className="mt-1 text-xs text-zinc-700">Исправьте текст или время при необходимости, затем примените.</p></div><button type="button" disabled={busy !== null} onClick={handleAcceptAlignment} className="primary">{busy === 'accept-align' ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle2 size={13} />} Применить выравнивание</button></div><div className="mt-4 max-h-80 space-y-2 overflow-y-auto">{alignmentDraft.marks.map((mark, index) => <div key={mark.mark_id} className="grid gap-2 rounded-lg border border-[var(--uv-border)] bg-black/10 p-2 sm:grid-cols-[1fr_110px_110px]"><input aria-label={`Слово выравнивания ${index + 1}`} value={mark.text} onChange={event => updateAlignmentMark(mark.mark_id, 'text', event.target.value)} className="field" /><input aria-label={`Начало слова ${index + 1}`} value={usToSeconds(mark.audio_start_us)} onChange={event => updateAlignmentMark(mark.mark_id, 'audio_start_us', event.target.value)} className="field" /><input aria-label={`Конец слова ${index + 1}`} value={usToSeconds(mark.audio_end_us)} onChange={event => updateAlignmentMark(mark.mark_id, 'audio_end_us', event.target.value)} className="field" /></div>)}</div></div>}
        </>
      )}

      <style jsx global>{`.field{width:100%;border:1px solid var(--uv-border);border-radius:10px;background:rgba(0,0,0,.18);padding:9px 11px;color:#d4d4d8;font-size:12px}.field:focus{border-color:rgba(139,124,246,.55)}.primary{display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:10px;background:var(--uv-accent);padding:9px 13px;color:#090a0d;font-size:12px;font-weight:650}.primary:disabled{cursor:not-allowed;background:#27272a;color:#52525b}.secondary{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--uv-border-strong);border-radius:10px;background:var(--uv-surface-1);padding:9px 12px;color:#d4d4d8;font-size:12px}.secondary:disabled{opacity:.35}`}</style>
    </section>
  );
}

function ToolCard({ icon, title, description, children }: { icon: React.ReactNode; title: string; description: string; children: React.ReactNode }) { return <div className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><div className="flex items-start gap-2.5"><span className="text-violet-300">{icon}</span><div><h3 className="text-sm font-medium text-zinc-200">{title}</h3><p className="mt-1 text-xs leading-5 text-zinc-700">{description}</p></div></div><div className="mt-4">{children}</div></div>; }
function Banner({ tone, children }: { tone: 'ok' | 'error'; children: React.ReactNode }) { return <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${tone === 'ok' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}>{children}</div>; }
