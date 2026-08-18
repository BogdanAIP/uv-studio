'use client';

import { CheckCircle2, FileVideo2, ListChecks, ShieldCheck } from 'lucide-react';
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
  return brief.constraints.find(item => item.constraint_id === 'requested_change')?.requirement ??
    brief.constraints[0]?.requirement ??
    'Выполнить запрошенное изменение выбранного фрагмента.';
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
  const fallbackBrief = briefs.find(brief => brief.edit_id === preferredEditId) ?? briefs[briefs.length - 1] ?? null;
  const brief = briefs.find(item => item.edit_id === selectedEditId) ?? fallbackBrief;

  if (!brief) return null;

  const plan = editorState.replacement_plans.find(item => item.edit_id === brief.edit_id) ?? null;
  const candidates = editorState.replacement_candidates.filter(item => item.edit_id === brief.edit_id && item.stage === 'full');
  const candidate = candidates.find(item => item.candidate_id === selectedCandidateId) ?? candidates[candidates.length - 1] ?? null;
  const reviews = candidate ? editorState.replacement_reviews.filter(item => item.candidate_id === candidate.candidate_id) : [];
  const review = reviews.find(item => item.review_id === selectedReviewId) ?? reviews[reviews.length - 1] ?? null;
  const acceptedEdit = editorState.accepted_edits.find(item => item.edit_id === brief.edit_id) ?? null;
  const replacementOptions = editorState.sources.filter(item => item.path !== brief.source_path);
  const replacementSource = replacementOptions.find(item => item.id === replacementSourceId) ?? replacementOptions[0] ?? null;
  const change = requestedChange(brief);

  const draftFor = (targetId: string): ReviewDraft => reviewDrafts[targetId] ?? DEFAULT_REVIEW_DRAFT;
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
    if (!replacementSource) throw new Error('Добавьте отдельный видеоклип, который будет использован для замены.');
    const result = await prepareAssetReplacementCandidate(projectId, brief.edit_id, replacementSource.path);
    setSelectedCandidateId(result.candidate.candidate_id);
    setSelectedReviewId(null);
    await onStateChanged();
  });

  const allReviewStatementsPresent = brief.review_targets.every(target => draftFor(target.target_id).statement.trim().length > 0);
  const hasFail = brief.review_targets.some(target => draftFor(target.target_id).outcome === 'fail');
  const hasUncertain = brief.review_targets.some(target => draftFor(target.target_id).outcome === 'uncertain');
  const requiredPass = brief.review_targets.filter(target => target.required).every(target => draftFor(target.target_id).outcome === 'pass');

  const submitReview = (verdict: ReviewVerdict) => withBusy(`review-${verdict}`, async () => {
    if (!candidate) throw new Error('Сначала создайте предпросмотр.');
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
    <section className="rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--uv-border)] pb-4">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><ListChecks size={17} /></span>
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-zinc-600">Текущее изменение</p>
            <h3 className="mt-1 text-sm font-medium text-zinc-200">Предпросмотр → проверка → применение</h3>
            <p className="mt-1 max-w-2xl text-xs leading-5 text-zinc-600">{change}</p>
          </div>
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
            className="rounded-lg border border-[var(--uv-border)] bg-black/20 px-3 py-2 text-xs text-zinc-400"
          >
            {briefs.map((item, index) => (
              <option key={item.edit_id} value={item.edit_id}>
                Изменение {index + 1}: {formatTimelineTime(item.start_us)} — {formatTimelineTime(item.end_us)}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && <div className="mt-4 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-xs leading-5 text-rose-200">{error}</div>}

      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        <WorkflowCard step="1" title="Источник замены" done={Boolean(plan)} description="Выберите уже добавленный клип. Исходное видео за пределами выделения останется без изменений.">
          {replacementOptions.length > 0 ? (
            <label className="block text-[11px] text-zinc-600">
              Клип для замены
              <select
                value={replacementSource?.id ?? ''}
                onChange={event => setReplacementSourceId(event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-[var(--uv-border)] bg-black/20 px-3 py-2 text-xs text-zinc-300"
              >
                {replacementOptions.map(source => <option key={source.id} value={source.id}>{referenceName(source)}</option>)}
              </select>
            </label>
          ) : (
            <div className="rounded-lg border border-amber-400/15 bg-amber-400/[0.06] p-3 text-[11px] leading-5 text-amber-100/80">
              Добавьте второе видео в медиатеку — оно станет доступно здесь как клип замены.
            </div>
          )}
          <button
            type="button"
            onClick={() => void approvePreparedPlan()}
            disabled={busy !== null || !replacementSource}
            className="mt-3 w-full rounded-lg border border-violet-400/25 bg-violet-400/10 px-3 py-2.5 text-xs font-medium text-violet-200 transition hover:bg-violet-400/15 disabled:cursor-not-allowed disabled:border-[var(--uv-border)] disabled:bg-black/10 disabled:text-zinc-700"
          >
            {busy === 'plan' ? 'Сохраняем…' : plan?.method_class === 'prepared_asset' ? 'Готовый клип выбран' : 'Использовать готовый клип'}
          </button>
        </WorkflowCard>

        <WorkflowCard step="2" title="Предпросмотр" done={Boolean(candidate)} description="Подготовьте вариант и посмотрите его до применения к монтажу.">
          <button
            type="button"
            onClick={() => void prepareCandidate()}
            disabled={busy !== null || plan?.method_class !== 'prepared_asset' || !replacementSource}
            className="w-full rounded-lg bg-violet-400 px-3 py-2.5 text-xs font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
          >
            {busy === 'candidate' ? 'Создаём…' : 'Создать предпросмотр'}
          </button>
          {plan?.method_class !== 'prepared_asset' && <p className="mt-2 text-[10px] leading-4 text-zinc-700">Сначала выберите клип замены.</p>}
          {candidates.length > 1 && (
            <select
              aria-label="Выбрать предпросмотр"
              value={candidate?.candidate_id ?? ''}
              onChange={event => {
                setSelectedCandidateId(event.target.value);
                setSelectedReviewId(null);
              }}
              className="mt-3 w-full rounded-lg border border-[var(--uv-border)] bg-black/20 px-3 py-2 text-[10px] text-zinc-500"
            >
              {candidates.map((item, index) => <option key={item.candidate_id} value={item.candidate_id}>Предпросмотр {index + 1}</option>)}
            </select>
          )}
          {candidate && <CandidatePreview projectId={projectId} candidate={candidate} />}
        </WorkflowCard>

        <WorkflowCard step="3" title="Проверка и применение" done={Boolean(acceptedEdit)} description="Подтвердите критерии результата. Применение остаётся отдельным явным действием.">
          {!candidate ? (
            <p className="text-xs leading-5 text-zinc-700">После создания предпросмотра здесь появится проверка результата.</p>
          ) : (
            <>
              <div className="space-y-3">
                {brief.review_targets.map(target => {
                  const draft = draftFor(target.target_id);
                  return (
                    <div key={target.target_id} className="rounded-xl border border-[var(--uv-border)] bg-black/15 p-3">
                      <p className="text-xs leading-5 text-zinc-300">{target.criterion}</p>
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        <select
                          aria-label={`Результат ${target.target_id}`}
                          value={draft.outcome}
                          onChange={event => setDraft(target.target_id, { outcome: event.target.value as ReviewOutcome })}
                          className="rounded-md border border-[var(--uv-border)] bg-[var(--uv-surface-0)] px-2 py-1.5 text-[10px] text-zinc-300"
                        >
                          <option value="pass">Соответствует</option>
                          <option value="uncertain">Не уверен</option>
                          <option value="fail">Не соответствует</option>
                        </select>
                        <select
                          aria-label={`Уверенность ${target.target_id}`}
                          value={draft.confidence}
                          onChange={event => setDraft(target.target_id, { confidence: event.target.value as ReviewConfidence })}
                          className="rounded-md border border-[var(--uv-border)] bg-[var(--uv-surface-0)] px-2 py-1.5 text-[10px] text-zinc-300"
                        >
                          <option value="high">Высокая уверенность</option>
                          <option value="medium">Средняя уверенность</option>
                          <option value="low">Низкая уверенность</option>
                        </select>
                      </div>
                      <textarea
                        value={draft.statement}
                        onChange={event => setDraft(target.target_id, { statement: event.target.value })}
                        rows={2}
                        maxLength={4000}
                        placeholder="Что видно в предпросмотре?"
                        className="mt-2 w-full resize-y rounded-md border border-[var(--uv-border)] bg-[var(--uv-surface-0)] px-2 py-2 text-[11px] leading-4 text-zinc-300 placeholder:text-zinc-700 focus:border-violet-400/40"
                      />
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-2">
                <button type="button" disabled={busy !== null || !allReviewStatementsPresent || !requiredPass || hasFail} onClick={() => void submitReview('approved')} className="rounded-lg bg-emerald-400 px-2 py-2 text-[10px] font-semibold text-zinc-950 disabled:bg-zinc-800 disabled:text-zinc-600">Одобрить</button>
                <button type="button" disabled={busy !== null || !allReviewStatementsPresent || !(hasFail || hasUncertain)} onClick={() => void submitReview('needs_revision')} className="rounded-lg border border-amber-400/20 px-2 py-2 text-[10px] text-amber-200 disabled:opacity-30">На доработку</button>
                <button type="button" disabled={busy !== null || !allReviewStatementsPresent || !hasFail} onClick={() => void submitReview('rejected')} className="rounded-lg border border-rose-400/20 px-2 py-2 text-[10px] text-rose-200 disabled:opacity-30">Отклонить</button>
              </div>
            </>
          )}

          {reviews.length > 1 && candidate && (
            <select aria-label="Выбрать проверку" value={review?.review_id ?? ''} onChange={event => setSelectedReviewId(event.target.value)} className="mt-3 w-full rounded-lg border border-[var(--uv-border)] bg-black/20 px-3 py-2 text-[10px] text-zinc-500">
              {reviews.map((item, index) => <option key={item.review_id} value={item.review_id}>Проверка {index + 1} · {item.verdict === 'approved' ? 'одобрено' : item.verdict === 'needs_revision' ? 'доработка' : 'отклонено'}</option>)}
            </select>
          )}

          {review && (
            <div className={`mt-3 rounded-xl border p-3 text-xs ${review.verdict === 'approved' ? 'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200' : review.verdict === 'needs_revision' ? 'border-amber-400/20 bg-amber-400/[0.06] text-amber-200' : 'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}>
              Проверка: <strong>{review.verdict === 'approved' ? 'одобрено' : review.verdict === 'needs_revision' ? 'нужна доработка' : 'отклонено'}</strong>
            </div>
          )}

          {review?.verdict === 'approved' && !acceptedEdit && (
            <button
              type="button"
              onClick={() => void acceptReview(review)}
              disabled={busy !== null}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-400 px-3 py-2.5 text-xs font-semibold text-zinc-950 disabled:opacity-40"
            >
              <ShieldCheck size={15} />
              {busy === 'accept' ? 'Применяем…' : 'Применить изменение'}
            </button>
          )}

          {acceptedEdit && (
            <div className="mt-3 flex items-start gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-3 text-xs leading-5 text-emerald-200">
              <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
              <span>Изменение применено и отмечено на таймлайне.</span>
            </div>
          )}
        </WorkflowCard>
      </div>
    </section>
  );
}

function WorkflowCard({ step, title, description, done, children }: { step: string; title: string; description: string; done: boolean; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-4">
      <div className="flex items-start gap-3">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] ${done ? 'bg-emerald-400/10 text-emerald-300' : 'bg-white/[0.035] text-zinc-600'}`}>
          {done ? <CheckCircle2 size={15} /> : step}
        </span>
        <div>
          <h4 className="text-sm font-medium text-zinc-200">{title}</h4>
          <p className="mt-1 text-[11px] leading-5 text-zinc-600">{description}</p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function CandidatePreview({ projectId, candidate }: { projectId: string; candidate: ReplacementCandidate }) {
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-[var(--uv-border)] bg-black">
      <div className="flex items-center gap-2 border-b border-[var(--uv-border)] px-3 py-2 text-[10px] text-zinc-600">
        <FileVideo2 size={13} className="text-violet-300" /> Предпросмотр изменения
      </div>
      <video controls preload="metadata" src={projectArtifactMediaUrl(projectId, candidate.artifact_id)} className="aspect-video w-full object-contain" />
    </div>
  );
}
