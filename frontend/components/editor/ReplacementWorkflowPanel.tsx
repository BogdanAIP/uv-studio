'use client';

import { CheckCircle2, CircleAlert, FileVideo2, ListChecks, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  approveReplacementPlan,
  prepareAssetReplacementCandidate,
  projectArtifactMediaUrl,
} from '@/lib/editorApi';
import type {
  EditorState,
  RangeContinuityBrief,
  ReplacementCandidate,
  ReplacementReview,
  ReviewConfidence,
  ReviewOutcome,
  ReviewVerdict,
} from '@/lib/editorApi';
import { executeProjectWorkflowAction } from '@/lib/productWorkflowApi';
import type { ProjectReference } from '@/lib/projectsApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface ReplacementWorkflowPanelProps {
  projectId: string;
  editorState: EditorState;
  sourcePath: string;
  preferredEditId?: string | null;
  onStateChanged: () => Promise<EditorState>;
  orchestrated?: boolean;
}

type ReviewDraft = {
  outcome: ReviewOutcome;
  confidence: ReviewConfidence;
  statement: string;
};

const DEFAULT_REVIEW_DRAFT: ReviewDraft = {
  outcome: 'uncertain',
  confidence: 'medium',
  statement: '',
};

function referenceName(reference: ProjectReference): string {
  const name = reference.metadata.original_name;
  return typeof name === 'string' && name.trim() ? name : reference.id;
}

function requestedChange(brief: RangeContinuityBrief): string {
  return (
    brief.constraints.find(item => item.constraint_id === 'requested_change')?.requirement ??
    brief.constraints[0]?.requirement ??
    'Выполнить запрошенное изменение выбранного диапазона.'
  );
}

function requireDomainResult<TResult>(
  response: Awaited<ReturnType<typeof executeProjectWorkflowAction<TResult>>>,
): TResult {
  if ('result' in response) return response.result;
  throw new Error('Product Orchestrator вернул capability-ответ для domain action.');
}

function reviewVerdictLabel(verdict: ReviewVerdict): string {
  if (verdict === 'approved') return 'вариант одобрен';
  if (verdict === 'rejected') return 'вариант отклонён';
  return 'нужна доработка';
}

