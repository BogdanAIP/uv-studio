'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getEditorState } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import {
  executeSequenceCommand,
  getSequenceState,
  getSequenceTimelineContext,
  sequenceMediaUrl,
  type SequenceContinuityRule,
  type SequenceContinuityState,
  type SequenceContextMedia,
  type SequenceRecord,
  type SequenceReviewOutcome,
  type SequenceReviewVerdict,
  type SequenceShotPlan,
  type SequenceTake,
  type SequenceTakeReview,
  type SequenceTimelineContext,
} from '@/lib/sequenceContinuityApi';

interface SequenceContinuityPanelProps {
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

interface ContextState {
  key: string;
  value: SequenceTimelineContext;
}

const outcomeLabels: Record<SequenceReviewOutcome, string> = {
  pass: 'Соответствует',
  fail: 'Не соответствует',
  uncertain: 'Не уверен',
};

const verdictLabels: Record<SequenceReviewVerdict, string> = {
  approved: 'Одобрить',
  needs_revision: 'Нужна доработка',
  rejected: 'Отклонить',
};

function nextShotId(sequence: SequenceRecord): string {
  return `shot_${String(sequence.plans.length + 1).padStart(2, '0')}`;
}

function planForTake(sequence: SequenceRecord, take: SequenceTake | null): SequenceShotPlan | null {
  if (!take) return null;
  return sequence.plans.find(item => item.shot_id === take.shot_id) ?? null;
}

function currentReview(sequence: SequenceRecord, take: SequenceTake | null): SequenceTakeReview | null {
  if (!take?.current_review_id) return null;
  return sequence.reviews.find(item => item.review_id === take.current_review_id) ?? null;
}

function makeReviewDraft(key: string, plan: SequenceShotPlan | null): ReviewDraft {
  return {
    key,
    verdict: 'needs_revision',
    outcomes: Object.fromEntries(
      (plan?.review_targets ?? []).map(item => [item.target_id, 'uncertain' as SequenceReviewOutcome]),
    ),
    observation: '',
    note: '',
  };
}

export function SequenceContinuityPanel({ projectId, onProjectChanged }: SequenceContinuityPanelProps) {
  const [state, setState] = useState<SequenceContinuityState | null>(null);
  const [videos, setVideos] = useState<VideoChoice[]>([]);
  const [activeSequenceId, setActiveSequenceId] = useState('');
  const [sequenceTitle, setSequenceTitle] = useState('Связанная последовательность');
  const [shotIntent, setShotIntent] = useState('');
  const [lockRequirement, setLockRequirement] = useState('');
  const [allowedChange, setAllowedChange] = useState('');
  const [reviewCriterion, setReviewCriterion] = useState(
    'Проверить визуальную непрерывность с принятым опорным дублем.',
  );
  const [takeShotId, setTakeShotId] = useState('');
  const [takeReferenceId, setTakeReferenceId] = useState('');
  const [selectedTakeId, setSelectedTakeId] = useState('');
  const [contextState, setContextState] = useState<ContextState | null>(null);
  const [reviewDraft, setReviewDraft] = useState<ReviewDraft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [sequenceState, editorState] = await Promise.all([
      getSequenceState(projectId),
      getEditorState(projectId),
    ]);
    setState(sequenceState);
    setVideos([
      ...editorState.sources.map(reference => ({ ...reference, collection: 'source' as const })),
      ...editorState.artifacts.map(reference => ({ ...reference, collection: 'artifact' as const })),
    ]);
    setActiveSequenceId(current => {
      if (current && sequenceState.sequences.some(item => item.sequence_id === current)) return current;
      return sequenceState.sequences[0]?.sequence_id ?? '';
    });
  }, [projectId]);

  useEffect(() => {
    let active = true;
    Promise.all([getSequenceState(projectId), getEditorState(projectId)])
      .then(([sequenceState, editorState]) => {
        if (!active) return;
        setState(sequenceState);
        setVideos([
          ...editorState.sources.map(reference => ({ ...reference, collection: 'source' as const })),
          ...editorState.artifacts.map(reference => ({ ...reference, collection: 'artifact' as const })),
        ]);
        setActiveSequenceId(sequenceState.sequences[0]?.sequence_id ?? '');
      })
      .catch(reason => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Не удалось загрузить последовательность');
        }
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const sequence = useMemo(
    () => state?.sequences.find(item => item.sequence_id === activeSequenceId) ?? state?.sequences[0] ?? null,
    [activeSequenceId, state],
  );

  const effectiveTakeShotId = useMemo(() => {
    if (!sequence) return '';
    if (takeShotId && sequence.plans.some(item => item.shot_id === takeShotId)) return takeShotId;
    return sequence.plans.at(-1)?.shot_id ?? '';
  }, [sequence, takeShotId]);

  const effectiveTakeReferenceId = useMemo(() => {
    if (takeReferenceId && videos.some(item => item.id === takeReferenceId)) return takeReferenceId;
    return videos[0]?.id ?? '';
  }, [takeReferenceId, videos]);

  const effectiveSelectedTakeId = useMemo(() => {
    if (!sequence) return '';
    if (selectedTakeId && sequence.takes.some(item => item.take_id === selectedTakeId)) {
      return selectedTakeId;
    }
    return (
      sequence.takes.find(item => item.status === 'prepared')?.take_id ??
      sequence.takes.at(-1)?.take_id ??
      ''
    );
  }, [selectedTakeId, sequence]);

  const selectedTake = useMemo(
    () => sequence?.takes.find(item => item.take_id === effectiveSelectedTakeId) ?? null,
    [effectiveSelectedTakeId, sequence],
  );
  const selectedPlan = useMemo(
    () => (sequence ? planForTake(sequence, selectedTake) : null),
    [selectedTake, sequence],
  );
  const selectedReview = useMemo(
    () => (sequence ? currentReview(sequence, selectedTake) : null),
    [selectedTake, sequence],
  );
  const acceptedTakes = useMemo(
    () => sequence?.takes.filter(item => item.status === 'accepted') ?? [],
    [sequence],
  );

  const reviewKey = selectedTake && selectedPlan
    ? `${sequence?.sequence_id ?? ''}:${selectedTake.take_id}:${selectedPlan.revision_sha256}`
    : '';
  const activeReviewDraft = reviewDraft?.key === reviewKey
    ? reviewDraft
    : makeReviewDraft(reviewKey, selectedPlan);
  const contextKey = selectedTake && selectedPlan
    ? `${sequence?.sequence_id ?? ''}:${selectedTake.take_id}:${selectedPlan.revision_sha256}`
    : '';
  const context = contextState?.key === contextKey ? contextState.value : null;

  const updateReviewDraft = (update: Partial<Omit<ReviewDraft, 'key'>>) => {
    setReviewDraft(current => {
      const base = current?.key === reviewKey ? current : makeReviewDraft(reviewKey, selectedPlan);
      return { ...base, ...update, key: reviewKey };
    });
  };

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
      await refresh();
      await onProjectChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Операция последовательности не выполнена');
    } finally {
      setBusy(false);
    }
  };

  if (!state) {
    return (
      <section className="mb-6 mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <p className="text-sm text-slate-400">Загрузка режима последовательности…</p>
      </section>
    );
  }

  if (state.sequences.length === 0) {
    return (
      <section className="mb-6 mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-wider text-slate-500">Stage 6 · необязательно</p>
          <h2 className="mt-2 text-xl font-medium">Непрерывность связанных кадров</h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            Включайте этот режим только когда следующий кадр должен продолжать принятый дубль. Обычные одиночные клипы не получают дополнительного состояния или проверки.
          </p>
        </div>
        <div className="mt-5 flex max-w-xl gap-3">
          <input
            aria-label="Название последовательности"
            value={sequenceTitle}
            onChange={event => setSequenceTitle(event.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <button
            type="button"
            disabled={busy || !sequenceTitle.trim()}
            onClick={() => run(async () => {
              const result = await executeSequenceCommand<SequenceRecord>(projectId, {
                command: 'create_sequence',
                title: sequenceTitle,
              });
              setActiveSequenceId(result.payload.sequence_id);
            })}
            className="rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
          >
            Включить последовательность
          </button>
        </div>
        {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
      </section>
    );
  }

  if (!sequence) return null;

  const newShotId = nextShotId(sequence);
  const defaultAnchor = sequence.anchor_take_id ?? acceptedTakes.at(-1)?.take_id ?? null;

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-wider text-slate-500">Stage 6 · Sequence Continuity</p>
          <h2 className="mt-2 text-xl font-medium">Принятый дубль → следующий связанный кадр</h2>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            План описывает то, что должно сохраниться. Наблюдения Review описывают только то, что действительно видно в конкретном дубле. Опорой может стать только принятый дубль с неизменившимися байтами.
          </p>
        </div>
        <select
          aria-label="Последовательность"
          value={sequence.sequence_id}
          onChange={event => setActiveSequenceId(event.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        >
          {state.sequences.map(item => (
            <option key={item.sequence_id} value={item.sequence_id}>{item.title}</option>
          ))}
        </select>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <Stat label="Планы кадров" value={sequence.plans.length} />
        <Stat label="Дубли" value={sequence.takes.length} />
        <Stat label="Принятые" value={acceptedTakes.length} />
        <Stat label="Текущая опора" value={sequence.anchor_take_id ?? 'нет'} />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">1. План следующего кадра</h3>
          <p className="mt-1 text-xs text-slate-500">{newShotId} · порядок {sequence.plans.length}</p>
          <label className="mt-4 block text-xs text-slate-400">Замысел кадра</label>
          <textarea
            aria-label="Замысел связанного кадра"
            value={shotIntent}
            onChange={event => setShotIntent(event.target.value)}
            rows={3}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Например: продолжить движение вправо, перейти на более крупный план."
          />
          <label className="mt-4 block text-xs text-slate-400">Опорный принятый дубль</label>
          <select
            aria-label="Опорный принятый дубль"
            value={defaultAnchor ?? ''}
            onChange={() => undefined}
            disabled
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm disabled:text-slate-400"
          >
            <option value="">Без опоры</option>
            {acceptedTakes.map(item => (
              <option key={item.take_id} value={item.take_id}>{item.take_id} · {item.shot_id}</option>
            ))}
          </select>
          <label className="mt-4 block text-xs text-slate-400">Что зафиксировать</label>
          <input
            aria-label="Фиксированное условие непрерывности"
            value={lockRequirement}
            onChange={event => setLockRequirement(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Например: сохранить направление движения вправо."
          />
          <label className="mt-4 block text-xs text-slate-400">Что разрешено изменить</label>
          <input
            aria-label="Разрешённое изменение непрерывности"
            value={allowedChange}
            onChange={event => setAllowedChange(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
            placeholder="Например: разрешить более крупное кадрирование."
          />
          <label className="mt-4 block text-xs text-slate-400">Критерий Review</label>
          <input
            aria-label="Критерий проверки связанного кадра"
            value={reviewCriterion}
            onChange={event => setReviewCriterion(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          />
          <button
            type="button"
            disabled={busy || !shotIntent.trim() || !reviewCriterion.trim()}
            onClick={() => run(async () => {
              const locks: SequenceContinuityRule[] = lockRequirement.trim()
                ? [{ rule_id: `${newShotId}.lock`, category: 'motion', requirement: lockRequirement.trim() }]
                : [];
              const allowed: SequenceContinuityRule[] = allowedChange.trim()
                ? [{ rule_id: `${newShotId}.allow`, category: 'visual', requirement: allowedChange.trim() }]
                : [];
              await executeSequenceCommand(projectId, {
                command: 'upsert_sequence_shot',
                sequence_id: sequence.sequence_id,
                shot_id: newShotId,
                order: sequence.plans.length,
                intent: shotIntent.trim(),
                anchor_take_id: defaultAnchor,
                locks,
                allowed_changes: allowed,
                review_targets: [{
                  target_id: `${newShotId}.continuity`,
                  criterion: reviewCriterion.trim(),
                  required: true,
                }],
              });
              setShotIntent('');
              setLockRequirement('');
              setAllowedChange('');
            })}
            className="mt-5 rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
          >
            Сохранить план кадра
          </button>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">2. Зарегистрировать подготовленный дубль</h3>
          <p className="mt-1 text-xs text-slate-500">
            UV Studio привяжет точный SHA/размер выбранного видео к текущей версии плана.
          </p>
          <label className="mt-4 block text-xs text-slate-400">Кадр</label>
          <select
            aria-label="Кадр для подготовленного дубля"
            value={effectiveTakeShotId}
            onChange={event => setTakeShotId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="">Выберите кадр</option>
            {sequence.plans.map(item => (
              <option key={item.shot_id} value={item.shot_id}>{item.shot_id} · {item.intent}</option>
            ))}
          </select>
          <label className="mt-4 block text-xs text-slate-400">Видео проекта</label>
          <select
            aria-label="Видео для подготовленного дубля"
            value={effectiveTakeReferenceId}
            onChange={event => setTakeReferenceId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          >
            <option value="">Выберите видео</option>
            {videos.map(item => (
              <option key={`${item.collection}:${item.id}`} value={item.id}>{item.collection} · {item.path}</option>
            ))}
          </select>
          <button
            type="button"
            disabled={busy || !effectiveTakeShotId || !effectiveTakeReferenceId}
            onClick={() => run(async () => {
              const result = await executeSequenceCommand<SequenceTake>(projectId, {
                command: 'register_sequence_take',
                sequence_id: sequence.sequence_id,
                shot_id: effectiveTakeShotId,
                reference_id: effectiveTakeReferenceId,
              });
              setSelectedTakeId(result.payload.take_id);
            })}
            className="mt-5 rounded-lg border border-sky-700 px-4 py-2 text-sm text-sky-300 disabled:opacity-50"
          >
            Зарегистрировать дубль
          </button>

          {sequence.takes.length > 0 && (
            <>
              <label className="mt-6 block text-xs text-slate-400">Дубль для проверки</label>
              <select
                aria-label="Дубль последовательности"
                value={effectiveSelectedTakeId}
                onChange={event => setSelectedTakeId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              >
                {sequence.takes.map(item => (
                  <option key={item.take_id} value={item.take_id}>
                    {item.take_id} · {item.shot_id} · {item.status}
                  </option>
                ))}
              </select>
              <button
                type="button"
                disabled={busy || !effectiveSelectedTakeId || selectedTake?.status === 'rejected'}
                onClick={async () => {
                  if (!effectiveSelectedTakeId) return;
                  setBusy(true);
                  setError(null);
                  try {
                    const value = await getSequenceTimelineContext(
                      projectId,
                      sequence.sequence_id,
                      effectiveSelectedTakeId,
                    );
                    setContextState({ key: contextKey, value });
                  } catch (reason) {
                    setError(reason instanceof Error ? reason.message : 'Не удалось загрузить границу');
                  } finally {
                    setBusy(false);
                  }
                }}
                className="mt-3 rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 disabled:opacity-50"
              >
                Показать контекст границы
              </button>
            </>
          )}
        </div>
      </div>

      {context && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-medium">3. Bounded TimelineContext</h3>
              <p className="mt-1 text-xs text-slate-500">
                Только хвост принятой опоры и начало candidate; полный видеоскан не выполняется.
              </p>
            </div>
            <span className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-400">
              {(context.window_us / 1_000_000).toFixed(2)} с
            </span>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {context.anchor ? (
              <BoundaryMedia projectId={projectId} title="Принятая опора · хвост" media={context.anchor} />
            ) : (
              <div className="rounded-lg border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                Первый кадр последовательности не требует опоры.
              </div>
            )}
            <BoundaryMedia projectId={projectId} title="Проверяемый дубль · начало" media={context.candidate} />
          </div>
          {(context.locks.length > 0 || context.allowed_changes.length > 0) && (
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <RuleList title="Зафиксировано" items={context.locks} />
              <RuleList title="Разрешено изменить" items={context.allowed_changes} />
            </div>
          )}
        </div>
      )}

      {selectedTake && selectedPlan && (
        <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">4. Review → Accept → Re-anchor</h3>
          <p className="mt-1 text-xs text-slate-500">
            Review относится к точным байтам дубля, текущей версии плана и текущей опоре.
          </p>

          {selectedTake.status === 'prepared' && (
            <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_280px]">
              <div className="space-y-3">
                {selectedPlan.review_targets.map(target => (
                  <div key={target.target_id} className="rounded-lg border border-slate-800 p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="text-sm text-slate-200">{target.criterion}</p>
                        <p className="mt-1 text-xs text-slate-600">
                          {target.target_id}{target.required ? ' · обязательно' : ''}
                        </p>
                      </div>
                      <select
                        aria-label={`Результат ${target.target_id}`}
                        value={activeReviewDraft.outcomes[target.target_id] ?? 'uncertain'}
                        onChange={event => updateReviewDraft({
                          outcomes: {
                            ...activeReviewDraft.outcomes,
                            [target.target_id]: event.target.value as SequenceReviewOutcome,
                          },
                        })}
                        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                      >
                        {(Object.keys(outcomeLabels) as SequenceReviewOutcome[]).map(value => (
                          <option key={value} value={value}>{outcomeLabels[value]}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                ))}
                <textarea
                  aria-label="Наблюдение по принятому дублю"
                  value={activeReviewDraft.observation}
                  onChange={event => updateReviewDraft({ observation: event.target.value })}
                  rows={2}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                  placeholder="Фактическое наблюдение: поза, направление движения, свет, композиция…"
                />
                <textarea
                  aria-label="Примечание Review последовательности"
                  value={activeReviewDraft.note}
                  onChange={event => updateReviewDraft({ note: event.target.value })}
                  rows={2}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                  placeholder="Примечание к решению"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-400">Вердикт</label>
                <select
                  aria-label="Вердикт Review последовательности"
                  value={activeReviewDraft.verdict}
                  onChange={event => updateReviewDraft({
                    verdict: event.target.value as SequenceReviewVerdict,
                  })}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                >
                  {(Object.keys(verdictLabels) as SequenceReviewVerdict[]).map(value => (
                    <option key={value} value={value}>{verdictLabels[value]}</option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => run(async () => {
                    await executeSequenceCommand<SequenceTakeReview>(projectId, {
                      command: 'review_sequence_take',
                      sequence_id: sequence.sequence_id,
                      take_id: selectedTake.take_id,
                      verdict: activeReviewDraft.verdict,
                      results: selectedPlan.review_targets.map(target => ({
                        target_id: target.target_id,
                        outcome: activeReviewDraft.outcomes[target.target_id] ?? 'uncertain',
                        note: null,
                      })),
                      observations: activeReviewDraft.observation.trim() ? [{
                        observation_id: `obs_${selectedTake.take_id}`,
                        kind: 'observation',
                        category: 'visual',
                        statement: activeReviewDraft.observation.trim(),
                        confidence: 'medium',
                      }] : [],
                      note: activeReviewDraft.note.trim() || null,
                    });
                  })}
                  className="mt-3 w-full rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
                >
                  Сохранить Review
                </button>
              </div>
            </div>
          )}

          {selectedReview && (
            <div className="mt-5 rounded-lg border border-slate-800 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-200">Текущий Review: {verdictLabels[selectedReview.verdict]}</p>
                  <p className="mt-1 font-mono text-xs text-slate-600">{selectedReview.review_id}</p>
                </div>
                {selectedTake.status === 'prepared' && selectedReview.verdict === 'approved' && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => run(async () => {
                      await executeSequenceCommand<SequenceTake>(projectId, {
                        command: 'accept_sequence_take',
                        sequence_id: sequence.sequence_id,
                        review_id: selectedReview.review_id,
                      });
                    })}
                    className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
                  >
                    Accept дубль
                  </button>
                )}
              </div>
              {selectedReview.observations.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm text-slate-400">
                  {selectedReview.observations.map(item => (
                    <li key={item.observation_id}>• {item.statement}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {selectedTake.status === 'accepted' && (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-emerald-900/60 bg-emerald-950/20 p-4">
              <div>
                <p className="text-sm text-emerald-200">Дубль принят и может стать factual anchor.</p>
                <p className="mt-1 text-xs text-slate-500">
                  Текущая опора: {sequence.anchor_take_id ?? 'не назначена'}
                </p>
              </div>
              <button
                type="button"
                disabled={busy || sequence.anchor_take_id === selectedTake.take_id}
                onClick={() => run(async () => {
                  await executeSequenceCommand<SequenceRecord>(projectId, {
                    command: 'reanchor_sequence',
                    sequence_id: sequence.sequence_id,
                    take_id: selectedTake.take_id,
                  });
                })}
                className="rounded-lg border border-emerald-700 px-4 py-2 text-sm text-emerald-300 disabled:opacity-50"
              >
                Сделать опорой
              </button>
            </div>
          )}
        </div>
      )}

      {error && (
        <p className="mt-5 rounded-lg border border-red-900/60 bg-red-950/20 p-3 text-sm text-red-300">{error}</p>
      )}
    </section>
  );
}

function BoundaryMedia({ projectId, title, media }: { projectId: string; title: string; media: SequenceContextMedia }) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  return (
    <div className="rounded-lg border border-slate-800 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-200">{title}</p>
          <p className="mt-1 font-mono text-xs text-slate-600">{media.take_id} · {media.reference_path}</p>
        </div>
        <span className="rounded-full bg-slate-900 px-2 py-1 text-[11px] text-slate-500">
          {media.sha256.slice(0, 10)}
        </span>
      </div>
      <video
        ref={videoRef}
        src={sequenceMediaUrl(projectId, media)}
        controls
        preload="metadata"
        className="mt-3 aspect-video w-full rounded-lg bg-black object-contain"
      />
      <div className="mt-3 flex flex-wrap gap-2">
        {media.sample_times_us.map(time => (
          <button
            key={time}
            type="button"
            onClick={() => {
              if (!videoRef.current) return;
              videoRef.current.currentTime = time / 1_000_000;
              void videoRef.current.play().catch(() => undefined);
            }}
            className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300"
          >
            {(time / 1_000_000).toFixed(2)} с
          </button>
        ))}
      </div>
    </div>
  );
}

function RuleList({ title, items }: { title: string; items: SequenceContinuityRule[] }) {
  return (
    <div className="rounded-lg border border-slate-800 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">{title}</p>
      <ul className="mt-2 space-y-2 text-sm text-slate-300">
        {items.length === 0 ? (
          <li className="text-slate-600">Нет</li>
        ) : items.map(item => (
          <li key={item.rule_id}>
            <span className="text-slate-500">{item.category}:</span> {item.requirement}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
      <p className="text-[11px] uppercase tracking-wider text-slate-600">{label}</p>
      <p className="mt-1 truncate text-sm text-slate-200">{value}</p>
    </div>
  );
}
