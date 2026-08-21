'use client';

import { FileText, Loader2, Upload } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { uploadProjectSource } from '@/lib/editorApi';
import {
  executeProjectWorkflowAction,
  type WorkflowAction,
} from '@/lib/productWorkflowApi';
import type { ProjectReference } from '@/lib/projectsApi';

interface DubbingSourceSetupPanelProps {
  projectId: string;
  sources: ProjectReference[];
  transcriptAction?: WorkflowAction;
  onProjectChanged?: () => void | Promise<void>;
}

type BusyAction = 'video' | 'transcript' | null;

function toMicroseconds(value: string): number | null {
  const normalized = value.trim().replace(',', '.');
  if (!normalized) return null;
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed * 1_000_000);
}

function projectedSourceIds(action?: WorkflowAction): string[] {
  const properties = action?.input_schema?.properties;
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return [];
  const source = (properties as Record<string, unknown>).source_id;
  if (!source || typeof source !== 'object' || Array.isArray(source)) return [];
  const values = (source as Record<string, unknown>).enum;
  if (!Array.isArray(values)) return [];
  return values.filter((value): value is string => typeof value === 'string' && Boolean(value));
}

function sourceName(source: ProjectReference): string {
  const value = source.metadata.original_name;
  return typeof value === 'string' && value.trim() ? value : source.id;
}

