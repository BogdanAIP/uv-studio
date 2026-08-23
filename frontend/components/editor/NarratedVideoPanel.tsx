'use client';

import { useMemo, useState } from 'react';
import { uploadPreparedAudio } from '@/lib/dubbingApi';
import {
  executeProjectWorkflowAction,
  type WorkflowAction,
  type WorkflowArtifact,
} from '@/lib/productWorkflowApi';
import type { ProjectReference } from '@/lib/projectsApi';

interface NarratedVideoPanelProps {
  projectId: string;
  artifacts: ProjectReference[];
  workflowAction?: WorkflowAction;
  currentOutcome: WorkflowArtifact | null;
  onProjectChanged: () => Promise<void> | void;
}

function preparedAudioName(reference: ProjectReference): string {
  const original = reference.metadata.original_name;
  if (typeof original === 'string' && original.trim()) return original;
  return reference.path.split('/').pop() || reference.id;
}

function actionEnum(action: WorkflowAction | undefined, field: string): string[] {
  const properties = action?.input_schema?.properties;
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return [];
  const schema = (properties as Record<string, unknown>)[field];
  if (!schema || typeof schema !== 'object' || Array.isArray(schema)) return [];
  const values = (schema as Record<string, unknown>).enum;
  if (!Array.isArray(values)) return [];
  return values.filter((value): value is string => typeof value === 'string' && Boolean(value));
}

function suggestedString(action: WorkflowAction | undefined, field: string): string | null {
  const value = action?.suggested_input?.[field];
  return typeof value === 'string' && value ? value : null;
}

export function NarratedVideoPanel({
  projectId,
  artifacts,
  workflowAction,
  currentOutcome,
  onProjectChanged,
}: NarratedVideoPanelProps) {
  const allowedAudioIds = useMemo(() => actionEnum(workflowAction, 'audio_id'), [workflowAction]);
  const allowedAudio = useMemo(
    () => artifacts.filter(reference => (
      reference.kind === 'audio'
      && reference.metadata.role === 'prepared-speech'
      && allowedAudioIds.includes(reference.id)
    )),
    [allowedAudioIds, artifacts],
  );
  const workspaceRevision = suggestedString(workflowAction, 'workspace_revision_sha256');
  const suggestedAudioId = suggestedString(workflowAction, 'audio_id');
  const [requestedAudioId, setRequestedAudioId] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedAudioId = (
    requestedAudioId && allowedAudioIds.includes(requestedAudioId)
      ? requestedAudioId
      : suggestedAudioId && allowedAudioIds.includes(suggestedAudioId)
        ? suggestedAudioId
        : allowedAudioIds[0] ?? ''
  );

  const uploadNarration = async (file: File | undefined) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const reference = await uploadPreparedAudio(projectId, file, 'imported');
      await onProjectChanged();
      setRequestedAudioId(reference.id);
      setMessage('Дикторская дорожка импортирована как проверяемый PreparedAudio проекта.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать дикторскую дорожку');
    } finally {
      setBusy(false);
    }
  };

  const render = async () => {
    if (!workflowAction || !workspaceRevision || !selectedAudioId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await executeProjectWorkflowAction(
        projectId,
        'render_narrated',
        {
          workspace_revision_sha256: workspaceRevision,
          audio_id: selectedAudioId,
        },
      );
      if (!('execution' in response)) {
        throw new Error('Narrated render вернул неожиданный тип результата');
      }
      setMessage('Новый Narrated мастер собран и зарегистрирован в проекте.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать Narrated мастер');
    } finally {
      setBusy(false);
    }
  };

  const canRender = Boolean(
    workflowAction?.enabled
    && workspaceRevision
    && selectedAudioId
    && allowedAudioIds.includes(selectedAudioId),
  );

  return (
    <section className="mb-6 rounded-2xl border border-violet-900/60 bg-violet-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-violet-400">Narrated · дикторская дорожка и мастер</p>
      <h2 className="mt-2 text-xl font-medium">Подготовленная речь</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
        Финальная сборка использует только текущую SHA-привязанную ревизию workspace, изображения из неё
        и проверенный project-owned PreparedAudio. Обычное аудио из материалов workspace не подменяет
        дикторскую дорожку. TTS остаётся отдельным необязательным путём с существующим явным D-017 согласием.
      </p>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Импортировать дикторскую дорожку</span>
          <input
            aria-label="Narrated prepared audio upload"
            type="file"
            accept="audio/*"
            disabled={busy}
            onChange={event => void uploadNarration(event.target.files?.[0])}
            className="mt-3 block w-full text-xs text-slate-400"
          />
        </label>

        <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
          <span className="block font-medium">Проверенная дорожка для мастера</span>
          <select
            aria-label="Narrated prepared audio"
            value={selectedAudioId}
            disabled={busy || allowedAudio.length === 0}
            onChange={event => setRequestedAudioId(event.target.value)}
            className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2"
          >
            {allowedAudio.length === 0 ? (
              <option value="">Нет доступной проверенной дорожки</option>
            ) : (
              allowedAudio.map(reference => (
                <option key={reference.id} value={reference.id}>
                  {preparedAudioName(reference)}
                </option>
              ))
            )}
          </select>
        </label>
      </div>

      <button
        type="button"
        disabled={busy || !canRender}
        onClick={() => void render()}
        className="mt-6 rounded-lg bg-violet-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        Собрать видео с дикторской дорожкой
      </button>

      {!workflowAction?.enabled && workflowAction && workflowAction.blocked_by.length > 0 && (
        <p className="mt-3 text-xs leading-5 text-amber-300">
          Пока не готово: {workflowAction.blocked_by.join(', ')}
        </p>
      )}

      {currentOutcome && (
        <div className="mt-6 rounded-xl border border-emerald-900/60 bg-emerald-950/20 p-4">
          <p className="text-sm font-medium text-emerald-300">Текущий мастер соответствует входам</p>
          <p className="mt-2 break-all font-mono text-xs text-slate-500">{currentOutcome.path}</p>
        </div>
      )}

      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </section>
  );
}
