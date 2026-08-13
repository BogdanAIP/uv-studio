'use client';

import { Download, Film, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { EditorState } from '@/lib/editorApi';
import { projectArtifactMediaUrl } from '@/lib/editorApi';
import type { ProjectReference } from '@/lib/projectsApi';
import { renderAcceptedEdits } from '@/lib/renderApi';
import { formatTimelineTime } from '@/lib/timelineMath';

interface EditorRenderPanelProps {
  projectId: string;
  editorState: EditorState;
  source: ProjectReference;
  onStateChanged: () => Promise<EditorState>;
  onProjectChanged?: () => void | Promise<void>;
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) && value.every(item => typeof item === 'string') ? value : [];
}

function metadataNumber(reference: ProjectReference, key: string): number | null {
  const value = reference.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(reference: ProjectReference, key: string): string | null {
  const value = reference.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function sameEditRevision(acceptedIds: string[], renderedIds: string[]): boolean {
  if (acceptedIds.length !== renderedIds.length) return false;
  return acceptedIds.every((id, index) => id === renderedIds[index]);
}

export function EditorRenderPanel({
  projectId,
  editorState,
  source,
  onStateChanged,
  onProjectChanged,
}: EditorRenderPanelProps) {
  const [rendering, setRendering] = useState(false);
  const [latestArtifactId, setLatestArtifactId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [browserPreviewError, setBrowserPreviewError] = useState(false);

  const accepted = useMemo(
    () => editorState.accepted_edits.filter(edit => edit.source_path === source.path),
    [editorState.accepted_edits, source.path],
  );
  const acceptedIds = useMemo(() => accepted.map(edit => edit.edit_id), [accepted]);
  const renders = useMemo(
    () =>
      editorState.artifacts.filter(
        artifact =>
          artifact.kind === 'video' &&
          artifact.metadata.lifecycle === 'render' &&
          artifact.metadata.source_path === source.path,
      ),
    [editorState.artifacts, source.path],
  );
  const activeRender =
    renders.find(artifact => artifact.id === latestArtifactId) ?? renders[renders.length - 1] ?? null;
  const renderedIds = activeRender ? stringArray(activeRender.metadata.edit_ids) : [];
  const currentRevision = activeRender ? sameEditRevision(acceptedIds, renderedIds) : false;
  const actualDurationUs = activeRender
    ? metadataNumber(activeRender, 'actual_output_video_duration_us')
    : null;
  const compositionMode = activeRender ? metadataText(activeRender, 'composition_mode') : null;

  const handleRender = async () => {
    if (accepted.length === 0) return;
    setRendering(true);
    setError(null);
    setBrowserPreviewError(false);
    try {
      const envelope = await renderAcceptedEdits(projectId, source.path);
      if (!envelope.result.artifact?.id) throw new Error('Рендер завершился без зарегистрированного artifact ID.');
      setLatestArtifactId(envelope.result.artifact.id);
      await onStateChanged();
      await onProjectChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать мастер-рендер');
    } finally {
      setRendering(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck size={18} className="text-emerald-300" />
            <p className="text-xs uppercase tracking-[0.18em] text-emerald-400">Authoritative render / export</p>
          </div>
          <h3 className="mt-2 text-lg font-medium text-slate-100">Собрать принятые правки в один мастер</h3>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            Accept остаётся лёгкой записью non-destructive edit state. Только эта явная операция запускает локальный FFmpeg и одним проходом материализует все принятые диапазоны текущего исходника.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void handleRender()}
          disabled={rendering || accepted.length === 0}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {rendering ? <Loader2 size={16} className="animate-spin" /> : <Film size={16} />}
          {rendering ? 'Сборка мастера…' : renders.length ? 'Пересобрать мастер' : 'Собрать мастер'}
        </button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <RenderStat label="Принято правок" value={accepted.length} />
        <RenderStat label="Мастер-рендеров" value={renders.length} />
        <RenderStat
          label="Состояние"
          value={!activeRender ? 'не собран' : currentRevision ? 'актуален' : 'устарел'}
          accent={activeRender && currentRevision ? 'ok' : activeRender ? 'warn' : undefined}
        />
      </div>

      {accepted.length === 0 && (
        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/50 p-3 text-xs leading-5 text-slate-500">
          Сначала доведите хотя бы одно изменение через Brief → Plan → Candidate → Review → Accept. Рендер не создаёт или не принимает правки сам.
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-xl border border-red-900/70 bg-red-950/40 p-3 text-xs leading-5 text-red-200">
          {error}
        </div>
      )}

      {activeRender && (
        <div className={`mt-4 rounded-xl border p-4 ${
          currentRevision
            ? 'border-emerald-900/70 bg-emerald-950/20'
            : 'border-amber-900/70 bg-amber-950/20'
        }`}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className={`text-xs font-medium ${currentRevision ? 'text-emerald-300' : 'text-amber-300'}`}>
                {currentRevision ? 'Мастер соответствует текущему Accepted state' : 'Мастер устарел — Accepted state изменился'}
              </p>
              <p className="mt-1 font-mono text-[10px] text-slate-600">{activeRender.id}</p>
            </div>
            <a
              href={projectArtifactMediaUrl(projectId, activeRender.id)}
              download={`${source.id}-uv-master.mkv`}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 transition hover:border-slate-500"
            >
              <Download size={14} />
              Скачать мастер
            </a>
          </div>

          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 font-mono text-[10px] text-slate-500">
            <span>edits: {renderedIds.length}</span>
            {actualDurationUs !== null && <span>duration: {formatTimelineTime(actualDurationUs)}</span>}
            {compositionMode && <span>{compositionMode}</span>}
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-slate-800 bg-black">
            {!browserPreviewError ? (
              <video
                key={activeRender.id}
                src={projectArtifactMediaUrl(projectId, activeRender.id)}
                controls
                playsInline
                preload="metadata"
                className="aspect-video w-full object-contain"
                onError={() => setBrowserPreviewError(true)}
              />
            ) : (
              <div className="flex min-h-44 flex-col items-center justify-center px-6 py-8 text-center">
                <RefreshCw size={22} className="text-slate-600" />
                <p className="mt-3 text-xs leading-5 text-slate-400">
                  Этот браузер не декодирует проектный FFV1/FLAC master. Файл не повреждён: authoritative render уже проверен FFprobe и остаётся доступен для скачивания.
                </p>
                <p className="mt-2 text-[10px] leading-4 text-slate-600">
                  Browser-compatible preview будет отдельной детерминированной проекцией мастера, а не заменой или скрытым повторным монтажом.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function RenderStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: 'ok' | 'warn';
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <p className="text-[10px] uppercase tracking-wider text-slate-600">{label}</p>
      <p className={`mt-1.5 text-sm font-medium ${
        accent === 'ok' ? 'text-emerald-300' : accent === 'warn' ? 'text-amber-300' : 'text-slate-300'
      }`}>
        {value}
      </p>
    </div>
  );
}
