'use client';

import { Loader2, RefreshCw, Sparkles, XCircle } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  authorizeGeneration,
  cancelGeneration,
  listGenerationJobs,
  listNamedModels,
  prepareGeneration,
  prepareGenerationRetry,
  retryGeneration,
  submitGeneration,
  type GenerationContract,
  type GenerationJob,
  type NamedModel,
} from '@/lib/generationApi';
import { getProductionSemantics, type ProductionSemantics } from '@/lib/productionApi';

interface GenerationWorkspacePanelProps {
  projectId: string;
  refreshRevision: number;
  onProjectChanged: () => void;
}

interface PendingConsent {
  idempotencyKey: string;
  request: {
    shot_id: string;
    model_id: string;
    inputs: Record<string, unknown>;
    contract: GenerationContract;
  };
  scopes: string[];
}

function lines(value: string): string[] {
  return Array.from(new Set(value.split('\n').map(item => item.trim()).filter(Boolean)));
}

function statusLabel(status: GenerationJob['status']): string {
  return {
    queued: 'В очереди',
    running: 'Выполняется',
    succeeded: 'Готово',
    failed: 'Ошибка',
    cancelled: 'Отменено',
  }[status];
}

function scopeLabel(scope: string): string {
  return {
    remote_execution: 'отправка данных во внешний сервис',
    external_cost: 'возможные внешние расходы',
    unknown_cost: 'стоимость заранее неизвестна',
  }[scope] ?? scope;
}

