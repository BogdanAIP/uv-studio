'use client';

import { useState } from 'react';
import {
  executeProjectWorkflowAction,
  type WorkflowAction,
  type WorkflowArtifact,
} from '@/lib/productWorkflowApi';

interface GeneralVideoPanelProps {
  projectId: string;
  workflowAction?: WorkflowAction;
  currentOutcome: WorkflowArtifact | null;
  onProjectChanged: () => Promise<void> | void;
}

function suggestedString(action: WorkflowAction | undefined, field: string): string | null {
  const value = action?.suggested_input?.[field];
  return typeof value === 'string' && value ? value : null;
}

export function GeneralVideoPanel({
  projectId,
  workflowAction,
  currentOutcome,
  onProjectChanged,
}: GeneralVideoPanelProps) {
  const workspaceRevision = suggestedString(workflowAction, 'workspace_revision_sha256');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const render = async () => {
    if (!workflowAction || !workspaceRevision) return;
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const response = await executeProjectWorkflowAction(
        projectId,
        'render_general',
        { workspace_revision_sha256: workspaceRevision },
      );
      if (!('execution' in response)) {
        throw new Error('General Video render вернул неожиданный тип результата');
      }
      setMessage('Новый General Video мастер собран и зарегистрирован в проекте.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать General Video мастер');
    } finally {
      setBusy(false);
    }
  };

  const canRender = Boolean(workflowAction?.enabled && workspaceRevision);

  return (
    <section className="mb-6 rounded-2xl border border-indigo-900/60 bg-indigo-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-indigo-400">General Video · локальный мастер</p>
      <h2 className="mt-2 text-xl font-medium">Сборка текущего визуального ряда</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
        Первый авторитетный General Video render намеренно ограничен: изображения показываются по 2 секунды,
        видео используются целиком и нормализуются в 1280×720/30 fps. Встроенный звук видеоклипов не смешивается
        скрыто; можно выбрать не более одной отдельной аудиодорожки в workspace или собрать ролик без звука.
      </p>

      <button
        type="button"
        disabled={busy || !canRender}
        onClick={() => void render()}
        className="mt-6 rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        Собрать обычный видеоролик
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
