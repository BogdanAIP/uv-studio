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
  return `${item.language} · ${item.segments.length} cues · ${item.origin}`;
}

function translationLabel(item: DubbingTranslation): string {
  return `${item.target_language} · ${item.translation_id}`;
}

export function DubbingSubtitleExportPanel({
  projectId,
  onProjectChanged,
}: DubbingSubtitleExportPanelProps) {
  const [state, setState] = useState<DubbingEditorState | null>(null);
  const [dubbingId, setDubbingId] = useState('');
  const [translationId, setTranslationId] = useState('');
  const [useTranslation, setUseTranslation] = useState(false);
  const [exported, setExported] = useState<ExportedSubtitle | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setState(await getDubbingEditorState(projectId));
  };

  useEffect(() => {
    let active = true;
    getDubbingEditorState(projectId)
      .then(value => {
        if (active) setState(value);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить subtitle state');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const transcripts = state?.dubbing.transcripts ?? [];
  const transcript = useMemo(
    () =>
      transcripts.find(item => item.dubbing_id === dubbingId) ??
      transcripts[transcripts.length - 1] ??
      null,
    [dubbingId, transcripts],
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
      translations.find(item => item.translation_id === translationId) ??
      translations[translations.length - 1] ??
      null,
    [translationId, translations],
  );

  const handleExport = async () => {
    if (!transcript) return;
    if (useTranslation && !translation) {
      setError('Для выбранного transcript нет сохранённого перевода.');
      return;
    }
    setBusy(true);
    setError(null);
    setExported(null);
    try {
      const result = await exportWebVTT(projectId, {
        dubbing_id: transcript.dubbing_id,
        ...(useTranslation && translation
          ? { translation_id: translation.translation_id }
          : {}),
      });
      setExported({ output: result.result.output, artifact: result.result.artifact });
      await refresh();
      await onProjectChanged?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось экспортировать WebVTT');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mt-4 rounded-2xl border border-indigo-900/60 bg-slate-950/80 p-4 sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-indigo-300">
            <Captions size={18} />
            <p className="text-xs uppercase tracking-[0.18em]">Stage 5 · subtitles</p>
          </div>
          <h2 className="mt-2 text-xl font-semibold text-slate-100">WebVTT из канонического текста</h2>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            Таймкоды всегда берутся из текущего transcript. Для перевода меняется только текст cue; точная transcript/translation SHA-привязка сохраняется в metadata артефакта.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={busy}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-slate-500 disabled:opacity-40"
        >
          <RefreshCw size={14} />
          Перечитать
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-red-900/70 bg-red-950/35 p-3 text-xs text-red-200">
          {error}
        </div>
      )}

      {transcripts.length === 0 ? (
        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-500">
          Сначала примите transcript в блоке дубляжа.
        </div>
      ) : (
        <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
          <label className="text-xs text-slate-500">
            Transcript
            <select
              value={transcript?.dubbing_id ?? ''}
              onChange={event => {
                setDubbingId(event.target.value);
                setTranslationId('');
                setExported(null);
              }}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
            >
              {transcripts.map(item => (
                <option key={item.dubbing_id} value={item.dubbing_id}>
                  {transcriptLabel(item)}
                </option>
              ))}
            </select>
          </label>

          <div>
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input
                type="checkbox"
                checked={useTranslation}
                onChange={event => {
                  setUseTranslation(event.target.checked);
                  setExported(null);
                }}
              />
              Экспортировать сохранённый перевод
            </label>
            <select
              value={translation?.translation_id ?? ''}
              onChange={event => {
                setTranslationId(event.target.value);
                setExported(null);
              }}
              disabled={!useTranslation || translations.length === 0}
              className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 disabled:opacity-40"
            >
              {translations.length === 0 && <option value="">Нет перевода</option>}
              {translations.map(item => (
                <option key={item.translation_id} value={item.translation_id}>
                  {translationLabel(item)}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => void handleExport()}
            disabled={busy || !transcript || (useTranslation && !translation)}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-400 px-4 py-2.5 text-xs font-semibold text-slate-950 disabled:opacity-40"
          >
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Captions size={14} />}
            Создать WebVTT
          </button>
        </div>
      )}

      {exported && (
        <div className="mt-4 flex flex-col gap-3 rounded-xl border border-emerald-900/50 bg-emerald-950/15 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-xs text-emerald-100">
            <p className="font-medium">WebVTT зарегистрирован в проекте.</p>
            <p className="mt-1 font-mono text-[10px] text-emerald-400">
              {exported.artifact.id} · {exported.output.language} · {exported.output.cue_count} cues
            </p>
          </div>
          <a
            href={projectArtifactDownloadUrl(projectId, exported.artifact.id)}
            download
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-700 px-3 py-2 text-xs text-emerald-100 hover:bg-emerald-950/40"
          >
            <Download size={14} />
            Скачать .vtt
          </a>
        </div>
      )}
    </section>
  );
}