export function GenerationWorkspacePanel({
  projectId,
  refreshRevision,
  onProjectChanged,
}: GenerationWorkspacePanelProps) {
  const [production, setProduction] = useState<ProductionSemantics | null>(null);
  const [models, setModels] = useState<NamedModel[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [selectedShotId, setSelectedShotId] = useState('');
  const [selectedModelId, setSelectedModelId] = useState('');
  const [prompt, setPrompt] = useState('');
  const [fixedText, setFixedText] = useState('');
  const [editableText, setEditableText] = useState('camera\nlighting');
  const [forbiddenText, setForbiddenText] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingConsent, setPendingConsent] = useState<PendingConsent | null>(null);
  const notifiedJobs = useRef(new Set<string>());

  const load = useCallback(async () => {
    const [productionValue, modelValues, jobValues] = await Promise.all([
      getProductionSemantics(projectId),
      listNamedModels(),
      listGenerationJobs(projectId),
    ]);
    setProduction(productionValue);
    setModels(modelValues);
    setJobs(jobValues);
    setSelectedShotId(current =>
      current && productionValue.shots.some(shot => shot.shot_id === current)
        ? current
        : productionValue.shots[0]?.shot_id ?? '',
    );
    setSelectedModelId(current =>
      current && modelValues.some(model => model.model_id === current)
        ? current
        : modelValues[0]?.model_id ?? '',
    );
  }, [projectId]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void load()
        .catch(err => {
          if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить генерацию');
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [load, refreshRevision]);

  const hasActiveJobs = jobs.some(job => job.status === 'queued' || job.status === 'running');
  useEffect(() => {
    if (!hasActiveJobs) return;
    const timer = window.setInterval(() => {
      void listGenerationJobs(projectId)
        .then(nextJobs => {
          setJobs(nextJobs);
          for (const job of nextJobs) {
            if (job.status !== 'succeeded' || notifiedJobs.current.has(job.job_id)) continue;
            notifiedJobs.current.add(job.job_id);
            onProjectChanged();
          }
        })
        .catch(() => undefined);
    }, 800);
    return () => window.clearInterval(timer);
  }, [hasActiveJobs, onProjectChanged, projectId]);

  const selectedModel = useMemo(
    () => models.find(model => model.model_id === selectedModelId) ?? null,
    [models, selectedModelId],
  );
  const latestJobs = useMemo(
    () => [...jobs].sort((left, right) => right.created_at.localeCompare(left.created_at)).slice(0, 6),
    [jobs],
  );

  function requestPayload() {
    const contract: GenerationContract = {
      fixed_constraints: lines(fixedText),
      editable_variables: lines(editableText),
      forbidden_changes: lines(forbiddenText),
      approved_reference_id: null,
    };
    return {
      shot_id: selectedShotId,
      model_id: selectedModelId,
      inputs: { prompt: prompt.trim() },
      contract,
    };
  }

  async function submitPrepared(
    request: ReturnType<typeof requestPayload>,
    idempotencyKey: string,
    authorizationToken: string | null,
  ) {
    const result = await submitGeneration(projectId, {
      ...request,
      idempotency_key: idempotencyKey,
      authorization_token: authorizationToken,
    });
    setJobs(current => {
      const rest = current.filter(job => job.job_id !== result.job.job_id);
      return [...rest, result.job];
    });
    if (result.job.status === 'succeeded' && !notifiedJobs.current.has(result.job.job_id)) {
      notifiedJobs.current.add(result.job.job_id);
      onProjectChanged();
    }
  }

  async function beginGeneration() {
    if (busy || !selectedShotId || !selectedModel || !prompt.trim()) return;
    if (selectedModel.execution.availability !== 'available') {
      setError(selectedModel.execution.reason);
      return;
    }
    setBusy(true);
    setError(null);
    setPendingConsent(null);
    try {
      const request = requestPayload();
      const prepared = await prepareGeneration(projectId, request);
      const idempotencyKey = `idem_${crypto.randomUUID()}`;
      if (prepared.authorization.authorization_required) {
        setPendingConsent({
          request,
          idempotencyKey,
          scopes: prepared.authorization.consent_required,
        });
        return;
      }
      await submitPrepared(request, idempotencyKey, null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось запустить генерацию');
    } finally {
      setBusy(false);
    }
  }

  async function confirmConsent() {
    if (!pendingConsent || busy) return;
    setBusy(true);
    setError(null);
    try {
      const authorized = await authorizeGeneration(
        projectId,
        pendingConsent.request,
        pendingConsent.scopes,
      );
      await submitPrepared(
        pendingConsent.request,
        pendingConsent.idempotencyKey,
        authorized.authorization_token,
      );
      setPendingConsent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось подтвердить генерацию');
    } finally {
      setBusy(false);
    }
  }

  async function cancel(job: GenerationJob) {
    if (busy || (job.status !== 'queued' && job.status !== 'running')) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await cancelGeneration(projectId, job.job_id);
      setJobs(current => current.map(item => item.job_id === updated.job_id ? updated : item));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось отменить генерацию');
    } finally {
      setBusy(false);
    }
  }

  async function retry(job: GenerationJob) {
    if (busy || job.status !== 'failed') return;
    setBusy(true);
    setError(null);
    try {
      const prepared = await prepareGenerationRetry(projectId, job.job_id);
      let token: string | null = null;
      if (prepared.authorization.authorization_required) {
        const request = {
          shot_id: job.request.shot_id,
          model_id: job.request.model_id,
          inputs: job.request.inputs,
          contract: job.request.generation_contract,
        };
        const authorized = await authorizeGeneration(
          projectId,
          request,
          prepared.authorization.consent_required,
        );
        token = authorized.authorization_token;
      }
      await retryGeneration(projectId, job.job_id, token);
      const nextJobs = await listGenerationJobs(projectId);
      setJobs(nextJobs);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось повторить генерацию');
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
        <p className="flex items-center gap-2 text-xs text-slate-500">
          <Loader2 size={14} className="animate-spin" /> Загружаем модели и задания…
        </p>
      </section>
    );
  }

  return (
    <section className="mt-3 rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-slate-500">
            <Sparkles size={15} className="text-violet-300" /> Генерация
          </p>
          <h3 className="mt-2 text-sm font-semibold text-slate-200">Named model → Job → новый дубль</h3>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
            Модель выбирается явно. Результат сначала становится артефактом проекта и кандидатом Take;
            в Timeline он попадёт только после обычного «Принять в Timeline» выше.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={busy}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-[10px] text-slate-400 disabled:opacity-40"
        >
          <RefreshCw size={11} /> Обновить
        </button>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[1fr_1fr_1.4fr]">
        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <label className="text-[10px] uppercase tracking-[0.14em] text-slate-600" htmlFor="generation-shot">
            Кадр
          </label>
          <select
            id="generation-shot"
            aria-label="Кадр для генерации"
            value={selectedShotId}
            onChange={event => setSelectedShotId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          >
            <option value="">Выберите кадр</option>
            {production?.shots.map(shot => (
              <option key={shot.shot_id} value={shot.shot_id}>{shot.intent}</option>
            ))}
          </select>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <label className="text-[10px] uppercase tracking-[0.14em] text-slate-600" htmlFor="generation-model">
            Модель
          </label>
          <select
            id="generation-model"
            aria-label="Модель генерации"
            value={selectedModelId}
            onChange={event => setSelectedModelId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          >
            <option value="">Выберите модель</option>
            {models.map(model => (
              <option key={model.model_id} value={model.model_id}>{model.title}</option>
            ))}
          </select>
          {selectedModel ? (
            <div className="mt-2 text-[10px] leading-4 text-slate-600">
              <p>{selectedModel.model_id}</p>
              <p className={selectedModel.execution.availability === 'available' ? 'text-emerald-400' : 'text-amber-400'}>
                {selectedModel.execution.availability === 'available'
                  ? `${selectedModel.execution.locality} · ${selectedModel.execution.cost_class}`
                  : selectedModel.execution.reason}
              </p>
            </div>
          ) : null}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <label className="text-[10px] uppercase tracking-[0.14em] text-slate-600" htmlFor="generation-prompt">
            Запрос
          </label>
          <textarea
            id="generation-prompt"
            aria-label="Запрос для генерации"
            value={prompt}
            onChange={event => setPrompt(event.target.value)}
            rows={3}
            placeholder="Что должно быть в этом кадре?"
            className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          />
        </div>
      </div>

      <details className="mt-3 rounded-xl border border-slate-800 bg-slate-950/35 p-3">
        <summary className="cursor-pointer text-xs text-slate-400">Generation Contract</summary>
        <p className="mt-1 text-[10px] leading-4 text-slate-600">
          Эти ограничения принадлежат UV Studio. Provider-specific prompt не становится источником истины.
        </p>
        <div className="mt-2 grid gap-2 lg:grid-cols-3">
          <textarea
            aria-label="Фиксированные ограничения генерации"
            value={fixedText}
            onChange={event => setFixedText(event.target.value)}
            rows={3}
            placeholder="Неизменяемые факты — по одному на строку"
            className="resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          />
          <textarea
            aria-label="Изменяемые параметры генерации"
            value={editableText}
            onChange={event => setEditableText(event.target.value)}
            rows={3}
            placeholder="Что модели можно менять"
            className="resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          />
          <textarea
            aria-label="Запрещённые изменения генерации"
            value={forbiddenText}
            onChange={event => setForbiddenText(event.target.value)}
            rows={3}
            placeholder="Что менять запрещено"
            className="resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-600"
          />
        </div>
      </details>

      {pendingConsent ? (
        <div className="mt-3 rounded-xl border border-amber-800/70 bg-amber-950/25 p-3">
          <p className="text-xs font-medium text-amber-200">Нужно явное подтверждение запуска</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-[11px] text-amber-300/80">
            {pendingConsent.scopes.map(scope => <li key={scope}>{scopeLabel(scope)}</li>)}
          </ul>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => void confirmConsent()}
              disabled={busy}
              className="rounded-lg bg-amber-300 px-3 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
            >
              Подтвердить и запустить
            </button>
            <button
              type="button"
              onClick={() => setPendingConsent(null)}
              disabled={busy}
              className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-400 disabled:opacity-40"
            >
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => void beginGeneration()}
          disabled={
            busy
            || !selectedShotId
            || !selectedModel
            || selectedModel.execution.availability !== 'available'
            || !prompt.trim()
          }
          className="mt-3 inline-flex items-center justify-center gap-2 rounded-lg bg-violet-400 px-4 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
          Сгенерировать дубль
        </button>
      )}

      {error ? (
        <div className="mt-3 rounded-lg border border-red-900/70 bg-red-950/30 px-3 py-2 text-xs text-red-200">
          {error}
        </div>
      ) : null}

      <div className="mt-4 border-t border-slate-800 pt-3">
        <p className="text-xs font-medium text-slate-300">Последние задания</p>
        {latestJobs.length === 0 ? (
          <p className="mt-2 text-[11px] text-slate-600">Генераций в этом проекте ещё не было.</p>
        ) : (
          <div className="mt-2 space-y-2">
            {latestJobs.map(job => {
              const attempt = job.attempts.at(-1) ?? null;
              return (
                <div key={job.job_id} className="rounded-lg border border-slate-800 bg-slate-950/45 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-xs text-slate-300">
                        {job.request.model_id} · {job.request.shot_id}
                      </p>
                      <p className="mt-1 font-mono text-[9px] text-slate-700">{job.job_id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] ${
                        job.status === 'succeeded' ? 'text-emerald-300'
                          : job.status === 'failed' ? 'text-red-300'
                            : job.status === 'cancelled' ? 'text-slate-500'
                              : 'text-violet-300'
                      }`}>
                        {statusLabel(job.status)}
                      </span>
                      {(job.status === 'queued' || job.status === 'running') ? (
                        <button
                          type="button"
                          aria-label={`Отменить генерацию ${job.job_id}`}
                          onClick={() => void cancel(job)}
                          disabled={busy}
                          className="text-slate-600 hover:text-red-300 disabled:opacity-40"
                        >
                          <XCircle size={13} />
                        </button>
                      ) : null}
                      {job.status === 'failed' ? (
                        <button
                          type="button"
                          onClick={() => void retry(job)}
                          disabled={busy}
                          className="rounded border border-slate-700 px-2 py-1 text-[10px] text-slate-400 disabled:opacity-40"
                        >
                          Повторить
                        </button>
                      ) : null}
                    </div>
                  </div>
                  {attempt?.error ? <p className="mt-2 text-[10px] text-red-300/80">{attempt.error}</p> : null}
                  {attempt?.take_id ? (
                    <p className="mt-2 text-[10px] text-emerald-300/80">
                      Новый Take: <span className="font-mono">{attempt.take_id}</span>. Примите его в Production выше, когда он подходит.
                    </p>
                  ) : null}
                  {job.attempts.length > 1 ? (
                    <p className="mt-1 text-[9px] text-slate-600">Попыток выполнения: {job.attempts.length}</p>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
