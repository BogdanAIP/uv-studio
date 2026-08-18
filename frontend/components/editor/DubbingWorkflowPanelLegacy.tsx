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
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  acceptAsrTranscript,
  acceptDubbingReview,
  attachPreparedSpeech,
  DubbingEditorState,
  DubbingTranscriptSegment,
  getDubbingEditorState,
  preparedAudioMediaUrl,
  renderAcceptedDubbing,
  reviewPreparedSpeech,
  saveDubbingTranslation,
  transcribeProjectSource,
  uploadPreparedAudio,
  type AsrDraft,
} from '@/lib/dubbingApi';
import { projectArtifactMediaUrl, projectSourceMediaUrl } from '@/lib/editorApi';
import { createBrowserPreview } from '@/lib/renderApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface DubbingWorkflowPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

type BusyAction =
  | 'asr'
  | 'accept-asr'
  | 'translation'
  | 'upload'
  | 'attach'
  | 'review'
  | 'accept'
  | 'render'
  | 'preview'
  | 'refresh';

function metadataNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function toUs(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value.replace(',', '.'));
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed * 1_000_000);
}

function latestById<T extends { [key: string]: unknown }>(values: T[], key: keyof T): T | null {
  if (values.length === 0) return null;
  return [...values].sort((a, b) => String(a[key]).localeCompare(String(b[key]))).at(-1) ?? null;
}

