'use client';

import { CheckCircle2, Link2, Loader2, Play, RefreshCw, ShieldCheck } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getEditorState } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  executeSequenceCommand,
  getSequenceState,
  getSequenceTimelineContext,
  sequenceMediaUrl,
  type SequenceContextMedia,
  type SequenceContinuityRule,
  type SequenceContinuityState,
  type SequenceRecord,
  type SequenceReviewOutcome,
  type SequenceReviewVerdict,
  type SequenceShotPlan,
  type SequenceTake,
  type SequenceTakeReview,
  type SequenceTimelineContext,
} from '@/lib/sequenceContinuityApi';

interface SequenceContinuityWorkspaceProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

interface VideoChoice extends ProjectReference {
  collection: 'source' | 'artifact';
}

interface ReviewDraft {
  key: string;
  verdict: SequenceReviewVerdict;
  outcomes: Record<string, SequenceReviewOutcome>;
  observation: string;
  note: string;
}

const outcomeLabels: Record<SequenceReviewOutcome, string> = {
  pass: 'Соответствует',
  uncertain: 'Не уверен',
  fail: 'Не соответствует',
};

const verdictLabels: Record<SequenceReviewVerdict, string> = {
  approved: 'Одобрить',
  needs_revision: 'На доработку',
  rejected: 'Отклонить',
};

function nextShotId(sequence: SequenceRecord): string {
  return `shot_${String(sequence.plans.length + 1).padStart(2, '0')}`;
}

function videoLabel(reference: ProjectReference): string {
  const originalName = reference.metadata.original_name;
  return typeof originalName === 'string' && originalName.trim() ? originalName : reference.path.split('/').at(-1) ?? 'Видео';
}

function makeDraft(key: string, plan: SequenceShotPlan | null): ReviewDraft {
  return {
    key,
    verdict: 'needs_revision',
    outcomes: Object.fromEntries((plan?.review_targets ?? []).map(target => [target.target_id, 'uncertain' as SequenceReviewOutcome])),
    observation: '',
    note: '',
  };
}

