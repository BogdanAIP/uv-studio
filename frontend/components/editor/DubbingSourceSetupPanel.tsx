'use client';

import { Loader2, Upload } from 'lucide-react';
import { useRef, useState } from 'react';
import { uploadProjectSource } from '@/lib/editorApi';

interface DubbingSourceSetupPanelProps {
  projectId: string;
  sourceCount: number;
  onProjectChanged?: () => void | Promise<void>;
}

export function DubbingSourceSetupPanel({
  projectId,
  sourceCount,
  onProjectChanged,
}: DubbingSourceSetupPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleFile = async (file: File | null) => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await uploadProjectSource(projectId, file);
      await onProjectChanged?.();
      setNotice(`Видео «${file.name}» добавлено в Project Store.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать видео для дубляжа');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
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
            {sourceCount > 0 ? `Видео в проекте: ${sourceCount}` : 'Сначала добавьте видео с исходной речью.'}
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
            disabled={busy}
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-xl bg-violet-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            {sourceCount > 0 ? 'Добавить ещё видео' : 'Добавить видео'}
          </button>
        </div>
      </div>

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
