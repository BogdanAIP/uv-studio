'use client';

import { CheckCircle2, CircleAlert, FileVideo2, ListChecks, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  acceptReplacementReview,
  approveReplacementPlan,
  createReplacementReview,
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
import type { ProjectReference } from '@/lib/projectsApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface ReplacementWorkflowPanelProps {
  projectId: string;
  editorState: EditorState;
  sourcePath: string;
  preferredEditId?: string | null;
  onStateChanged: () => Promise<EditorState>;
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

export function ReplacementWorkflowPanel({
  projectId,
  editorState,
  sourcePath,
  preferredEditId,
  onStateChanged,
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
          Plan → Candidate → Review → Accept
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">
          Сначала выделите диапазон на timeline и сохраните задачу изменения. После этого здесь продолжится тот же edit_id без ручных API-вызовов.
        </p>
      </section>
    );
  }

  const plan = editorState.replacement_plans.find(item => item.edit_id === brief.edit_id) ?? null;
  const candidates = editorState.replacement_candidates.filter(
    item => item.edit_id === brief.edit_id && item.stage === 'full',
  );
  const candidate =
    candidates.find(item => item.candidate_id === selectedCandidateId) ??
    candidates[candidates.length - 1] ??
    null;
  const reviews = candidate
    ? editorState.replacement_reviews.filter(item => item.candidate_id === candidate.candidate_id)
    : [];
  const review =
    reviews.find(item => item.review_id === selectedReviewId) ??
    reviews[reviews.length - 1] ??
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

  const prepareCandidate = () => withBusy('candidate', async () => {
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
    if (!candidate) throw new Error('Сначала подготовьте full candidate.');
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
    const created = await createReplacementReview(projectId, {
      candidate_id: candidate.candidate_id,
      verdict,
      observations,
      assessments,
    });
    setSelectedReviewId(created.review_id);
    await onStateChanged();
  });

  const acceptReview = (currentReview: ReplacementReview) => withBusy('accept', async () => {
    await acceptReplacementReview(projectId, currentReview.review_id);
    await onStateChanged();
  });

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-violet-400">Replacement workflow</p>
          <h3 className="mt-1 text-lg font-medium text-slate-100">Brief → Plan → Candidate → Review → Accept</h3>
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
                {formatTimelineTime(item.start_us)} — {formatTimelineTime(item.end_us)} · {item.edit_id}
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
          title="Plan"
          done={Boolean(plan)}
          description="Метод и границы изменения утверждаются до подготовки replacement."
        >
          <p className="rounded-lg bg-slate-900/70 p-3 text-xs leading-5 text-slate-400">{change}</p>
          {plan ? (
            <div className="mt-3 text-xs leading-5 text-slate-400">
              <p><span className="text-slate-600">Метод:</span> {plan.method_class}</p>
              <p><span className="text-slate-600">Аудио:</span> {plan.audio_strategy}</p>
              <p className="mt-2 text-emerald-400">План привязан к текущей ревизии Brief.</p>
            </div>
          ) : (
            <p className="mt-3 text-[11px] leading-5 text-slate-500">
              Полностью рабочий локальный маршрут использует уже импортированный клип-замену. Генеративные методы остаются за Capability/D-017 boundary и не подменяются скрытым API.
            </p>
          )}
          <button
            type="button"
            onClick={() => void approvePreparedPlan()}
            disabled={busy !== null}
            className="mt-4 w-full rounded-lg border border-violet-700/70 bg-violet-950/40 px-3 py-2 text-xs font-medium text-violet-200 hover:border-violet-500 disabled:opacity-40"
          >
            {busy === 'plan' ? 'Фиксация…' : plan?.method_class === 'prepared_asset' ? 'Переутвердить prepared-asset план' : 'Утвердить план по готовому клипу'}
          </button>
        </WorkflowCard>

        <WorkflowCard
          step="02"
          title="Candidate"
          done={Boolean(candidate)}
          description="Candidate создаётся только из project-owned media и остаётся отдельным артефактом до Review."
        >
          {replacementOptions.length > 0 ? (
            <label className="block text-[11px] text-slate-500">
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
            <div className="rounded-lg border border-amber-900/70 bg-amber-950/30 p-3 text-[11px] leading-5 text-amber-200">
              Импортируйте второе видео в медиатеку — оно станет клипом-заменой. Исходник не предлагается сам себе как replacement.
            </div>
          )}
          <button
            type="button"
            onClick={() => void prepareCandidate()}
            disabled={busy !== null || plan?.method_class !== 'prepared_asset' || !replacementSource}
            className="mt-3 w-full rounded-lg border border-sky-700/70 bg-sky-950/40 px-3 py-2 text-xs font-medium text-sky-200 hover:border-sky-500 disabled:opacity-40"
          >
            {busy === 'candidate' ? 'Подготовка…' : 'Подготовить full candidate'}
          </button>
          {candidates.length > 1 && (
            <select
              aria-label="Выбрать candidate"
              value={candidate?.candidate_id ?? ''}
              onChange={event => {
                setSelectedCandidateId(event.target.value);
                setSelectedReviewId(null);
              }}
              className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-[10px] text-slate-400"
            >
              {candidates.map(item => (
                <option key={item.candidate_id} value={item.candidate_id}>{item.candidate_id}</option>
              ))}
            </select>
          )}
          {candidate && (
            <CandidatePreview projectId={projectId} candidate={candidate} />
          )}
        </WorkflowCard>

        <WorkflowCard
          step="03"
          title="Review + Accept"
          done={Boolean(acceptedEdit)}
          description="Каждый ReviewTarget должен быть оценён по точному candidate artifact. Accept остаётся отдельным D-032 действием."
        >
          {!candidate ? (
            <p className="text-xs leading-5 text-slate-600">Подготовьте full candidate, чтобы открыть evidence-based Review.</p>
          ) : (
            <>
              <div className="space-y-3">
                {brief.review_targets.map(target => {
                  const draft = draftFor(target.target_id);
                  return (
                    <div key={target.target_id} className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-xs leading-5 text-slate-300">{target.criterion}</p>
                        {target.required && <span className="shrink-0 text-[9px] uppercase text-violet-400">required</span>}
                      </div>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        <select
                          aria-label={`Результат ${target.target_id}`}
                          value={draft.outcome}
                          onChange={event => setDraft(target.target_id, { outcome: event.target.value as ReviewOutcome })}
                          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-[10px] text-slate-300"
                        >
                          <option value="pass">pass</option>
                          <option value="uncertain">uncertain</option>
                          <option value="fail">fail</option>
                        </select>
                        <select
                          aria-label={`Уверенность ${target.target_id}`}
                          value={draft.confidence}
                          onChange={event => setDraft(target.target_id, { confidence: event.target.value as ReviewConfidence })}
                          className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-[10px] text-slate-300"
                        >
                          <option value="high">high confidence</option>
                          <option value="medium">medium confidence</option>
                          <option value="low">low confidence</option>
                        </select>
                      </div>
                      <textarea
                        value={draft.statement}
                        onChange={event => setDraft(target.target_id, { statement: event.target.value })}
                        rows={2}
                        maxLength={4000}
                        placeholder="Что именно видно в candidate и почему это подтверждает оценку…"
                        className="mt-2 w-full resize-y rounded-md border border-slate-700 bg-slate-950 px-2 py-2 text-[11px] leading-4 text-slate-300 outline-none focus:border-violet-600"
                      />
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <button
                  type="button"
                  disabled={busy !== null || !allReviewStatementsPresent || !requiredPass || hasFail}
                  onClick={() => void submitReview('approved')}
                  className="rounded-lg bg-emerald-500 px-2 py-2 text-[10px] font-semibold text-slate-950 disabled:opacity-30"
                >Одобрить</button>
                <button
                  type="button"
                  disabled={busy !== null || !allReviewStatementsPresent || !(hasFail || hasUncertain)}
                  onClick={() => void submitReview('needs_revision')}
                  className="rounded-lg border border-amber-700 px-2 py-2 text-[10px] text-amber-300 disabled:opacity-30"
                >На доработку</button>
                <button
                  type="button"
                  disabled={busy !== null || !allReviewStatementsPresent || !hasFail}
                  onClick={() => void submitReview('rejected')}
                  className="rounded-lg border border-red-900 px-2 py-2 text-[10px] text-red-300 disabled:opacity-30"
                >Отклонить</button>
              </div>
            </>
          )}

          {reviews.length > 1 && candidate && (
            <select
              aria-label="Выбрать review"
              value={review?.review_id ?? ''}
              onChange={event => setSelectedReviewId(event.target.value)}
              className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-[10px] text-slate-400"
            >
              {reviews.map(item => (
                <option key={item.review_id} value={item.review_id}>{item.verdict} · {item.review_id}</option>
              ))}
            </select>
          )}

          {review && (
            <div className={`mt-3 rounded-xl border p-3 text-xs ${
              review.verdict === 'approved'
                ? 'border-emerald-900/70 bg-emerald-950/30 text-emerald-200'
                : review.verdict === 'needs_revision'
                  ? 'border-amber-900/70 bg-amber-950/30 text-amber-200'
                  : 'border-red-900/70 bg-red-950/30 text-red-200'
            }`}>
              <p>Review: <strong>{review.verdict}</strong></p>
              <p className="mt-1 font-mono text-[9px] opacity-60">{review.review_id}</p>
            </div>
          )}

          {review?.verdict === 'approved' && !acceptedEdit && (
            <button
              type="button"
              onClick={() => void acceptReview(review)}
              disabled={busy !== null}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-400 px-3 py-2.5 text-xs font-semibold text-slate-950 disabled:opacity-40"
            >
              <ShieldCheck size={15} />
              {busy === 'accept' ? 'Проверка и принятие…' : 'Принять в timeline'}
            </button>
          )}

          {acceptedEdit && (
            <div className="mt-3 flex items-start gap-2 rounded-xl border border-emerald-800/70 bg-emerald-950/40 p-3 text-xs leading-5 text-emerald-200">
              <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
              <span>Замена принята через D-032 и уже отображается зелёным диапазоном на timeline.</span>
            </div>
          )}
        </WorkflowCard>
      </div>
    </section>
  );
}

function WorkflowCard({
  step,
  title,
  description,
  done,
  children,
}: {
  step: string;
  title: string;
  description: string;
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="flex items-start gap-3">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-mono text-[10px] ${done ? 'bg-emerald-950 text-emerald-300' : 'bg-slate-900 text-slate-500'}`}>
          {done ? <CheckCircle2 size={15} /> : step}
        </span>
        <div>
          <h4 className="text-sm font-medium text-slate-200">{title}</h4>
          <p className="mt-1 text-[11px] leading-5 text-slate-500">{description}</p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function CandidatePreview({
  projectId,
  candidate,
}: {
  projectId: string;
  candidate: ReplacementCandidate;
}) {
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-slate-800 bg-black">
      <div className="flex items-center gap-2 border-b border-slate-800 px-3 py-2">
        <FileVideo2 size={13} className="text-sky-400" />
        <span className="truncate font-mono text-[9px] text-slate-500">{candidate.candidate_id}</span>
      </div>
      <video
        controls
        preload="metadata"
        src={projectArtifactMediaUrl(projectId, candidate.artifact_id)}
        className="aspect-video w-full object-contain"
      />
    </div>
  );
}
