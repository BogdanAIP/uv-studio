'use client';

import { useState } from 'react';
import {
  executeProjectWorkflowAction,
  type WorkflowAction,
  type WorkflowArtifact,
} from '@/lib/productWorkflowApi';
import { projectStage8ArtifactUrl } from '@/lib/stage8MediaApi';

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
        throw new Error('Локальная сборка вернула неожиданный тип результата');
      }
      setMessage('Новый ролик собран и сохранён в проекте.');
      await onProjectChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось собрать ролик');
    } finally {
      setBusy(false);
    }
  };

  const canRender = Boolean(workflowAction?.enabled && workspaceRevision);

  return (
    <section className="mb-6 rounded-2xl border border-indigo-900/60 bg-indigo-950/20 p-6">
      <p className="text-xs uppercase tracking-wider text-indigo-400">Локальная сборка · без платного API</p>
      <h2 className="mt-2 text-xl font-medium">Собрать текущий черновик</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
        UV Studio последовательно собирает выбранные изображения и видео в локальный H.264-файл. Изображения
        пока показываются по 2 секунды, видео используются целиком и нормализуются в 1280×720/30 fps. Можно
        добавить одну отдельную аудиодорожку или собрать ролик без звука. Эти ограничения видимы и не меняются скрыто.
      </p>

      <button
        type="button"
        disabled={busy || !canRender}
        onClick={() => void render()}
        className="mt-6 rounded-lg bg-indigo-400 px-4 py-2.5 text-sm font-medium text-slate-950 disabled:opacity-40"
      >
        {busy ? 'Собираю…' : 'Собрать ролик'}
      </button>

      {!workflowAction?.enabled && workflowAction && workflowAction.blocked_by.length > 0 && (
        <p className="mt-3 text-xs leading-5 text-amber-300">
          Сборка откроется после сохранения нужных материалов текущего проекта.
        </p>
      )}

      {currentOutcome && (
        <div className="mt-6 rounded-xl border border-emerald-900/60 bg-emerald-950/20 p-4">
          <p className="text-sm font-medium text-emerald-300">Текущий ролик соответствует сохранённым материалам</p>
          <a
            href={projectStage8ArtifactUrl(projectId, currentOutcome.artifact_id)}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex text-sm text-sky-400 hover:text-sky-300"
          >
            Открыть готовый ролик →
          </a>
        </div>
      )}

      {message && <p className="mt-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
    </section>
  );
}