export function DubbingSourceSetupPanel({
  projectId,
  sources,
  transcriptAction,
  onProjectChanged,
}: DubbingSourceSetupPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const videoSources = useMemo(() => sources.filter(source => source.kind === 'video'), [sources]);
  const allowedSourceIds = useMemo(() => projectedSourceIds(transcriptAction), [transcriptAction]);
  const transcriptSources = useMemo(
    () => videoSources.filter(source => allowedSourceIds.includes(source.id)),
    [allowedSourceIds, videoSources],
  );
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [language, setLanguage] = useState('en');
  const [startSeconds, setStartSeconds] = useState('0');
  const [endSeconds, setEndSeconds] = useState('');
  const [transcriptText, setTranscriptText] = useState('');
  const [busy, setBusy] = useState<BusyAction>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (selectedSourceId && transcriptSources.some(source => source.id === selectedSourceId)) return;
    setSelectedSourceId(transcriptSources[0]?.id ?? '');
  }, [selectedSourceId, transcriptSources]);

  const handleFile = async (file: File | null) => {
    if (!file || busy !== null) return;
    setBusy('video');
    setError(null);
    setNotice(null);
    try {
      await uploadProjectSource(projectId, file);
      await onProjectChanged?.();
      setNotice(`Видео «${file.name}» добавлено в Project Store.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать видео для дубляжа');
    } finally {
      setBusy(null);
      if (inputRef.current) inputRef.current.value = '';
    }
  };

  const handleTranscript = async () => {
    if (!transcriptAction?.enabled || !selectedSourceId || busy !== null) return;
    const startUs = toMicroseconds(startSeconds);
    const endUs = toMicroseconds(endSeconds);
    const text = transcriptText.trim();
    const normalizedLanguage = language.trim().toLowerCase();
    if (startUs === null || endUs === null || endUs <= startUs) {
      setError('Укажите корректный диапазон transcript: конец должен быть позже начала.');
      return;
    }
    if (normalizedLanguage.length < 2) {
      setError('Укажите язык transcript.');
      return;
    }
    if (!text) {
      setError('Введите проверенный текст речи.');
      return;
    }

    setBusy('transcript');
    setError(null);
    setNotice(null);
    try {
      const response = await executeProjectWorkflowAction(
        projectId,
        'import_dubbing_transcript',
        {
          source_id: selectedSourceId,
          language: normalizedLanguage,
          start_us: startUs,
          end_us: endUs,
          segments: [
            {
              segment_id: 'manual_1',
              start_us: startUs,
              end_us: endUs,
              text,
            },
          ],
        },
      );
      if (!('result' in response)) {
        throw new Error('Product Orchestrator вернул capability-ответ вместо сохранённого transcript.');
      }
      await onProjectChanged?.();
      setNotice('Проверенный transcript сохранён в каноническое состояние проекта.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить проверенный transcript');
    } finally {
      setBusy(null);
    }
  };

  return (
    <section className="mt-8 rounded-2xl border border-violet-900/50 bg-slate-900/50 p-4 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-violet-300">Старт Dubbing</p>
          <h2 className="mt-2 text-lg font-semibold text-slate-100">Исходное видео для дубляжа</h2>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-slate-500">
            Видео сохраняется как project-owned source и проверяется перед тем, как Product Orchestrator разрешит работу с текстом, речью и финальным рендером.
          </p>
          <p className="mt-2 text-xs text-slate-600">
            {videoSources.length > 0 ? `Видео в проекте: ${videoSources.length}` : 'Сначала добавьте видео с исходной речью.'}
          </p>
        </div>

        <div className="shrink-0">
          <input
            ref={inputRef}
            type="file"
            accept="video/*"
            aria-label="Импортировать видео для дубляжа"
            className="sr-only"
            onChange={event => void handleFile(event.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy === 'video' ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {videoSources.length > 0 ? 'Добавить ещё видео' : 'Добавить видео'}
          </button>
        </div>
      </div>

      {videoSources.length > 0 && (
        <div className="mt-6 border-t border-slate-800 pt-6">
          <div className="flex items-start gap-3">
            <FileText size={18} className="mt-0.5 shrink-0 text-violet-300" />
            <div>
              <h3 className="text-sm font-medium text-slate-200">Проверенный transcript без ASR</h3>
              <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
                Если локальный whisper.cpp не настроен, введите уже проверенный текст вручную. Здесь сохраняется один точный речевой диапазон; автоматический ASR ниже по-прежнему остаётся черновиком до явного принятия.
              </p>
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <label className="text-xs text-slate-500 md:col-span-2">
              Видео
              <select
                aria-label="Видео для ручного transcript"
                value={selectedSourceId}
                onChange={event => setSelectedSourceId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              >
                {transcriptSources.map(source => (
                  <option key={source.id} value={source.id}>{sourceName(source)}</option>
                ))}
              </select>
            </label>
            <label className="text-xs text-slate-500">
              Язык
              <input
                aria-label="Язык ручного transcript"
                value={language}
                onChange={event => setLanguage(event.target.value)}
                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
              />
            </label>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-xs text-slate-500">
                Начало, с
                <input
                  aria-label="Начало ручного transcript"
                  inputMode="decimal"
                  value={startSeconds}
                  onChange={event => setStartSeconds(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                />
              </label>
              <label className="text-xs text-slate-500">
                Конец, с
                <input
                  aria-label="Конец ручного transcript"
                  inputMode="decimal"
                  value={endSeconds}
                  onChange={event => setEndSeconds(event.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200"
                />
              </label>
            </div>
          </div>

          <label className="mt-3 block text-xs text-slate-500">
            Проверенный текст речи
            <textarea
              aria-label="Текст ручного transcript"
              rows={3}
              maxLength={8000}
              value={transcriptText}
              onChange={event => setTranscriptText(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm leading-6 text-slate-200"
              placeholder="Введите текст, который действительно звучит в выбранном диапазоне…"
            />
          </label>

          <button
            type="button"
            disabled={busy !== null || !transcriptAction?.enabled || !selectedSourceId}
            onClick={() => void handleTranscript()}
            className="mt-3 inline-flex items-center gap-2 rounded-lg bg-emerald-400 px-3 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy === 'transcript' ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
            Сохранить проверенный transcript
          </button>
          {!transcriptAction?.enabled && (
            <p className="mt-2 text-xs text-amber-300">
              Product Orchestrator пока не разрешает сохранение transcript для текущего source.
            </p>
          )}
        </div>
      )}

      {error && (
        <p className="mt-4 rounded-xl border border-red-900/60 bg-red-950/30 px-3 py-2 text-xs text-red-200">
          {error}
        </p>
      )}
      {notice && (
        <p className="mt-4 rounded-xl border border-emerald-900/60 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-200">
          {notice}
        </p>
      )}
    </section>
  );
}
