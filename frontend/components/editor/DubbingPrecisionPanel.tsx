'use client';

import {
  AlignHorizontalJustifyCenter,
  CheckCircle2,
  Languages,
  Loader2,
  MicVocal,
  RefreshCw,
  ShieldCheck,
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

interface DubbingPrecisionPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

type PrecisionState = DubbingEditorState & {
  dubbing_alignments?: DubbingAlignmentState;
};

type Busy = 'refresh' | 'translate' | 'save-translation' | 'tts' | 'align' | 'accept-align';

function secondsToUs(value: string): number | null {
  const parsed = Number(value.replace(',', '.'));
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed * 1_000_000);
}

function usToSeconds(value: number): string {
  return (value / 1_000_000).toFixed(3);
}

function transcriptLabel(item: DubbingTranscript): string {
  return `${item.language} · ${item.origin} · ${item.segments.length} сегм.`;
}

function translationLabel(item: DubbingTranslation): string {
  return `${item.target_language} · ${item.translation_id}`;
}

function takeLabel(item: PreparedSpeechTake): string {
  return `${item.script_kind} · ${item.segment_id ?? 'весь текст'} · ${(item.duration_us / 1_000_000).toFixed(2)} с`;
}

export function DubbingPrecisionPanel({ projectId, onProjectChanged }: DubbingPrecisionPanelProps) {
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
  const [createdTakeId, setCreatedTakeId] = useState<string | null>(null);

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
      .then(value => {
        if (active) setState(value as PrecisionState);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить Stage 5 precision state');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const transcripts = state?.dubbing.transcripts ?? [];
  const transcript = useMemo(
    () =>
      transcripts.find(item => item.dubbing_id === selectedDubbingId) ??
      transcripts[transcripts.length - 1] ??
      null,
    [selectedDubbingId, transcripts],
  );
  const translations = useMemo(
    () =>
      transcript && state
        ? state.dubbing.translations.filter(item => item.dubbing_id === transcript.dubbing_id)
        : [],
    [state, transcript],
  );
  const translation = useMemo(
    () =>
      translations.find(item => item.translation_id === selectedTranslationId) ??
      translations[translations.length - 1] ??
      null,
    [selectedTranslationId, translations],
  );
  const takes = useMemo(
    () =>
      transcript && state
        ? state.prepared_speech.takes.filter(item => item.dubbing_id === transcript.dubbing_id)
        : [],
    [state, transcript],
  );
  const selectedTake = useMemo(
    () => takes.find(item => item.take_id === selectedTakeId) ?? takes[takes.length - 1] ?? null,
    [selectedTakeId, takes],
  );
  const currentAlignment = useMemo(
    () =>
      selectedTake
        ? state?.dubbing_alignments?.alignments.find(item => item.take_id === selectedTake.take_id) ?? null
        : null,
    [selectedTake, state],
  );
  const ttsSegment = useMemo(() => {
    if (!transcript) return null;
    return (
      transcript.segments.find(item => item.segment_id === ttsSegmentId) ??
      transcript.segments[0] ??
      null
    );
  }, [transcript, ttsSegmentId]);
  const ttsText = useMemo(() => {
    if (!ttsSegment) return '';
    if (!ttsUseTranslation) return ttsSegment.text;
    return (
      translation?.segments.find(item => item.segment_id === ttsSegment.segment_id)?.text ?? ''
    );
  }, [translation, ttsSegment, ttsUseTranslation]);

  const run = async (action: Busy, work: () => Promise<void>) => {
    setBusy(action);
    setError(null);
    setNotice(null);
    try {
      await work();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stage 5 precision operation failed');
    } finally {
      setBusy(null);
    }
  };

  const handleRefresh = () =>
    run('refresh', async () => {
      await refresh();
      setNotice('Precision state перечитан из канонического Project Store.');
    });

  const handleAutoTranslate = () => {
    if (!transcript) return;
    void run('translate', async () => {
      const draft = await createLocalTranslationDraft(projectId, {
        source_language: transcript.language,
        target_language: targetLanguage,
        segments: transcript.segments.map(item => ({
          segment_id: item.segment_id,
          text: item.text,
        })),
      });
      setTranslationDraft(draft);
      setNotice(
        'Argos создал только перевод-черновик. Проверьте/исправьте текст и отдельно сохраните его в Project Store.',
      );
    });
  };

  const updateTranslationDraft = (segmentId: string, text: string) => {
    setTranslationDraft(current =>
      current
        ? {
            ...current,
            segments: current.segments.map(item =>
              item.segment_id === segmentId ? { ...item, text } : item,
            ),
          }
        : current,
    );
  };

  const handleSaveTranslationDraft = () => {
    if (!transcript || !translationDraft) return;
    void run('save-translation', async () => {
      if (translationDraft.segments.some(item => !item.text.trim())) {
        throw new Error('Перед сохранением заполните каждый сегмент перевода.');
      }
      const result = await saveTranslatedDraft(projectId, {
        dubbing_id: transcript.dubbing_id,
        target_language: translationDraft.target_language,
        segments: translationDraft.segments.map(item => ({
          segment_id: item.segment_id,
          text: item.text.trim(),
        })),
        ...(translation ? { translation_id: translation.translation_id } : {}),
      });
      setSelectedTranslationId(result.payload.translation.translation_id);
      setTranslationDraft(null);
      await refresh();
      setNotice('Проверенный перевод принят и привязан к точной ревизии transcript.');
    });
  };

  const handleTts = () => {
    if (!transcript || !ttsSegment) return;
    void run('tts', async () => {
      if (!remoteConsent) {
        throw new Error('Для Edge TTS нужно явно подтвердить удалённую отправку выбранного текста.');
      }
      if (!ttsVoice.trim()) {
        throw new Error('Укажите Edge TTS voice ID. UV Studio не подменяет выбор голоса скрытым значением.');
      }
      if (!ttsText.trim()) {
        throw new Error(
          ttsUseTranslation
            ? 'Для выбранного сегмента нет сохранённого перевода.'
            : 'Выбранный transcript segment пуст.',
        );
      }
      const speed = Number(ttsSpeed.replace(',', '.'));
      if (!Number.isFinite(speed) || speed <= 0) {
        throw new Error('Скорость TTS должна быть положительным числом.');
      }
      const synthesized = await synthesizeSpeechWithExplicitRemoteConsent(projectId, {
        text: ttsText,
        voice: ttsVoice.trim(),
        speed,
      });
      const generatedArtifact = synthesized.result.artifact;
      if (!generatedArtifact?.id) {
        throw new Error('TTS завершился без зарегистрированного project-owned audio artifact.');
      }
      const prepared = await promoteGeneratedSpeechArtifact(projectId, generatedArtifact.id);
      const attached = await attachGeneratedPreparedSpeech(projectId, {
        dubbing_id: transcript.dubbing_id,
        audio_id: prepared.id,
        segment_id: ttsSegment.segment_id,
        ...(ttsUseTranslation && translation
          ? { translation_id: translation.translation_id }
          : {}),
      });
      const newTakeId = attached.payload.prepared_speech.take_id;
      setCreatedTakeId(newTakeId);
      setSelectedTakeId(newTakeId);
      setAlignmentDraft(null);
      setRemoteConsent(false);
      await refresh();
      await onProjectChanged?.();
      setNotice(
        'TTS создан с одноразовым D-017 consent, локально перепроверен FFprobe/SHA и привязан как обычный PreparedSpeech take.',
      );
    });
  };

  const handleAlign = () => {
    if (!selectedTake) return;
    void run('align', async () => {
      const draft = await createForcedAlignmentDraft(projectId, selectedTake.take_id);
      setAlignmentDraft(draft);
      setNotice(
        'WhisperX создал alignment draft. Project Store ещё не изменён — проверьте word timestamps и отдельно примите их.',
      );
    });
  };

  const updateAlignmentMark = (
    markId: string,
    field: 'text' | 'audio_start_us' | 'audio_end_us',
    value: string,
  ) => {
    setAlignmentDraft(current => {
      if (!current) return current;
      return {
        ...current,
        marks: current.marks.map(mark => {
          if (mark.mark_id !== markId) return mark;
          if (field === 'text') return { ...mark, text: value };
          const parsed = secondsToUs(value);
          if (parsed === null) return mark;
          return { ...mark, [field]: parsed };
        }),
      };
    });
  };

  const handleAcceptAlignment = () => {
    if (!alignmentDraft) return;
    void run('accept-align', async () => {
      const result = await acceptForcedAlignment(projectId, alignmentDraft);
      setAlignmentDraft(null);
      await refresh();
      setNotice(
        `Forced alignment ${result.payload.alignment.alignment_id} принят с серверной повторной привязкой к take/script/audio SHA.`,
      );
    });
  };

  if (!state) {
    return (
      <section className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-400">
        Загрузка точного перевода/выравнивания…
      </section>
    );
  }

  return (
    <section className="mt-4 rounded-2xl border border-cyan-900/60 bg-slate-950/80 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyan-300">
            <AlignHorizontalJustifyCenter size={18} />
            <p className="text-xs uppercase tracking-[0.18em]">Stage 5 · precision tools</p>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-slate-100">Перевод, TTS и forced alignment</h2>
          <p className="mt-2 max-w-4xl text-xs leading-5 text-slate-500">
            Argos и WhisperX остаются сменными capability-движками. Их вывод сначала является черновиком. Edge TTS использует одноразовое D-017 согласие, а результат проходит тот же PreparedSpeech → Review → Accept путь, что и запись.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          disabled={busy !== null}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-slate-500 disabled:opacity-40"
        >
          {busy === 'refresh' ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Перечитать
        </button>
      </div>

      {error && <Banner tone="error">{error}</Banner>}
      {notice && <Banner tone="ok">{notice}</Banner>}

      {transcripts.length === 0 ? (
        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-500">
          Сначала примите transcript в основном блоке дубляжа выше.
        </div>
      ) : (
        <>
          <div className="mt-5 grid gap-3 lg:grid-cols-2">
            <label className="text-xs text-slate-500">
              Transcript
              <select
                value={transcript?.dubbing_id ?? ''}
                onChange={event => {
                  setSelectedDubbingId(event.target.value);
                  setSelectedTranslationId('');
                  setTranslationDraft(null);
                  setTtsSegmentId('');
                  setSelectedTakeId('');
                  setAlignmentDraft(null);
                }}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
              >
                {transcripts.map(item => (
                  <option key={item.dubbing_id} value={item.dubbing_id}>{transcriptLabel(item)}</option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-500">
              Сохранённый перевод
              <select
                value={translation?.translation_id ?? ''}
                onChange={event => setSelectedTranslationId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
              >
                {translations.length === 0 && <option value="">Нет сохранённого перевода</option>}
                {translations.map(item => (
                  <option key={item.translation_id} value={item.translation_id}>{translationLabel(item)}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
              <div className="flex items-center gap-2 text-violet-300">
                <Languages size={16} />
                <h3 className="text-sm font-medium">Argos: перевод-черновик</h3>
              </div>
              <p className="mt-2 text-[11px] leading-5 text-slate-500">
                Offline/local free. Если runtime или языковая пара не установлены, capability останется configuration_required.
              </p>
              <label className="mt-3 block text-xs text-slate-500">
                Язык назначения
                <input
                  value={targetLanguage}
                  onChange={event => setTargetLanguage(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200"
                />
              </label>
              <button
                type="button"
                onClick={handleAutoTranslate}
                disabled={busy !== null || !transcript}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-violet-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
              >
                {busy === 'translate' ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                Создать локальный черновик
              </button>

              {translationDraft && (
                <div className="mt-4 max-h-80 space-y-2 overflow-y-auto pr-1">
                  {translationDraft.segments.map(item => (
                    <div key={item.segment_id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-2">
                      <p className="font-mono text-[10px] text-slate-600">{item.segment_id}</p>
                      <textarea
                        rows={3}
                        value={item.text}
                        onChange={event => updateTranslationDraft(item.segment_id, event.target.value)}
                        className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 p-2 text-xs text-slate-200"
                      />
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={handleSaveTranslationDraft}
                    disabled={busy !== null}
                    className="inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
                  >
                    {busy === 'save-translation' ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    Принять проверенный перевод
                  </button>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
              <div className="flex items-center gap-2 text-sky-300">
                <MicVocal size={16} />
                <h3 className="text-sm font-medium">Edge TTS → PreparedSpeech</h3>
              </div>
              <p className="mt-2 text-[11px] leading-5 text-slate-500">
                Текст отправляется удалённому Edge TTS только после явного согласия. Сгенерированный MP3 затем копируется в assets/, заново хешируется и проверяется FFprobe.
              </p>
              <label className="mt-3 block text-xs text-slate-500">
                Сегмент
                <select
                  value={ttsSegment?.segment_id ?? ''}
                  onChange={event => setTtsSegmentId(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200"
                >
                  {transcript?.segments.map(item => (
                    <option key={item.segment_id} value={item.segment_id}>
                      {formatTimelineTime(item.start_us)}–{formatTimelineTime(item.end_us)} · {item.text.slice(0, 38)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="mt-3 flex items-center gap-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={ttsUseTranslation}
                  onChange={event => setTtsUseTranslation(event.target.checked)}
                />
                Использовать сохранённый перевод
              </label>
              <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/70 p-2 text-xs leading-5 text-slate-300">
                {ttsText || 'Для выбранного режима текст пока недоступен.'}
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <label className="col-span-2 text-xs text-slate-500">
                  Edge voice ID
                  <input
                    value={ttsVoice}
                    onChange={event => setTtsVoice(event.target.value)}
                    placeholder="например, locale-VoiceNeural"
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-200"
                  />
                </label>
                <label className="text-xs text-slate-500">
                  Скорость
                  <input
                    value={ttsSpeed}
                    onChange={event => setTtsSpeed(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-2 text-xs text-slate-200"
                  />
                </label>
              </div>
              <label className="mt-3 flex items-start gap-2 rounded-lg border border-amber-900/50 bg-amber-950/15 p-2 text-[11px] leading-5 text-amber-100">
                <input
                  type="checkbox"
                  checked={remoteConsent}
                  onChange={event => setRemoteConsent(event.target.checked)}
                  className="mt-1"
                />
                Я разрешаю одноразово отправить показанный выше текст в удалённый Edge TTS для синтеза речи.
              </label>
              <button
                type="button"
                onClick={handleTts}
                disabled={busy !== null || !transcript || !ttsSegment || !ttsText || !remoteConsent}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-sky-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
              >
                {busy === 'tts' ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                Синтезировать и подготовить
              </button>
              {createdTakeId && (
                <p className="mt-2 font-mono text-[10px] text-emerald-400">PreparedSpeech: {createdTakeId}</p>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
              <div className="flex items-center gap-2 text-cyan-300">
                <AlignHorizontalJustifyCenter size={16} />
                <h3 className="text-sm font-medium">WhisperX: forced alignment</h3>
              </div>
              <p className="mt-2 text-[11px] leading-5 text-slate-500">
                Optional heavy precision-layer. Работает только с локальным model cache; скрыто модели не скачивает. В Project Store сохраняются только provider-neutral marks.
              </p>
              {takes.length === 0 ? (
                <p className="mt-3 text-xs text-slate-500">Сначала создайте PreparedSpeech take.</p>
              ) : (
                <>
                  <select
                    value={selectedTake?.take_id ?? ''}
                    onChange={event => {
                      setSelectedTakeId(event.target.value);
                      setAlignmentDraft(null);
                    }}
                    className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200"
                  >
                    {takes.map(item => (
                      <option key={item.take_id} value={item.take_id}>{takeLabel(item)}</option>
                    ))}
                  </select>
                  {currentAlignment && (
                    <div className="mt-2 rounded-lg border border-emerald-900/50 bg-emerald-950/15 p-2 text-[11px] text-emerald-200">
                      Current alignment: {currentAlignment.alignment_id} · {currentAlignment.marks.length} marks
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleAlign}
                    disabled={busy !== null || !selectedTake}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg border border-cyan-700 bg-cyan-950/20 px-3 py-2 text-xs text-cyan-100 disabled:opacity-40"
                  >
                    {busy === 'align' ? <Loader2 size={14} className="animate-spin" /> : <AlignHorizontalJustifyCenter size={14} />}
                    Создать alignment draft
                  </button>
                </>
              )}

              {alignmentDraft && (
                <div className="mt-4">
                  <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
                    {alignmentDraft.marks.map(mark => (
                      <div key={mark.mark_id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-2">
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            value={mark.text}
                            onChange={event => updateAlignmentMark(mark.mark_id, 'text', event.target.value)}
                            className="col-span-2 rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs"
                          />
                          <label className="text-[10px] text-slate-600">
                            start, s
                            <input
                              key={`${mark.mark_id}-start-${mark.audio_start_us}`}
                              defaultValue={usToSeconds(mark.audio_start_us)}
                              onBlur={event => updateAlignmentMark(mark.mark_id, 'audio_start_us', event.target.value)}
                              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300"
                            />
                          </label>
                          <label className="text-[10px] text-slate-600">
                            end, s
                            <input
                              key={`${mark.mark_id}-end-${mark.audio_end_us}`}
                              defaultValue={usToSeconds(mark.audio_end_us)}
                              onBlur={event => updateAlignmentMark(mark.mark_id, 'audio_end_us', event.target.value)}
                              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300"
                            />
                          </label>
                        </div>
                        <p className="mt-1 font-mono text-[10px] text-slate-600">
                          {mark.unit} · confidence {mark.confidence ?? '—'}
                        </p>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={handleAcceptAlignment}
                    disabled={busy !== null}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
                  >
                    {busy === 'accept-align' ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    Принять проверенное выравнивание
                  </button>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function Banner({ children, tone }: { children: React.ReactNode; tone: 'error' | 'ok' }) {
  return (
    <div
      className={`mt-4 rounded-xl border p-3 text-xs ${
        tone === 'error'
          ? 'border-red-900/70 bg-red-950/35 text-red-200'
          : 'border-emerald-900/60 bg-emerald-950/20 text-emerald-200'
      }`}
    >
      {children}
    </div>
  );
}