export function SequenceContinuityWorkspace({ projectId, onProjectChanged }: SequenceContinuityWorkspaceProps) {
  const [state, setState] = useState<SequenceContinuityState | null>(null);
  const [videos, setVideos] = useState<VideoChoice[]>([]);
  const [activeSequenceId, setActiveSequenceId] = useState('');
  const [sequenceTitle, setSequenceTitle] = useState('Связанная сцена');
  const [shotIntent, setShotIntent] = useState('');
  const [lockRequirement, setLockRequirement] = useState('');
  const [allowedChange, setAllowedChange] = useState('');
  const [reviewCriterion, setReviewCriterion] = useState('Проверить визуальную непрерывность с предыдущим принятым кадром.');
  const [takeShotId, setTakeShotId] = useState('');
  const [takeReferenceId, setTakeReferenceId] = useState('');
  const [selectedTakeId, setSelectedTakeId] = useState('');
  const [context, setContext] = useState<{ key: string; value: SequenceTimelineContext } | null>(null);
  const [reviewDraft, setReviewDraft] = useState<ReviewDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [sequenceState, editorState] = await Promise.all([getSequenceState(projectId), getEditorState(projectId)]);
    setState(sequenceState);
    setVideos([
      ...editorState.sources.filter(item => item.kind === 'video').map(item => ({ ...item, collection: 'source' as const })),
      ...editorState.artifacts.filter(item => item.kind === 'video').map(item => ({ ...item, collection: 'artifact' as const })),
    ]);
    setActiveSequenceId(current => current && sequenceState.sequences.some(item => item.sequence_id === current) ? current : sequenceState.sequences[0]?.sequence_id ?? '');
    return sequenceState;
  }, [projectId]);

  useEffect(() => {
    let active = true;
    Promise.all([getSequenceState(projectId), getEditorState(projectId)])
      .then(([sequenceState, editorState]) => {
        if (!active) return;
        setState(sequenceState);
        setVideos([
          ...editorState.sources.filter(item => item.kind === 'video').map(item => ({ ...item, collection: 'source' as const })),
          ...editorState.artifacts.filter(item => item.kind === 'video').map(item => ({ ...item, collection: 'artifact' as const })),
        ]);
        setActiveSequenceId(sequenceState.sequences[0]?.sequence_id ?? '');
      })
      .catch(reason => {
        if (active) setError(reason instanceof Error ? reason.message : 'Не удалось загрузить связность сцен');
      });
    return () => { active = false; };
  }, [projectId]);

  const sequence = useMemo(
    () => state?.sequences.find(item => item.sequence_id === activeSequenceId) ?? state?.sequences[0] ?? null,
    [activeSequenceId, state],
  );
  const acceptedTakes = useMemo(() => sequence?.takes.filter(item => item.status === 'accepted') ?? [], [sequence]);
  const effectiveShotId = useMemo(() => {
    if (!sequence) return '';
    return takeShotId && sequence.plans.some(item => item.shot_id === takeShotId) ? takeShotId : sequence.plans.at(-1)?.shot_id ?? '';
  }, [sequence, takeShotId]);
  const effectiveVideoId = useMemo(() => {
    return takeReferenceId && videos.some(item => item.id === takeReferenceId) ? takeReferenceId : videos[0]?.id ?? '';
  }, [takeReferenceId, videos]);
  const effectiveTakeId = useMemo(() => {
    if (!sequence) return '';
    if (selectedTakeId && sequence.takes.some(item => item.take_id === selectedTakeId)) return selectedTakeId;
    return sequence.takes.find(item => item.status === 'prepared')?.take_id ?? sequence.takes.at(-1)?.take_id ?? '';
  }, [selectedTakeId, sequence]);
  const selectedTake = sequence?.takes.find(item => item.take_id === effectiveTakeId) ?? null;
  const selectedPlan = selectedTake ? sequence?.plans.find(item => item.shot_id === selectedTake.shot_id) ?? null : null;
  const selectedReview = selectedTake?.current_review_id ? sequence?.reviews.find(item => item.review_id === selectedTake.current_review_id) ?? null : null;
  const reviewKey = selectedTake && selectedPlan ? `${selectedTake.take_id}:${selectedPlan.revision_sha256}` : '';
  const activeDraft = reviewDraft?.key === reviewKey ? reviewDraft : makeDraft(reviewKey, selectedPlan);
  const activeContext = context?.key === reviewKey ? context.value : null;

  const updateDraft = (patch: Partial<Omit<ReviewDraft, 'key'>>) => {
    setReviewDraft(current => ({ ...(current?.key === reviewKey ? current : makeDraft(reviewKey, selectedPlan)), ...patch, key: reviewKey }));
  };

  const run = async (operation: () => Promise<void>, success?: string) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await operation();
      await refresh();
      await onProjectChanged?.();
      if (success) setNotice(success);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Операция не выполнена');
    } finally {
      setBusy(false);
    }
  };

  if (!state) {
    return <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6 text-sm text-zinc-600">Загрузка связности сцен…</section>;
  }

  if (state.sequences.length === 0) {
    return (
      <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-6">
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><Link2 size={18} /></span>
          <div>
            <h2 className="text-lg font-medium text-zinc-100">Связность сцен</h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-zinc-600">Включайте этот инструмент, когда следующий кадр должен продолжать внешний вид, движение или другие факты предыдущего принятого кадра.</p>
          </div>
        </div>
        <div className="mt-5 flex max-w-xl gap-2">
          <input aria-label="Название последовательности" value={sequenceTitle} onChange={event => setSequenceTitle(event.target.value)} className="min-w-0 flex-1 rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300" />
          <button type="button" disabled={busy || !sequenceTitle.trim()} onClick={() => void run(async () => {
            const result = await executeSequenceCommand<SequenceRecord>(projectId, { command: 'create_sequence', title: sequenceTitle.trim() });
            setActiveSequenceId(result.payload.sequence_id);
          }, 'Связанная сцена создана.')} className="rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-600">Включить</button>
        </div>
        {error && <Message tone="error">{error}</Message>}
      </section>
    );
  }

  if (!sequence) return null;
  const newShotId = nextShotId(sequence);
  const defaultAnchor = sequence.anchor_take_id ?? acceptedTakes.at(-1)?.take_id ?? null;

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-600">Связанные кадры</p>
          <h2 className="mt-2 text-xl font-medium text-zinc-100">{sequence.title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Следующий вариант сравнивается с последним принятым опорным кадром. Факты предыдущего кадра используются только после вашей проверки и применения.</p>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border)] px-3 text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-40"><RefreshCw size={13} /> Обновить</button>
      </div>

      {state.sequences.length > 1 && (
        <label className="mt-4 block max-w-sm text-xs text-zinc-600">Связанная сцена<select value={sequence.sequence_id} onChange={event => setActiveSequenceId(event.target.value)} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300">{state.sequences.map(item => <option key={item.sequence_id} value={item.sequence_id}>{item.title}</option>)}</select></label>
      )}

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Stat label="Запланировано кадров" value={sequence.plans.length} />
        <Stat label="Принято вариантов" value={acceptedTakes.length} />
        <Stat label="Опорный кадр" value={sequence.anchor_take_id ? 'Выбран' : 'Пока нет'} tone={sequence.anchor_take_id ? 'ok' : undefined} />
      </div>

      {notice && <Message tone="ok">{notice}</Message>}
      {error && <Message tone="error">{error}</Message>}

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <Card step="1" title="Следующий кадр" description="Опишите намерение кадра и что должно остаться неизменным относительно принятой опоры.">
          <Field label="Что происходит в следующем кадре"><textarea aria-label="Замысел связанного кадра" value={shotIntent} onChange={event => setShotIntent(event.target.value)} rows={3} className="field" placeholder="Например: персонаж продолжает движение вправо…" /></Field>
          <Field label="Что обязательно сохранить"><input aria-label="Фиксированное условие непрерывности" value={lockRequirement} onChange={event => setLockRequirement(event.target.value)} className="field" placeholder="Идентичность, направление движения, одежда…" /></Field>
          <Field label="Что можно изменить"><input aria-label="Разрешённое изменение непрерывности" value={allowedChange} onChange={event => setAllowedChange(event.target.value)} className="field" placeholder="Например: более крупный план" /></Field>
          <Field label="Как проверить результат"><input aria-label="Критерий проверки связанного кадра" value={reviewCriterion} onChange={event => setReviewCriterion(event.target.value)} className="field" /></Field>
          <button type="button" disabled={busy || !shotIntent.trim() || !reviewCriterion.trim()} onClick={() => void run(async () => {
            const locks: SequenceContinuityRule[] = lockRequirement.trim() ? [{ rule_id: `${newShotId}.lock`, category: 'motion', requirement: lockRequirement.trim() }] : [];
            const allowed: SequenceContinuityRule[] = allowedChange.trim() ? [{ rule_id: `${newShotId}.allow`, category: 'visual', requirement: allowedChange.trim() }] : [];
            await executeSequenceCommand(projectId, {
              command: 'upsert_sequence_shot', sequence_id: sequence.sequence_id, shot_id: newShotId,
              order: sequence.plans.length, intent: shotIntent.trim(), anchor_take_id: defaultAnchor,
              locks, allowed_changes: allowed,
              review_targets: [{ target_id: `${newShotId}.continuity`, criterion: reviewCriterion.trim(), required: true }],
            });
            setShotIntent(''); setLockRequirement(''); setAllowedChange('');
          }, 'План следующего кадра сохранён.')} className="primary">Сохранить кадр</button>
        </Card>

        <Card step="2" title="Вариант" description="Выберите видео проекта, которое хотите проверить как следующий связанный кадр.">
          {sequence.plans.length === 0 ? <Hint>Сначала сохраните план следующего кадра.</Hint> : videos.length === 0 ? <Hint>Добавьте видео в проект.</Hint> : (
            <>
              {sequence.plans.length > 1 && <Field label="Кадр"><select aria-label="Кадр для подготовленного дубля" value={effectiveShotId} onChange={event => setTakeShotId(event.target.value)} className="field">{sequence.plans.map((plan, index) => <option key={plan.shot_id} value={plan.shot_id}>Кадр {index + 1} · {plan.intent}</option>)}</select></Field>}
              <Field label="Видео"><select aria-label="Видео для подготовленного дубля" value={effectiveVideoId} onChange={event => setTakeReferenceId(event.target.value)} className="field">{videos.map(video => <option key={`${video.collection}:${video.id}`} value={video.id}>{videoLabel(video)}</option>)}</select></Field>
              <button type="button" disabled={busy || !effectiveShotId || !effectiveVideoId} onClick={() => void run(async () => {
                const result = await executeSequenceCommand<SequenceTake>(projectId, { command: 'register_sequence_take', sequence_id: sequence.sequence_id, shot_id: effectiveShotId, reference_id: effectiveVideoId });
                setSelectedTakeId(result.payload.take_id); setContext(null); setReviewDraft(null);
              }, 'Вариант добавлен для проверки.')} className="secondary">Проверить этот вариант</button>
            </>
          )}
          {sequence.takes.length > 1 && <Field label="Подготовленный вариант"><select aria-label="Дубль последовательности" value={effectiveTakeId} onChange={event => { setSelectedTakeId(event.target.value); setContext(null); setReviewDraft(null); }} className="field">{sequence.takes.map((take, index) => <option key={take.take_id} value={take.take_id}>Вариант {index + 1} · {take.status === 'accepted' ? 'применён' : take.status === 'rejected' ? 'отклонён' : 'на проверке'}</option>)}</select></Field>}
          {selectedTake && selectedTake.status !== 'rejected' && <button type="button" disabled={busy} onClick={async () => {
            setBusy(true); setError(null);
            try {
              const value = await getSequenceTimelineContext(projectId, sequence.sequence_id, selectedTake.take_id);
              setContext({ key: reviewKey, value });
            } catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось подготовить сравнение.'); }
            finally { setBusy(false); }
          }} className="secondary"><Play size={13} /> Сравнить границу</button>}
        </Card>
      </div>

      {activeContext && (
        <Card step="3" title="Сравнение границы" description="Посмотрите конец принятой опоры рядом с началом нового варианта. Полное видео не дублируется и не пересобирается для этой проверки." full>
          <div className="grid gap-4 lg:grid-cols-2">
            {activeContext.anchor ? <BoundaryMedia projectId={projectId} title="Принятый опорный кадр" media={activeContext.anchor} /> : <div className="flex min-h-44 items-center justify-center rounded-xl border border-dashed border-[var(--uv-border)] p-4 text-center text-sm text-zinc-700">Это первый кадр последовательности — предыдущая опора не требуется.</div>}
            <BoundaryMedia projectId={projectId} title="Новый вариант" media={activeContext.candidate} />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2"><RuleList title="Должно сохраниться" items={activeContext.locks} /><RuleList title="Можно изменить" items={activeContext.allowed_changes} /></div>
        </Card>
      )}

      {selectedTake && selectedPlan && (
        <Card step="4" title="Проверка" description="Отметьте соответствие критериям и примените вариант только после явного одобрения." full>
          {selectedTake.status === 'prepared' && (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_260px]">
              <div className="space-y-3">
                {selectedPlan.review_targets.map((target, index) => (
                  <div key={target.target_id} className="rounded-xl border border-[var(--uv-border)] bg-black/10 p-3">
                    <p className="text-sm text-zinc-300">{target.criterion}</p>
                    <select aria-label={`Результат критерия ${index + 1}`} value={activeDraft.outcomes[target.target_id] ?? 'uncertain'} onChange={event => updateDraft({ outcomes: { ...activeDraft.outcomes, [target.target_id]: event.target.value as SequenceReviewOutcome } })} className="mt-2 field">{(Object.keys(outcomeLabels) as SequenceReviewOutcome[]).map(value => <option key={value} value={value}>{outcomeLabels[value]}</option>)}</select>
                  </div>
                ))}
                <Field label="Что вы заметили"><textarea aria-label="Наблюдение по связанному кадру" value={activeDraft.observation} onChange={event => updateDraft({ observation: event.target.value })} rows={2} className="field" placeholder="Коротко опишите фактический результат…" /></Field>
                <Field label="Примечание (необязательно)"><textarea aria-label="Примечание проверки связанного кадра" value={activeDraft.note} onChange={event => updateDraft({ note: event.target.value })} rows={2} className="field" /></Field>
              </div>
              <div>
                <Field label="Решение"><select aria-label="Решение по связанному кадру" value={activeDraft.verdict} onChange={event => updateDraft({ verdict: event.target.value as SequenceReviewVerdict })} className="field">{(Object.keys(verdictLabels) as SequenceReviewVerdict[]).map(value => <option key={value} value={value}>{verdictLabels[value]}</option>)}</select></Field>
                <button type="button" disabled={busy} onClick={() => void run(async () => {
                  await executeSequenceCommand<SequenceTakeReview>(projectId, {
                    command: 'review_sequence_take', sequence_id: sequence.sequence_id, take_id: selectedTake.take_id, verdict: activeDraft.verdict,
                    results: selectedPlan.review_targets.map(target => ({ target_id: target.target_id, outcome: activeDraft.outcomes[target.target_id] ?? 'uncertain', note: null })),
                    observations: activeDraft.observation.trim() ? [{ observation_id: `obs_${selectedTake.take_id}`, kind: 'observation', category: 'visual', statement: activeDraft.observation.trim(), confidence: 'medium' }] : [],
                    note: activeDraft.note.trim() || null,
                  });
                }, 'Проверка сохранена.')} className="primary w-full">Сохранить проверку</button>
              </div>
            </div>
          )}

          {selectedReview && <ReviewSummary review={selectedReview} />}

          {selectedTake.status === 'prepared' && selectedReview?.verdict === 'approved' && (
            <button type="button" disabled={busy} onClick={() => void run(async () => {
              await executeSequenceCommand<SequenceTake>(projectId, { command: 'accept_sequence_take', sequence_id: sequence.sequence_id, review_id: selectedReview.review_id });
            }, 'Вариант применён. Теперь его можно сделать новой опорой.')} className="mt-3 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-zinc-950"><CheckCircle2 size={15} /> Применить вариант</button>
          )}

          {selectedTake.status === 'accepted' && (
            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-4">
              <div className="flex items-start gap-2 text-sm text-emerald-200"><CheckCircle2 size={16} className="mt-0.5" /><span>Вариант применён. Он может стать опорой для следующего кадра.</span></div>
              <button type="button" disabled={busy || sequence.anchor_take_id === selectedTake.take_id} onClick={() => void run(async () => {
                await executeSequenceCommand<SequenceRecord>(projectId, { command: 'reanchor_sequence', sequence_id: sequence.sequence_id, take_id: selectedTake.take_id });
              }, 'Опорный кадр обновлён.')} className="inline-flex items-center gap-2 rounded-lg border border-emerald-400/25 px-3 py-2 text-xs text-emerald-200 disabled:opacity-40"><ShieldCheck size={14} /> {sequence.anchor_take_id === selectedTake.take_id ? 'Текущая опора' : 'Сделать опорой'}</button>
            </div>
          )}
        </Card>
      )}

      <style jsx global>{`
        .field { width: 100%; border: 1px solid var(--uv-border); border-radius: 10px; background: rgba(0,0,0,.18); padding: 9px 11px; color: #d4d4d8; font-size: 12px; }
        .field:focus { border-color: rgba(139,124,246,.55); }
        .primary { border-radius: 10px; background: var(--uv-accent); padding: 9px 13px; color: #090a0d; font-size: 12px; font-weight: 650; }
        .primary:disabled { cursor: not-allowed; background: #27272a; color: #52525b; }
        .secondary { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--uv-border-strong); border-radius: 10px; background: var(--uv-surface-1); padding: 9px 13px; color: #d4d4d8; font-size: 12px; }
        .secondary:disabled { cursor: not-allowed; opacity: .35; }
      `}</style>
    </section>
  );
}