export function ReplacementWorkflowPanel({
  projectId,
  editorState,
  sourcePath,
  preferredEditId,
  onStateChanged,
  orchestrated = false,
}: ReplacementWorkflowPanelProps) {
  const [selectedEditId, setSelectedEditId] = useState<string | null>(null);
  const [replacementSourceId, setReplacementSourceId] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(null);
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, ReviewDraft>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const briefs = useMemo(
    () => editorState.briefs.filter(brief => brief.source_path === sourcePath),
    [editorState.briefs, sourcePath],
  );
  const fallbackBrief =
    briefs.find(brief => brief.edit_id === preferredEditId) ??
    briefs[briefs.length - 1] ??
    null;
  const brief = briefs.find(item => item.edit_id === selectedEditId) ?? fallbackBrief;

  if (!brief) {
    return (
      <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-5">
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <ListChecks size={17} className="text-slate-500" />
          Следующее действие
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Сначала выделите диапазон на timeline и опишите изменение. UV Studio сохранит технический Brief внутри проекта и предложит следующий понятный шаг.
        </p>
      </section>
    );
  }

  const plan = editorState.replacement_plans.find(item => item.edit_id === brief.edit_id) ?? null;
  const candidates = editorState.replacement_candidates.filter(
    item => item.edit_id === brief.edit_id && item.stage === 'full',
  );
  const artifactOrder = new Map(
    editorState.artifacts.map((artifact, index) => [artifact.id, index]),
  );
  const orderedCandidates = [...candidates].sort(
    (left, right) =>
      (artifactOrder.get(left.artifact_id) ?? -1) -
      (artifactOrder.get(right.artifact_id) ?? -1),
  );
  const candidate =
    orderedCandidates.find(item => item.candidate_id === selectedCandidateId) ??
    orderedCandidates[orderedCandidates.length - 1] ??
    null;
  const reviews = candidate
    ? editorState.replacement_reviews.filter(item => item.candidate_id === candidate.candidate_id)
    : [];
  const review =
    reviews.find(item => item.review_id === selectedReviewId) ??
    reviews.find(item => item.verdict === 'approved') ??
    reviews[0] ??
    null;
  const acceptedEdit = editorState.accepted_edits.find(item => item.edit_id === brief.edit_id) ?? null;
  const replacementOptions = editorState.sources.filter(item => item.path !== brief.source_path);
  const replacementSource =
    replacementOptions.find(item => item.id === replacementSourceId) ??
    replacementOptions[0] ??
    null;
  const change = requestedChange(brief);

  const draftFor = (targetId: string): ReviewDraft =>
    reviewDrafts[targetId] ?? DEFAULT_REVIEW_DRAFT;

  const setDraft = (targetId: string, patch: Partial<ReviewDraft>) => {
    setReviewDrafts(current => ({
      ...current,
      [targetId]: { ...(current[targetId] ?? DEFAULT_REVIEW_DRAFT), ...patch },
    }));
  };

  const withBusy = async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Операция не выполнена');
    } finally {
      setBusy(null);
    }
  };

  const prepareReplacement = () => withBusy('prepare', async () => {
    if (!orchestrated) throw new Error('Составная подготовка доступна только в оркестрированном режиме.');
    if (!replacementSource) throw new Error('Импортируйте отдельный видеоклип для замены.');
    const response = await executeProjectWorkflowAction<{
      plan: Record<string, unknown>;
      candidate: ReplacementCandidate;
    }>(projectId, 'prepare_replacement', {
      edit_id: brief.edit_id,
      replacement_source_id: replacementSource.id,
    });
    const result = requireDomainResult(response);
    setSelectedCandidateId(result.candidate.candidate_id);
    setSelectedReviewId(null);
    await onStateChanged();
  });

  const approvePreparedPlan = () => withBusy('plan', async () => {
    await approveReplacementPlan(projectId, {
      edit_id: brief.edit_id,
      method_class: 'prepared_asset',
      goal: change,
      required_changes: [change],
      allowed_changes: [],
      forbidden_changes: ['Не изменять исходное видео вне выбранного диапазона.'],
      audio_strategy: 'preserve_source',
    });
    setSelectedCandidateId(null);
    setSelectedReviewId(null);
    await onStateChanged();
  });

  const prepareLegacyCandidate = () => withBusy('candidate', async () => {
    if (!replacementSource) throw new Error('Импортируйте отдельный видеоклип для замены.');
    const result = await prepareAssetReplacementCandidate(
      projectId,
      brief.edit_id,
      replacementSource.path,
    );
    setSelectedCandidateId(result.candidate.candidate_id);
    setSelectedReviewId(null);
    await onStateChanged();
  });

  const allReviewStatementsPresent = brief.review_targets.every(
    target => draftFor(target.target_id).statement.trim().length > 0,
  );
  const hasFail = brief.review_targets.some(
    target => draftFor(target.target_id).outcome === 'fail',
  );
  const hasUncertain = brief.review_targets.some(
    target => draftFor(target.target_id).outcome === 'uncertain',
  );
  const requiredPass = brief.review_targets
    .filter(target => target.required)
    .every(target => draftFor(target.target_id).outcome === 'pass');

  const submitReview = (verdict: ReviewVerdict) => withBusy(`review-${verdict}`, async () => {
    if (!candidate) throw new Error('Сначала подготовьте вариант замены.');
    const observations = brief.review_targets.map((target, index) => {
      const draft = draftFor(target.target_id);
      return {
        observation_id: `obs_${index + 1}`,
        kind: 'observation' as const,
        statement: draft.statement.trim(),
        confidence: draft.confidence,
        evidence: [
          { kind: 'candidate_artifact' as const, ref_id: candidate.artifact_id },
          ...target.evidence_ids.map(refId => ({ kind: 'brief_evidence' as const, ref_id: refId })),
        ],
      };
    });
    const assessments = brief.review_targets.map((target, index) => ({
      target_id: target.target_id,
      outcome: draftFor(target.target_id).outcome,
      observation_ids: [`obs_${index + 1}`],
    }));
    const response = await executeProjectWorkflowAction<ReplacementReview>(
      projectId,
      'review_replacement',
      {
        candidate_id: candidate.candidate_id,
        verdict,
        observations,
        assessments,
      },
    );
    const created = requireDomainResult(response);
    setSelectedReviewId(created.review_id);
    await onStateChanged();
  });

  const acceptReview = (currentReview: ReplacementReview) => withBusy('accept', async () => {
    await executeProjectWorkflowAction(projectId, 'accept_replacement', {
      review_id: currentReview.review_id,
    });
    await onStateChanged();
  });

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-violet-400">Точечное изменение</p>
          <h3 className="mt-1 text-lg font-medium text-slate-100">Вариант → проверка → принять</h3>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            {orchestrated
              ? 'UV Studio сохраняет Brief, Plan, Candidate и Review внутри проекта, но показывает только действия, которые нужны для результата.'
              : 'Этот сценарий ещё не перенесён в Product Orchestrator: технический Plan и подготовка Candidate временно остаются отдельными явными шагами.'}
          </p>
        </div>
        {briefs.length > 1 && (
          <select
            aria-label="Выбрать изменение"
            value={brief.edit_id}
            onChange={event => {
              setSelectedEditId(event.target.value);
              setSelectedCandidateId(null);
              setSelectedReviewId(null);
            }}
            className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-300"
          >
            {briefs.map(item => (
              <option key={item.edit_id} value={item.edit_id}>
                {formatTimelineTime(item.start_us)} — {formatTimelineTime(item.end_us)}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-900/70 bg-red-950/40 px-4 py-3 text-xs leading-5 text-red-200">
          {error}
        </div>
      )}

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <WorkflowCard
          step="01"
          title="Подготовить вариант"
          done={Boolean(candidate)}
          description={
            orchestrated
              ? 'Выберите второй project-owned клип. Технический план и отдельный candidate создаются одним семантическим действием.'
              : 'Переходный режим сохраняет старую честную границу: сначала утвердить Plan, затем отдельно подготовить Candidate.'
          }
        >
          <p className="rounded-lg bg-slate-900/70 p-3 text-xs leading-5 text-slate-400">{change}</p>
          {replacementOptions.length > 0 ? (
            <label className="mt-3 block text-[11px] text-slate-500">
              Клип-замена
              <select
                value={replacementSource?.id ?? ''}
                onChange={event => setReplacementSourceId(event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300"
              >
                {replacementOptions.map(source => (
                  <option key={source.id} value={source.id}>{referenceName(source)}</option>
                ))}
              </select>
            </label>
          ) : (
            <div className="mt-3 rounded-lg border border-amber-900/70 bg-amber-950/30 p-3 text-[11px] leading-5 text-amber-200">
              Импортируйте второе видео. Исходник не может быть заменой самому себе.
            </div>
          )}

          {orchestrated ? (
            <button
              type="button"
              onClick={() => void prepareReplacement()}
              disabled={busy !== null || !replacementSource}
              className="mt-3 w-full rounded-lg border border-violet-700/70 bg-violet-950/40 px-3 py-2 text-xs font-medium text-violet-200 hover:border-violet-500 disabled:opacity-40"
            >
              {busy === 'prepare' ? 'Подготовка…' : candidate ? 'Подготовить новый вариант' : 'Подготовить вариант замены'}
            </button>
          ) : (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => void approvePreparedPlan()}
                disabled={busy !== null}
                className="rounded-lg border border-violet-700/70 bg-violet-950/40 px-3 py-2 text-xs font-medium text-violet-200 hover:border-violet-500 disabled:opacity-40"
              >
                {busy === 'plan' ? 'Фиксация…' : plan?.method_class === 'prepared_asset' ? 'Переутвердить Plan' : 'Утвердить Plan'}
              </button>
              <button
                type="button"
                onClick={() => void prepareLegacyCandidate()}
                disabled={busy !== null || plan?.method_class !== 'prepared_asset' || !replacementSource}
                className="rounded-lg border border-sky-700/70 bg-sky-950/40 px-3 py-2 text-xs font-medium text-sky-200 hover:border-sky-500 disabled:opacity-40"
              >
                {busy === 'candidate' ? 'Подготовка…' : 'Подготовить Candidate'}
              </button>
            </div>
          )}

          {orderedCandidates.length > 1 && (
            <label className="mt-3 block text-[11px] text-slate-500">
              Вариант
              <select
                aria-label="Выбрать вариант"
                value={candidate?.candidate_id ?? ''}
                onChange={event => {
                  setSelectedCandidateId(event.target.value);
                  setSelectedReviewId(null);
                }}
                className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300"
              >
                {orderedCandidates.map((item, index) => (
                  <option key={item.candidate_id} value={item.candidate_id}>
                    Вариант {index + 1}
                  </option>
                ))}
              </select>
            </label>
          )}
          {candidate && <CandidatePreview projectId={projectId} candidate={candidate} />}
        </WorkflowCard>

        <WorkflowCard
          step="02"
          title="Проверить результат"
          done={Boolean(review?.verdict === 'approved')}
          description="Каждый обязательный критерий проверяется по конкретному candidate artifact."
        >
          {!candidate ? (
            <p className="text-xs leading-5 text-slate-600">Сначала подготовьте вариант замены.</p>
          ) : (
            <>
              <div className="space-y-3">
                {brief.review_targets.map(target => {
                  const draft = draftFor(target.target_id);
                  return (
                    <div key={target.target_id} className="rounded-xl border border-slate-800 bg-slate-900/45 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-medium text-slate-200">{target.criterion}</p>
                          <p className="mt-1 font-mono text-[10px] text-slate-600">{target.target_id}</p>
                        </div>
                        {target.required && <span className="text-[10px] text-amber-400">обязательно</span>}
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-2">
                        <label className="text-[10px] text-slate-500">
                          Результат
                          <select
                            aria-label={`Результат ${target.target_id}`}
                            value={draft.outcome}
                            onChange={event => setDraft(target.target_id, { outcome: event.target.value as ReviewOutcome })}
                            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-300"
                          >
                            <option value="uncertain">нужно проверить</option>
                            <option value="pass">соответствует</option>
                            <option value="fail">не соответствует</option>
                          </select>
                        </label>
                        <label className="text-[10px] text-slate-500">
                          Уверенность
                          <select
                            value={draft.confidence}
                            onChange={event => setDraft(target.target_id, { confidence: event.target.value as ReviewConfidence })}
                            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-300"
                          >
                            <option value="low">низкая</option>
                            <option value="medium">средняя</option>
                            <option value="high">высокая</option>
                          </select>
                        </label>
                      </div>
                      <textarea
                        aria-label={`Наблюдение ${target.target_id}`}
                        value={draft.statement}
                        onChange={event => setDraft(target.target_id, { statement: event.target.value })}
                        rows={2}
                        placeholder="Что видно в подготовленном варианте?"
                        className="mt-2 w-full resize-y rounded-lg border border-slate-700 bg-slate-950 px-2.5 py-2 text-xs leading-5 text-slate-300 outline-none focus:border-sky-600"
                      />
                    </div>
                  );
                })}
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <button
                  type="button"
                  onClick={() => void submitReview('rejected')}
                  disabled={busy !== null || !allReviewStatementsPresent || !hasFail}
                  className="rounded-lg border border-red-900 bg-red-950/30 px-3 py-2 text-xs text-red-200 disabled:opacity-40"
                >
                  Отклонить вариант
                </button>
                <button
                  type="button"
                  onClick={() => void submitReview('needs_revision')}
                  disabled={busy !== null || !allReviewStatementsPresent || !(hasFail || hasUncertain)}
                  className="rounded-lg border border-amber-800 bg-amber-950/30 px-3 py-2 text-xs text-amber-200 disabled:opacity-40"
                >
                  Нужна доработка
                </button>
                <button
                  type="button"
                  onClick={() => void submitReview('approved')}
                  disabled={busy !== null || !allReviewStatementsPresent || hasFail || hasUncertain || !requiredPass}
                  className="rounded-lg border border-emerald-800 bg-emerald-950/30 px-3 py-2 text-xs text-emerald-200 disabled:opacity-40"
                >
                  {busy === 'review-approved' ? 'Сохранение…' : 'Одобрить вариант'}
                </button>
              </div>
              {reviews.length > 1 && (
                <label className="mt-3 block text-[11px] text-slate-500">
                  Проверка
                  <select
                    aria-label="Выбрать проверку"
                    value={review?.review_id ?? ''}
                    onChange={event => setSelectedReviewId(event.target.value)}
                    className="mt-1.5 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300"
                  >
                    {reviews.map((item, index) => (
                      <option key={item.review_id} value={item.review_id}>
                        Проверка {index + 1} · {reviewVerdictLabel(item.verdict)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {review && (
                <p className={`mt-3 text-xs ${
                  review.verdict === 'approved'
                    ? 'text-emerald-400'
                    : review.verdict === 'rejected'
                      ? 'text-red-400'
                      : 'text-amber-400'
                }`}>
                  Проверка: {reviewVerdictLabel(review.verdict)}
                </p>
              )}
            </>
          )}
        </WorkflowCard>

        <WorkflowCard
          step="03"
          title="Принять в проект"
          done={Boolean(acceptedEdit)}
          description="Только одобренный Review становится non-destructive правкой. Финальная сборка остаётся отдельным действием."
        >
          {acceptedEdit ? (
            <div className="rounded-xl border border-emerald-900/70 bg-emerald-950/25 p-3 text-xs leading-5 text-emerald-200">
              <div className="flex items-center gap-2 font-medium"><ShieldCheck size={15} /> Правка принята через D-032</div>
              <p className="mt-2 font-mono text-[10px] text-emerald-500">{acceptedEdit.edit_id}</p>
            </div>
          ) : review?.verdict === 'approved' ? (
            <button
              type="button"
              onClick={() => void acceptReview(review)}
              disabled={busy !== null}
              className="w-full rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 hover:bg-emerald-300 disabled:opacity-40"
            >
              {busy === 'accept' ? 'Принятие…' : 'Принять в timeline'}
            </button>
          ) : (
            <p className="text-xs leading-5 text-slate-600">Одобрите проверенный вариант, чтобы открыть принятие.</p>
          )}
        </WorkflowCard>
      </div>
    </section>
  );
}

function CandidatePreview({ projectId, candidate }: { projectId: string; candidate: ReplacementCandidate }) {
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-800 bg-black">
      <video
        src={projectArtifactMediaUrl(projectId, candidate.artifact_id)}
        controls
        playsInline
        preload="metadata"
        className="aspect-video w-full object-contain"
      />
      <div className="flex items-center gap-2 border-t border-slate-800 bg-slate-950 px-3 py-2 font-mono text-[10px] text-slate-600">
        <FileVideo2 size={12} /> {candidate.candidate_id}
      </div>
    </div>
  );
}

function WorkflowCard({
  step,
  title,
  done,
  description,
  children,
}: {
  step: string;
  title: string;
  done: boolean;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/35 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex gap-3">
          <span className="font-mono text-[10px] text-slate-600">{step}</span>
          <div>
            <h4 className="text-sm font-medium text-slate-200">{title}</h4>
            <p className="mt-1 text-[11px] leading-5 text-slate-500">{description}</p>
          </div>
        </div>
        {done ? <CheckCircle2 size={17} className="shrink-0 text-emerald-400" /> : <CircleAlert size={17} className="shrink-0 text-slate-700" />}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}
