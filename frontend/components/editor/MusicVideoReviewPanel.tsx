'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getUVProject, type ProjectReference } from '@/lib/projectsApi';
import { projectVideoArtifactUrl } from '@/lib/musicVideoApi';
import {
  getMusicVideoReview,
  submitMusicVideoReview,
  type MusicVideoReviewOutcome,
  type MusicVideoReviewState,
  type MusicVideoReviewVerdict,
} from '@/lib/musicVideoReviewApi';

interface MusicVideoReviewPanelProps {
  projectId: string;
  refreshRevision?: number;
  onProjectChanged?: () => void | Promise<void>;
}

function seconds(us: number): string {
  return (us / 1_000_000).toFixed(3).replace(/\.000$/, '');
}

function renderArtifact(reference: ProjectReference): boolean {
  return reference.kind === 'video' && reference.metadata.lifecycle === 'music_video_render';
}

export function MusicVideoReviewPanel({ projectId, refreshRevision = 0, onProjectChanged }: MusicVideoReviewPanelProps) {
  const [artifacts, setArtifacts] = useState<ProjectReference[]>([]);
  const [artifactId, setArtifactId] = useState('');
  const [review, setReview] = useState<MusicVideoReviewState | null>(null);
  const [verdict, setVerdict] = useState<MusicVideoReviewVerdict>('approved');
  const [transitionOutcome, setTransitionOutcome] = useState<MusicVideoReviewOutcome>('pass');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const project = await getUVProject(projectId);
    const rendered = project.artifacts.filter(renderArtifact);
    setArtifacts(rendered);
    setArtifactId(current => rendered.some(item => item.id === current) ? current : rendered.at(-1)?.id ?? '');
    try {
      const currentReview = await getMusicVideoReview(projectId);
      setReview(currentReview);
      setWarning(null);
      if (currentReview) {
        setArtifactId(currentReview.artifact_id);
        setVerdict(currentReview.verdict);
        setTransitionOutcome(currentReview.transition_outcome);
        setNote(currentReview.note ?? '');
      }
    } catch (reason) {
      setReview(null);
      setWarning(reason instanceof Error ? reason.message : 'Предыдущая проверка устарела');
    }
  }, [projectId]);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void refresh().catch(reason => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Не удалось загрузить финальную проверку');
      });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [refresh, refreshRevision]);

  const selected = useMemo(() => artifacts.find(item => item.id === artifactId) ?? null, [artifacts, artifactId]);
  const excerpt = selected?.metadata.song_excerpt;
  const excerptDuration = typeof excerpt === 'object' && excerpt !== null
    && typeof (excerpt as Record<string, unknown>).start_us === 'number'
    && typeof (excerpt as Record<string, unknown>).end_us === 'number'
    ? ((excerpt as Record<string, number>).end_us - (excerpt as Record<string, number>).start_us)
    : null;

  const submit = async () => {
    if (!artifactId) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await submitMusicVideoReview(projectId, {
        artifact_id: artifactId,
        verdict,
        transition_outcome: transitionOutcome,
        note: note.trim() || null,
      });
      setReview(saved);
      setWarning(null);
      await onProjectChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Финальная проверка не сохранена');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-emerald-900/60 bg-slate-900/60 p-6">
      <p className="text-xs uppercase tracking-wider text-emerald-400">Stage 7 · Final Review</p>
      <h2 className="mt-2 text-xl font-medium">Финальная проверка музыкального клипа</h2>
      <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">
        Approval привязан к точному SHA рендера, текущим Music Map/Director/Assembly и измеримому rhythm audit. Релизный excerpt должен быть 20–30 секунд; переходы подтверждаются человеком по готовому рендеру.
      </p>

      {artifacts.length === 0 ? (
        <p className="mt-5 rounded-lg border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-400">Сначала соберите canonical master-render выше.</p>
      ) : (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <label className="text-xs text-slate-500">
              Финальный рендер
              <select aria-label="Финальный Music Video рендер" value={artifactId} onChange={event => setArtifactId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm">
                {artifacts.map(item => <option key={item.id} value={item.id}>{item.id}</option>)}
              </select>
            </label>
            {selected && (
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                <a href={projectVideoArtifactUrl(projectId, selected.id)} target="_blank" rel="noreferrer" className="text-emerald-300 hover:text-emerald-200">Открыть рендер</a>
                {excerptDuration !== null && <span>excerpt: {seconds(excerptDuration)} с</span>}
                {excerptDuration !== null && <span className={excerptDuration >= 20_000_000 && excerptDuration <= 30_000_000 ? 'text-emerald-300' : 'text-amber-300'}>{excerptDuration >= 20_000_000 && excerptDuration <= 30_000_000 ? '20–30 с: pass' : '20–30 с: fail'}</span>}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs text-slate-500">Вердикт
                <select aria-label="Вердикт финальной Music Video проверки" value={verdict} onChange={event => setVerdict(event.target.value as MusicVideoReviewVerdict)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm">
                  <option value="approved">Approved</option><option value="needs_revision">Needs revision</option><option value="rejected">Rejected</option>
                </select>
              </label>
              <label className="text-xs text-slate-500">Переходы между сценами
                <select aria-label="Проверка переходов Music Video" value={transitionOutcome} onChange={event => setTransitionOutcome(event.target.value as MusicVideoReviewOutcome)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm">
                  <option value="pass">Pass</option><option value="uncertain">Uncertain</option><option value="fail">Fail</option>
                </select>
              </label>
            </div>
            <textarea aria-label="Заметка финальной Music Video проверки" value={note} onChange={event => setNote(event.target.value)} rows={3} maxLength={4000} placeholder="Что проверено визуально" className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm" />
            <button type="button" disabled={busy || !artifactId} onClick={() => void submit()} className="mt-3 rounded-lg bg-emerald-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">Сохранить финальную проверку</button>
          </div>
        </div>
      )}

      {warning && <p className="mt-4 rounded-lg border border-amber-900 bg-amber-950/20 p-3 text-xs text-amber-300">Предыдущая проверка больше не текущая: {warning}</p>}
      {review && (
        <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-5 text-xs">
          <Evidence label="20–30 с" outcome={review.evidence.release_duration.outcome} />
          <Evidence label="Rhythm" outcome={review.evidence.rhythm_alignment.outcome} />
          <Evidence label="Master audio" outcome={review.evidence.master_audio_binding.outcome} />
          <Evidence label="Assembly" outcome={review.evidence.visual_assembly_binding.outcome} />
          <Evidence label="Transitions" outcome={review.transition_outcome} />
        </div>
      )}
      {review && <p className="mt-4 text-sm text-slate-300">Текущий вердикт: <strong>{review.verdict}</strong></p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </section>
  );
}

function Evidence({ label, outcome }: { label: string; outcome: string }) {
  const pass = outcome === 'pass';
  return <div className={`rounded-lg border p-3 ${pass ? 'border-emerald-900 bg-emerald-950/20 text-emerald-300' : 'border-amber-900 bg-amber-950/20 text-amber-300'}`}><span className="text-slate-400">{label}: </span>{outcome}</div>;
}