function Card({ step, title, description, children, full = false }: { step: string; title: string; description: string; children: React.ReactNode; full?: boolean }) {
  return <div className={`rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 ${full ? 'mt-4' : ''}`}><div className="flex items-start gap-3"><span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-400/10 text-xs font-medium text-violet-300">{step}</span><div><h3 className="text-sm font-medium text-zinc-200">{title}</h3><p className="mt-1 text-xs leading-5 text-zinc-700">{description}</p></div></div><div className="mt-4 space-y-3">{children}</div></div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-[11px] text-zinc-600"><span className="mb-1.5 block">{label}</span>{children}</label>;
}

function Hint({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-[var(--uv-border)] p-4 text-xs leading-5 text-zinc-700">{children}</div>;
}

function Message({ tone, children }: { tone: 'ok' | 'error'; children: React.ReactNode }) {
  return <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${tone === 'ok' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}>{children}</div>;
}

function Stat({ label, value, tone }: { label: string; value: string | number; tone?: 'ok' }) {
  return <div className="rounded-xl border border-[var(--uv-border)] bg-black/10 p-3"><p className="text-[10px] uppercase tracking-[0.12em] text-zinc-700">{label}</p><p className={`mt-1.5 text-sm font-medium ${tone === 'ok' ? 'text-emerald-300' : 'text-zinc-300'}`}>{value}</p></div>;
}

function BoundaryMedia({ projectId, title, media }: { projectId: string; title: string; media: SequenceContextMedia }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  return <div className="rounded-xl border border-[var(--uv-border)] bg-black/20 p-3"><p className="text-xs font-medium text-zinc-300">{title}</p><video ref={videoRef} src={sequenceMediaUrl(projectId, media)} controls preload="metadata" className="mt-3 aspect-video w-full rounded-lg bg-black object-contain" /><div className="mt-2 flex flex-wrap gap-1.5">{media.sample_times_us.map((time, index) => <button key={time} type="button" onClick={() => { if (videoRef.current) videoRef.current.currentTime = time / 1_000_000; }} className="rounded-md border border-[var(--uv-border)] px-2 py-1 text-[10px] text-zinc-600 hover:text-zinc-300">Точка {index + 1}</button>)}</div>{(media.observations?.length ?? 0) > 0 && <div className="mt-3 rounded-lg bg-white/[0.025] p-3 text-xs leading-5 text-zinc-600">{media.observations?.map(item => <p key={item.observation_id}>{item.statement}</p>)}</div>}</div>;
}

function RuleList({ title, items }: { title: string; items: SequenceContinuityRule[] }) {
  return <div className="rounded-xl border border-[var(--uv-border)] bg-black/10 p-3"><p className="text-[11px] font-medium text-zinc-500">{title}</p>{items.length ? <ul className="mt-2 space-y-1.5 text-xs leading-5 text-zinc-600">{items.map(item => <li key={item.rule_id}>• {item.requirement}</li>)}</ul> : <p className="mt-2 text-xs text-zinc-700">Нет дополнительных условий.</p>}</div>;
}

function ReviewSummary({ review }: { review: SequenceTakeReview }) {
  const text = review.verdict === 'approved' ? 'Вариант одобрен' : review.verdict === 'needs_revision' ? 'Нужна доработка' : 'Вариант отклонён';
  const tone = review.verdict === 'approved' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : review.verdict === 'needs_revision' ? 'border-amber-400/20 bg-amber-400/[0.06] text-amber-100' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200';
  return <div className={`rounded-xl border p-3 text-sm ${tone}`}>{text}{review.observations.length > 0 && <p className="mt-1 text-xs opacity-75">{review.observations[0].statement}</p>}</div>;
}