export function DubbingWorkflowPanel({ projectId, onProjectChanged }: DubbingWorkflowPanelProps) {
  const [state, setState] = useState<DubbingEditorState | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState<string>('');
  const [selectedDubbingId, setSelectedDubbingId] = useState<string>('');
  const [selectedTranslationId, setSelectedTranslationId] = useState<string>('');
  const [selectedAudioId, setSelectedAudioId] = useState<string>('');
  const [selectedSegmentId, setSelectedSegmentId] = useState<string>('');
  const [selectedTakeId, setSelectedTakeId] = useState<string>('');
  const [asrLanguage, setAsrLanguage] = useState('auto');
  const [asrStartSec, setAsrStartSec] = useState('');
  const [asrEndSec, setAsrEndSec] = useState('');
  const [asrDraft, setAsrDraft] = useState<AsrDraft | null>(null);
  const [targetLanguage, setTargetLanguage] = useState('ru');
  const [translationDraft, setTranslationDraft] = useState<Record<string, string>>({});
  const [useTranslation, setUseTranslation] = useState(true);
  const [reviewContent, setReviewContent] = useState(false);
  const [reviewSync, setReviewSync] = useState(false);
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
      .then(value => {
        if (active) setState(value);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить дубляж');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const source = useMemo(() => {
    if (!state) return null;
    return state.sources.find(item => item.id === selectedSourceId) ?? state.sources[0] ?? null;
  }, [selectedSourceId, state]);

  const sourceTranscripts = useMemo(
    () =>
      state && source
        ? state.dubbing.transcripts.filter(item => item.source_id === source.id)
        : [],
    [source, state],
  );
  const transcript = useMemo(
    () =>
      sourceTranscripts.find(item => item.dubbing_id === selectedDubbingId) ??
      sourceTranscripts[sourceTranscripts.length - 1] ??
      null,
    [selectedDubbingId, sourceTranscripts],
  );
  const translations = useMemo(
    () =>
      state && transcript
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
  const audio = useMemo(
    () =>
      state?.prepared_audio.find(item => item.id === selectedAudioId) ??
      state?.prepared_audio[state.prepared_audio.length - 1] ??
      null,
    [selectedAudioId, state],
  );
  const segmentId =
    selectedSegmentId && transcript?.segments.some(item => item.segment_id === selectedSegmentId)
      ? selectedSegmentId
      : transcript?.segments[0]?.segment_id ?? '';
  const takes = useMemo(
    () =>
      state && transcript
        ? state.prepared_speech.takes.filter(item => item.dubbing_id === transcript.dubbing_id)
        : [],
    [state, transcript],
  );
  const take = useMemo(
    () => takes.find(item => item.take_id === selectedTakeId) ?? takes[takes.length - 1] ?? null,
    [selectedTakeId, takes],
  );
  const takeReviews = useMemo(
    () => (state && take ? state.dubbing_reviews.filter(item => item.take_id === take.take_id) : []),
    [state, take],
  );
  const currentReview = latestById(takeReviews, 'review_id');
  const acceptedForSource = useMemo(
    () => (state && source ? state.accepted_dubbing.filter(item => item.source_id === source.id) : []),
    [source, state],
  );
  const renders = useMemo(
    () =>
      state && source
        ? state.artifacts.filter(
            item => item.kind === 'video' && item.metadata.lifecycle === 'dubbing_render' && item.metadata.source_id === source.id,
          )
        : [],
    [source, state],
  );
  const activeRender = renders.find(item => item.id === latestRenderId) ?? renders[renders.length - 1] ?? null;
  const previews = useMemo(
    () =>
      state && activeRender
        ? state.artifacts.filter(
            item =>
              item.kind === 'video' &&
              item.metadata.lifecycle === 'browser_preview' &&
              item.metadata.source_artifact_id === activeRender.id,
          )
        : [],
    [activeRender, state],
  );
  const activePreview =
    previews.find(item => item.id === latestPreviewId) ?? previews[previews.length - 1] ?? null;

  const run = async (action: BusyAction, work: () => Promise<void>) => {
    setBusy(action);
    setError(null);
    setNotice(null);
    try {
      await work();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Операция дубляжа завершилась ошибкой');
    } finally {
      setBusy(null);
    }
  };

  const handleRefresh = () =>
    run('refresh', async () => {
      await refresh();
      setNotice('Состояние проекта перечитано из Project Store.');
    });

  const handleTranscribe = () => {
    if (!source) return;
    void run('asr', async () => {
      const startUs = toUs(asrStartSec);
      const endUs = toUs(asrEndSec);
      if ((startUs === null) !== (endUs === null)) {
        throw new Error('Для частичного распознавания укажите и начало, и конец диапазона.');
      }
      if (startUs !== null && endUs !== null && endUs <= startUs) {
        throw new Error('Конец диапазона распознавания должен быть позже начала.');
      }
      const draft = await transcribeProjectSource(projectId, {
        source_id: source.id,
        language: asrLanguage.trim() || 'auto',
        ...(startUs !== null && endUs !== null ? { start_us: startUs, end_us: endUs } : {}),
      });
      setAsrDraft(draft);
      setNotice('ASR завершён. Текст пока не записан в проект — проверьте и исправьте черновик.');
    });
  };

  const updateAsrText = (segmentIdValue: string, text: string) => {
    setAsrDraft(current =>
      current
        ? {
            ...current,
            segments: current.segments.map(item =>
              item.segment_id === segmentIdValue ? { ...item, text } : item,
            ),
          }
        : current,
    );
  };

  const handleAcceptAsr = () => {
    if (!asrDraft) return;
    void run('accept-asr', async () => {
      if (asrDraft.segments.some(item => !item.text.trim())) {
        throw new Error('Перед принятием заполните текст каждого сегмента.');
      }
      const accepted = await acceptAsrTranscript(projectId, asrDraft);
      setSelectedDubbingId(accepted.dubbing_id);
      setAsrDraft(null);
      await refresh();
      await onProjectChanged?.();
      setNotice('Проверенный transcript принят в каноническое состояние проекта.');
    });
  };

  const existingTranslationText = (segment: DubbingTranscriptSegment): string =>
    translation?.segments.find(item => item.segment_id === segment.segment_id)?.text ?? segment.text;

  const translationText = (segment: DubbingTranscriptSegment): string =>
    translationDraft[segment.segment_id] ?? existingTranslationText(segment);

  const handleSaveTranslation = () => {
    if (!transcript) return;
    void run('translation', async () => {
      const segments = transcript.segments.map(item => ({
        segment_id: item.segment_id,
        text: translationText(item).trim(),
      }));
      if (segments.some(item => !item.text)) throw new Error('Перевод каждого сегмента должен быть заполнен.');
      const saved = await saveDubbingTranslation(projectId, {
        dubbing_id: transcript.dubbing_id,
        target_language: targetLanguage,
        segments,
        ...(translation ? { translation_id: translation.translation_id } : {}),
      });
      setSelectedTranslationId(saved.payload.translation.translation_id);
      setTranslationDraft({});
      await refresh();
      setNotice('Перевод сохранён и привязан к точной ревизии transcript.');
    });
  };

  const handleAudioUpload = (file: File | null) => {
    if (!file) return;
    void run('upload', async () => {
      const uploaded = await uploadPreparedAudio(projectId, file, 'imported');
      setSelectedAudioId(uploaded.id);
      await refresh();
      await onProjectChanged?.();
      setNotice('Речевая дорожка импортирована и проверена FFprobe.');
    });
  };

  const handleAttach = () => {
    if (!transcript || !audio) return;
    void run('attach', async () => {
      const chosenTranslation = useTranslation ? translation : null;
      if (useTranslation && !chosenTranslation) {
        throw new Error('Сначала сохраните перевод либо отключите использование перевода для этой дорожки.');
      }
      const result = await attachPreparedSpeech(projectId, {
        dubbing_id: transcript.dubbing_id,
        audio_id: audio.id,
        ...(chosenTranslation ? { translation_id: chosenTranslation.translation_id } : {}),
        ...(segmentId ? { segment_id: segmentId } : {}),
      });
      setSelectedTakeId(result.payload.prepared_speech.take_id);
      setReviewContent(false);
      setReviewSync(false);
      await refresh();
      setNotice('Голосовая дорожка привязана к точной версии текста и выбранному диапазону.');
    });
  };

  const handleReview = (verdict: 'approved' | 'needs_revision' | 'rejected') => {
    if (!take) return;
    void run('review', async () => {
      const result = await reviewPreparedSpeech(projectId, {
        take_id: take.take_id,
        verdict,
        content_fidelity_confirmed: reviewContent,
        synchronization_confirmed: reviewSync,
        ...(reviewNote.trim() ? { note: reviewNote.trim() } : {}),
      });
      await refresh();
      setNotice(
        result.payload.review.verdict === 'approved'
          ? 'Review одобрен: сервер подтвердил timing/loudness и сохранил ваши проверки содержания и синхронизации.'
          : 'Review сохранён без принятия в timeline.',
      );
    });
  };

  const handleAcceptReview = () => {
    if (!currentReview || currentReview.verdict !== 'approved') return;
    void run('accept', async () => {
      await acceptDubbingReview(projectId, currentReview.review_id);
      await refresh();
      setNotice('Одобренная озвучка принята как non-destructive dubbing edit.');
    });
  };

  const handleRender = () => {
    if (!source || acceptedForSource.length === 0) return;
    void run('render', async () => {
      const rendered = await renderAcceptedDubbing(projectId, source.id);
      const artifactId = rendered.result.artifact?.id;
      if (!artifactId) throw new Error('Рендер завершился без зарегистрированного artifact ID.');
      setLatestRenderId(artifactId);
      setLatestPreviewId(null);
      try {
        const preview = await createBrowserPreview(projectId, artifactId);
        if (preview.result.artifact?.id) setLatestPreviewId(preview.result.artifact.id);
      } catch {
        setNotice('Мастер с дубляжом создан. Browser preview можно создать отдельно.');
      }
      await refresh();
      await onProjectChanged?.();
    });
  };

  const handlePreview = () => {
    if (!activeRender) return;
    void run('preview', async () => {
      const preview = await createBrowserPreview(projectId, activeRender.id);
      if (!preview.result.artifact?.id) throw new Error('Preview завершился без artifact ID.');
      setLatestPreviewId(preview.result.artifact.id);
      await refresh();
    });
  };

  if (!state) {
    return (
      <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6 text-sm text-slate-400">
        Загрузка рабочего пространства дубляжа…
      </section>
    );
  }

  return (
    <section className="mt-8 rounded-2xl border border-violet-900/60 bg-slate-950/80 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-violet-300">
            <Mic2 size={18} />
            <p className="text-xs uppercase tracking-[0.18em]">Stage 5 · Dubbing / Translation</p>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-slate-100">Дубляж в том же проекте и таймлайне</h2>
          <p className="mt-2 max-w-4xl text-xs leading-5 text-slate-500">
            Распознавание создаёт только редактируемый черновик. Transcript, перевод, голосовая дорожка, Review и Accept проходят через общий Command API; финальный мастер строится из текущих Accepted video + dubbing решений.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          disabled={busy !== null}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-slate-500 disabled:opacity-40"
        >
          {busy === 'refresh' ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Перечитать состояние
        </button>
      </div>

      {error && <Message tone="error">{error}</Message>}
      {notice && <Message tone="ok">{notice}</Message>}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <StageCard number="1" title="Источник и распознавание" icon={<AudioLines size={16} />}>
          {state.sources.length === 0 ? (
            <p className="text-xs text-slate-500">Сначала импортируйте видео в редактор выше.</p>
          ) : (
            <>
              <label className="block text-xs text-slate-500">Видео</label>
              <select
                value={source?.id ?? ''}
                onChange={event => {
                  setSelectedSourceId(event.target.value);
                  setSelectedDubbingId('');
                  setSelectedTranslationId('');
                  setSelectedTakeId('');
                  setAsrDraft(null);
                }}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              >
                {state.sources.map(item => (
                  <option key={item.id} value={item.id}>{metadataText(item.metadata.original_name) ?? item.id}</option>
                ))}
              </select>
              {source && (
                <video
                  src={projectSourceMediaUrl(projectId, source.id)}
                  controls
                  playsInline
                  preload="metadata"
                  className="mt-3 aspect-video w-full rounded-xl border border-slate-800 bg-black object-contain"
                />
              )}
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Input label="Язык" value={asrLanguage} onChange={setAsrLanguage} placeholder="auto" />
                <Input label="Начало, с" value={asrStartSec} onChange={setAsrStartSec} placeholder="всё" />
                <Input label="Конец, с" value={asrEndSec} onChange={setAsrEndSec} placeholder="всё" />
              </div>
              <button
                type="button"
                onClick={handleTranscribe}
                disabled={busy !== null || !source}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-violet-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
              >
                {busy === 'asr' ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                Распознать локально
              </button>
            </>
          )}

          {asrDraft && (
            <div className="mt-4 rounded-xl border border-violet-900/60 bg-violet-950/15 p-3">
              <p className="text-xs font-medium text-violet-200">Черновик ASR — ещё не часть проекта</p>
              <p className="mt-1 font-mono text-[10px] text-slate-600">
                {asrDraft.language} · {formatTimelineTime(asrDraft.start_us)}–{formatTimelineTime(asrDraft.end_us)}
              </p>
              <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                {asrDraft.segments.map(item => (
                  <div key={item.segment_id} className="rounded-lg border border-slate-800 bg-slate-950/70 p-2">
                    <p className="font-mono text-[10px] text-slate-600">
                      {formatTimelineTime(item.start_us)} → {formatTimelineTime(item.end_us)}
                    </p>
                    <textarea
                      value={item.text}
                      onChange={event => updateAsrText(item.segment_id, event.target.value)}
                      rows={2}
                      className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 p-2 text-xs text-slate-200"
                    />
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={handleAcceptAsr}
                disabled={busy !== null}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
              >
                {busy === 'accept-asr' ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                Принять проверенный transcript
              </button>
            </div>
          )}
        </StageCard>

        <StageCard number="2" title="Transcript и перевод" icon={<Languages size={16} />}>
          {sourceTranscripts.length === 0 ? (
            <p className="text-xs text-slate-500">После принятия ASR здесь появится канонический transcript.</p>
          ) : (
            <>
              <select
                value={transcript?.dubbing_id ?? ''}
                onChange={event => {
                  setSelectedDubbingId(event.target.value);
                  setSelectedTranslationId('');
                  setTranslationDraft({});
                  setSelectedTakeId('');
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              >
                {sourceTranscripts.map(item => (
                  <option key={item.dubbing_id} value={item.dubbing_id}>
                    {item.language} · {item.origin} · {item.segments.length} сегм.
                  </option>
                ))}
              </select>
              <div className="mt-3 flex items-end gap-2">
                <div className="flex-1">
                  <Input label="Язык перевода" value={targetLanguage} onChange={setTargetLanguage} placeholder="ru" />
                </div>
                <span className="pb-2 text-[10px] text-slate-600">Автоперевод подключается через text.translate; поля уже редактируемые.</span>
              </div>
              <div className="mt-3 max-h-80 space-y-2 overflow-y-auto pr-1">
                {transcript?.segments.map(item => (
                  <div key={item.segment_id} className="grid gap-2 rounded-lg border border-slate-800 bg-slate-950/60 p-2 sm:grid-cols-2">
                    <div>
                      <p className="font-mono text-[10px] text-slate-600">{item.segment_id}</p>
                      <p className="mt-1 text-xs leading-5 text-slate-300">{item.text}</p>
                    </div>
                    <textarea
                      value={translationText(item)}
                      onChange={event =>
                        setTranslationDraft(current => ({ ...current, [item.segment_id]: event.target.value }))
                      }
                      rows={3}
                      className="w-full rounded-md border border-slate-800 bg-slate-900 p-2 text-xs text-slate-200"
                    />
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={handleSaveTranslation}
                disabled={busy !== null || !transcript}
                className="mt-3 inline-flex items-center gap-2 rounded-lg border border-violet-700 bg-violet-950/30 px-3 py-2 text-xs text-violet-200 disabled:opacity-40"
              >
                {busy === 'translation' ? <Loader2 size={14} className="animate-spin" /> : <Languages size={14} />}
                {translation ? 'Сохранить новую ревизию перевода' : 'Сохранить перевод'}
              </button>
            </>
          )}
        </StageCard>

        <StageCard number="3" title="Подготовленная речь" icon={<FileAudio size={16} />}>
          <label className="flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-slate-700 bg-slate-900/40 px-4 py-4 text-xs text-slate-300 hover:border-violet-600">
            {busy === 'upload' ? <Loader2 size={15} className="animate-spin" /> : <FileAudio size={15} />}
            Импортировать запись / подготовленную речь
            <input
              type="file"
              accept="audio/*"
              className="hidden"
              disabled={busy !== null}
              onChange={event => handleAudioUpload(event.target.files?.[0] ?? null)}
            />
          </label>
          {state.prepared_audio.length > 0 && (
            <>
              <label className="mt-3 block text-xs text-slate-500">Аудио</label>
              <select
                value={audio?.id ?? ''}
                onChange={event => setSelectedAudioId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              >
                {state.prepared_audio.map(item => (
                  <option key={item.id} value={item.id}>{metadataText(item.metadata.original_name) ?? item.id}</option>
                ))}
              </select>
              {audio && <audio controls src={preparedAudioMediaUrl(projectId, audio.id)} className="mt-2 w-full" />}
            </>
          )}
          {transcript && (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div>
                <label className="text-xs text-slate-500">Диапазон / сегмент</label>
                <select
                  value={segmentId}
                  onChange={event => setSelectedSegmentId(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs"
                >
                  {transcript.segments.map(item => (
                    <option key={item.segment_id} value={item.segment_id}>
                      {formatTimelineTime(item.start_us)}–{formatTimelineTime(item.end_us)} · {item.text.slice(0, 36)}
                    </option>
                  ))}
                </select>
              </div>
              <label className="flex items-end gap-2 pb-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={useTranslation}
                  onChange={event => setUseTranslation(event.target.checked)}
                />
                Озвучивать текущий перевод
              </label>
            </div>
          )}
          <button
            type="button"
            onClick={handleAttach}
            disabled={busy !== null || !transcript || !audio}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-sky-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
          >
            {busy === 'attach' ? <Loader2 size={14} className="animate-spin" /> : <AudioLines size={14} />}
            Привязать к тексту и диапазону
          </button>
        </StageCard>

        <StageCard number="4" title="Review → Accept" icon={<ShieldCheck size={16} />}>
          {takes.length === 0 ? (
            <p className="text-xs text-slate-500">Сначала привяжите подготовленную речь к transcript/translation.</p>
          ) : (
            <>
              <select
                value={take?.take_id ?? ''}
                onChange={event => {
                  setSelectedTakeId(event.target.value);
                  setReviewContent(false);
                  setReviewSync(false);
                }}
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              >
                {takes.map(item => (
                  <option key={item.take_id} value={item.take_id}>
                    {item.script_kind} · {item.segment_id ?? 'весь transcript'} · {(item.duration_us / 1_000_000).toFixed(2)} с
                  </option>
                ))}
              </select>
              <div className="mt-3 space-y-2 rounded-xl border border-slate-800 bg-slate-900/40 p-3">
                <label className="flex items-start gap-2 text-xs text-slate-300">
                  <input type="checkbox" checked={reviewContent} onChange={event => setReviewContent(event.target.checked)} />
                  Содержание и произношение проверены по выбранному тексту
                </label>
                <label className="flex items-start gap-2 text-xs text-slate-300">
                  <input type="checkbox" checked={reviewSync} onChange={event => setReviewSync(event.target.checked)} />
                  Синхронизация с видео проверена человеком
                </label>
                <textarea
                  value={reviewNote}
                  onChange={event => setReviewNote(event.target.value)}
                  rows={2}
                  placeholder="Комментарий к проверке"
                  className="w-full rounded-md border border-slate-800 bg-slate-950 p-2 text-xs"
                />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => handleReview('approved')}
                  disabled={busy !== null || !take || !reviewContent || !reviewSync}
                  className="rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
                >
                  {busy === 'review' ? 'Проверка…' : 'Review: approved'}
                </button>
                <button
                  type="button"
                  onClick={() => handleReview('needs_revision')}
                  disabled={busy !== null || !take}
                  className="rounded-lg border border-amber-800 px-3 py-2 text-xs text-amber-200 disabled:opacity-40"
                >
                  Нужна доработка
                </button>
                <button
                  type="button"
                  onClick={() => handleReview('rejected')}
                  disabled={busy !== null || !take}
                  className="rounded-lg border border-red-900 px-3 py-2 text-xs text-red-300 disabled:opacity-40"
                >
                  Отклонить
                </button>
              </div>
            </>
          )}
          {currentReview && (
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className={currentReview.verdict === 'approved' ? 'text-emerald-300' : 'text-amber-300'}>
                  {currentReview.verdict}
                </span>
                <span className="font-mono text-[10px] text-slate-600">{currentReview.review_id}</span>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-400 sm:grid-cols-4">
                <span>timing: {currentReview.timing_pass ? 'pass' : 'fail'}</span>
                <span>audio: {currentReview.audio_safety_pass ? 'pass' : 'fail'}</span>
                <span>LUFS: {currentReview.loudness.integrated_lufs ?? '—'}</span>
                <span>TP: {currentReview.loudness.true_peak_dbtp ?? '—'} dBTP</span>
              </div>
              {currentReview.verdict === 'approved' &&
                !state.accepted_dubbing.some(item => item.review_id === currentReview.review_id) && (
                  <button
                    type="button"
                    onClick={handleAcceptReview}
                    disabled={busy !== null}
                    className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
                  >
                    {busy === 'accept' ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                    Принять в timeline
                  </button>
                )}
            </div>
          )}
        </StageCard>
      </div>

      <div className="mt-4 rounded-2xl border border-emerald-900/60 bg-emerald-950/10 p-4 sm:p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-emerald-400">Accepted dubbing render</p>
            <h3 className="mt-2 text-lg font-medium">Материализовать видео + принятый дубляж</h3>
            <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
              Сейчас исполнима строгая политика replace_source_audio_range. Более сложные preserve-background / duck-mix остаются fail-closed, пока не пройдут отдельную media-оценку.
            </p>
          </div>
          <button
            type="button"
            onClick={handleRender}
            disabled={busy !== null || !source || acceptedForSource.length === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 disabled:opacity-40"
          >
            {busy === 'render' ? <Loader2 size={16} className="animate-spin" /> : <MonitorPlay size={16} />}
            {renders.length ? 'Пересобрать мастер' : 'Собрать мастер'}
          </button>
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-3">
          <Stat label="Accepted dubbing" value={acceptedForSource.length} />
          <Stat label="Dubbing masters" value={renders.length} />
          <Stat label="Источник" value={source ? metadataText(source.metadata.original_name) ?? source.id : '—'} />
        </div>

        {activeRender && (
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-xs text-emerald-300">Мастер с принятой озвучкой</p>
                <p className="mt-1 font-mono text-[10px] text-slate-600">{activeRender.id}</p>
              </div>
              <div className="flex gap-2">
                {!activePreview && (
                  <button
                    type="button"
                    onClick={handlePreview}
                    disabled={busy !== null}
                    className="inline-flex items-center gap-1 rounded-lg border border-sky-800 px-3 py-2 text-xs text-sky-200 disabled:opacity-40"
                  >
                    {busy === 'preview' ? <Loader2 size={13} className="animate-spin" /> : <MonitorPlay size={13} />}
                    Preview
                  </button>
                )}
                <a
                  href={projectArtifactMediaUrl(projectId, activeRender.id)}
                  download={`${source?.id ?? 'uv'}-dubbed-master.mkv`}
                  className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200"
                >
                  <Download size={13} /> Мастер
                </a>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-3 font-mono text-[10px] text-slate-500">
              <span>{metadataText(activeRender.metadata.composition_mode) ?? 'dubbing_render'}</span>
              {metadataNumber(activeRender.metadata.actual_output_video_duration_us) !== null && (
                <span>
                  {formatTimelineTime(metadataNumber(activeRender.metadata.actual_output_video_duration_us) as number)}
                </span>
              )}
            </div>
            <div className="mt-3 overflow-hidden rounded-xl border border-slate-800 bg-black">
              {activePreview ? (
                <video
                  key={activePreview.id}
                  src={projectArtifactMediaUrl(projectId, activePreview.id)}
                  controls
                  playsInline
                  preload="metadata"
                  className="aspect-video w-full object-contain"
                />
              ) : (
                <div className="flex min-h-36 items-center justify-center px-6 text-center text-xs text-slate-500">
                  Мастер хранится как lossless MKV; browser preview создаётся отдельно из мастера.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function StageCard({
  number,
  title,
  icon,
  children,
}: {
  number: string;
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/45 p-4">
      <div className="flex items-center gap-2 text-slate-300">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-violet-950 text-[10px] text-violet-300">{number}</span>
        {icon}
        <h3 className="text-sm font-medium">{title}</h3>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block text-xs text-slate-500">
      {label}
      <input
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-2.5 py-2 text-xs text-slate-200"
      />
    </label>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p>
      <p className="mt-1.5 truncate text-sm text-slate-300">{value}</p>
    </div>
  );
}

function Message({ children, tone }: { children: React.ReactNode; tone: 'error' | 'ok' }) {
  return (
    <div className={`mt-4 rounded-xl border p-3 text-xs ${
      tone === 'error'
        ? 'border-red-900/70 bg-red-950/40 text-red-200'
        : 'border-emerald-900/60 bg-emerald-950/20 text-emerald-200'
    }`}>
      {children}
    </div>
  );
}
