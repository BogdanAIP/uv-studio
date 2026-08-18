'use client';

import { Captions, Download, Loader2, RefreshCw } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  getDubbingEditorState,
  type DubbingEditorState,
  type DubbingTranscript,
  type DubbingTranslation,
} from '@/lib/dubbingApi';
import {
  exportWebVTT,
  projectArtifactDownloadUrl,
  type WebVTTExportOutput,
} from '@/lib/subtitleApi';
import type { ProjectReference } from '@/lib/projectsApi';

interface DubbingSubtitleExportPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

interface ExportedSubtitle {
  output: WebVTTExportOutput;
  artifact: ProjectReference;
}

function transcriptLabel(item: DubbingTranscript): string {
  return `${item.language} · ${item.segments.length} фрагм.`;
}

function translationLabel(item: DubbingTranslation): string {
  return `${item.target_language} · ${item.segments.length} фрагм.`;
}

export function DubbingSubtitleExportPanel({ projectId, onProjectChanged }: DubbingSubtitleExportPanelProps) {
  const [state, setState] = useState<DubbingEditorState | null>(null);
  const [dubbingId, setDubbingId] = useState('');
  const [translationId, setTranslationId] = useState('');
  const [useTranslation, setUseTranslation] = useState(false);
  const [exported, setExported] = useState<ExportedSubtitle | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => { setState(await getDubbingEditorState(projectId)); };

  useEffect(() => {
    let active = true;
    getDubbingEditorState(projectId)
      .then(value => { if (active) setState(value); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить данные субтитров'); });
    return () => { active = false; };
  }, [projectId]);

  const transcripts = state?.dubbing.transcripts ?? [];
  const transcript = useMemo(() => transcripts.find(item => item.dubbing_id === dubbingId) ?? transcripts.at(-1) ?? null, [dubbingId, transcripts]);
  const translations = useMemo(() => transcript && state ? state.dubbing.translations.filter(item => item.dubbing_id === transcript.dubbing_id) : [], [state, transcript]);
  const translation = useMemo(() => translations.find(item => item.translation_id === translationId) ?? translations.at(-1) ?? null, [translationId, translations]);

  const handleExport = async () => {
    if (!transcript) return;
    if (useTranslation && !translation) {
      setError('Для выбранного текста нет сохранённого перевода.');
      return;
    }
    setBusy(true); setError(null); setExported(null);
    try {
      const result = await exportWebVTT(projectId, {
        dubbing_id: transcript.dubbing_id,
        ...(useTranslation && translation ? { translation_id: translation.translation_id } : {}),
      });
      setExported({ output: result.result.output, artifact: result.result.artifact });
      await refresh(); await onProjectChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать файл субтитров');
    } finally { setBusy(false); }
  };

  return (
    <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><Captions size={17} /></span>
          <div>
            <h2 className="text-lg font-medium text-zinc-100">Субтитры</h2>
            <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Создайте WebVTT из проверенного текста или его сохранённого перевода. Таймкоды остаются привязаны к исходным фрагментам речи.</p>
          </div>
        </div>
        <button type="button" onClick={() => void refresh()} disabled={busy} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[var(--uv-border)] px-3 text-xs text-zinc-500 hover:text-zinc-300 disabled:opacity-40"><RefreshCw size={13} /> Обновить</button>
      </div>

      {error && <div className="mt-4 rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-3 text-sm text-rose-200">{error}</div>}

      {transcripts.length === 0 ? (
        <div className="mt-5 rounded-xl border border-dashed border-[var(--uv-border)] p-5 text-sm text-zinc-700">Сначала сохраните проверенный текст в разделе «Дубляж».</div>
      ) : (
        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
          <label className="text-xs text-zinc-600">Текст<select value={transcript?.dubbing_id ?? ''} onChange={event => { setDubbingId(event.target.value); setTranslationId(''); setExported(null); }} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300">{transcripts.map((item, index) => <option key={item.dubbing_id} value={item.dubbing_id}>Версия {index + 1} · {transcriptLabel(item)}</option>)}</select></label>
          <div>
            <label className="flex items-center gap-2 text-xs text-zinc-500"><input type="checkbox" checked={useTranslation} onChange={event => { setUseTranslation(event.target.checked); setExported(null); }} /> Использовать сохранённый перевод</label>
            <select aria-label="Перевод для субтитров" value={translation?.translation_id ?? ''} onChange={event => { setTranslationId(event.target.value); setExported(null); }} disabled={!useTranslation || translations.length === 0} className="mt-2 w-full rounded-xl border border-[var(--uv-border)] bg-black/20 px-3 py-2.5 text-sm text-zinc-300 disabled:opacity-35"><option value="">{translations.length ? 'Выберите перевод' : 'Перевода пока нет'}</option>{translations.map((item, index) => <option key={item.translation_id} value={item.translation_id}>Перевод {index + 1} · {translationLabel(item)}</option>)}</select>
          </div>
          <button type="button" onClick={() => void handleExport()} disabled={busy || !transcript || (useTranslation && !translation)} className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-violet-400 px-4 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600">{busy ? <Loader2 size={14} className="animate-spin" /> : <Captions size={14} />} Создать .vtt</button>
        </div>
      )}

      {exported && (
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.06] p-4 sm:flex-row sm:items-center sm:justify-between">
          <div><p className="text-sm font-medium text-emerald-200">Субтитры готовы</p><p className="mt-1 text-xs text-emerald-300/60">{exported.output.language} · {exported.output.cue_count} фрагм.</p></div>
          <a href={projectArtifactDownloadUrl(projectId, exported.artifact.id)} download className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-emerald-400/25 px-3 text-xs text-emerald-100 hover:bg-emerald-400/[0.06]"><Download size={13} /> Скачать .vtt</a>
        </div>
      )}
    </section>
  );
}
