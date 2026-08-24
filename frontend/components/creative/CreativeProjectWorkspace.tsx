'use client';

import { useEffect, useMemo, useState } from 'react';
import { GeneralVideoPanel } from '@/components/editor/GeneralVideoPanel';
import {
  CreativePhase,
  CreativePlan,
  CreativeRoute,
  saveCreativePreparation,
} from '@/lib/creativeProjectApi';
import { uploadProjectSource } from '@/lib/editorApi';
import type { ProjectWorkflowState } from '@/lib/productWorkflowApi';
import type { ProjectReference, UVProject } from '@/lib/projectsApi';
import {
  uploadProjectImageSource,
  uploadStage8AudioSource,
} from '@/lib/stage8MediaApi';

interface CreativeProjectWorkspaceProps {
  project: UVProject;
  plan: CreativePlan;
  workflow: ProjectWorkflowState;
  onRefresh: () => Promise<void>;
}

function sourceName(source: ProjectReference): string {
  const original = source.metadata.original_name;
  return typeof original === 'string' && original
    ? original
    : source.path.split('/').pop() || source.id;
}

function routeStatus(route: CreativeRoute): string {
  if (route.state === 'ready') {
    if (route.route_class === 'local_free') return 'Локально · бесплатно';
    if (route.route_class === 'local_input' || route.route_class === 'manual') return 'Можно сейчас';
    if (route.may_cost_money) return 'Исполнитель найден · возможна оплата';
    if (route.has_external) return 'Внешний исполнитель найден';
    return 'Исполнитель найден';
  }
  if (route.state === 'needs_connection') return 'Нужно подключить';
  if (route.state === 'blocked') return 'Сначала предыдущие шаги';
  return 'Нет рабочего исполнителя';
}

function routeClass(route: CreativeRoute): string {
  if (route.state === 'ready') {
    return route.may_cost_money
      ? 'border-amber-900/70 bg-amber-950/20 text-amber-200'
      : 'border-emerald-900/60 bg-emerald-950/20 text-emerald-200';
  }
  if (route.state === 'needs_connection') {
    return 'border-sky-900/60 bg-sky-950/20 text-sky-200';
  }
  return 'border-slate-800 bg-slate-950/50 text-slate-400';
}

function phaseBadge(phase: CreativePhase): string {
  if (phase.state === 'complete') return 'Готово';
  if (phase.state === 'actionable') return 'Можно продолжать';
  if (phase.state === 'optional') return 'Необязательно';
  if (phase.state === 'blocked') return 'Ожидает';
  return 'Позже';
}

function isDirectlyUsableRoute(route: CreativeRoute) {
  return route.route_class === 'manual' || route.route_class === 'local_input' || route.route_class === 'local_free';
}

export function CreativeProjectWorkspace({
  project,
  plan,
  workflow,
  onRefresh,
}: CreativeProjectWorkspaceProps) {
  const [goal, setGoal] = useState(plan.goal);
  const [script, setScript] = useState(plan.script);
  const [selectedIds, setSelectedIds] = useState<string[]>(plan.material_source_ids);
  const [sources, setSources] = useState<ProjectReference[]>(project.sources);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setGoal(plan.goal);
    setScript(plan.script);
    setSelectedIds(plan.material_source_ids);
    setSources(project.sources);
  }, [plan, project.sources]);

  const sourceById = useMemo(() => new Map(sources.map(source => [source.id, source])), [sources]);
  const materialSources = useMemo(
    () => sources.filter(source => source.kind === 'image' || source.kind === 'video' || source.kind === 'audio'),
    [sources],
  );
  const orderedVisualIds = selectedIds.filter(id => {
    const kind = sourceById.get(id)?.kind;
    return kind === 'image' || kind === 'video';
  });

  const addUploadedSource = (source: ProjectReference) => {
    setSources(current => [...current.filter(item => item.id !== source.id), source]);
    setSelectedIds(current => {
      if (source.kind === 'audio') {
        const withoutAudio = current.filter(id => sourceById.get(id)?.kind !== 'audio');
        return [...withoutAudio, source.id];
      }
      return current.includes(source.id) ? current : [...current, source.id];
    });
  };

  const upload = async (kind: 'image' | 'video' | 'audio', file: File | undefined) => {
    if (!file || busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const source = kind === 'image'
        ? await uploadProjectImageSource(project.project_id, file)
        : kind === 'audio'
          ? await uploadStage8AudioSource(project.project_id, file)
          : await uploadProjectSource(project.project_id, file);
      addUploadedSource(source);
      setMessage(`${sourceName(source)} добавлен в материалы проекта. Сохраните подготовку, чтобы использовать его в черновике.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось добавить материал');
    } finally {
      setBusy(false);
    }
  };

  const toggleSource = (source: ProjectReference) => {
    setSelectedIds(current => {
      if (current.includes(source.id)) return current.filter(id => id !== source.id);
      if (source.kind === 'audio') {
        return [...current.filter(id => sourceById.get(id)?.kind !== 'audio'), source.id];
      }
      return [...current, source.id];
    });
  };

  const moveVisual = (sourceId: string, offset: -1 | 1) => {
    setSelectedIds(current => {
      const visualIds = current.filter(id => {
        const kind = sourceById.get(id)?.kind;
        return kind === 'image' || kind === 'video';
      });
      const index = visualIds.indexOf(sourceId);
      const target = index + offset;
      if (index < 0 || target < 0 || target >= visualIds.length) return current;
      const swapped = [...visualIds];
      [swapped[index], swapped[target]] = [swapped[target], swapped[index]];
      let visualIndex = 0;
      return current.map(id => {
        const kind = sourceById.get(id)?.kind;
        if (kind !== 'image' && kind !== 'video') return id;
        const replacement = swapped[visualIndex];
        visualIndex += 1;
        return replacement;
      });
    });
  };

  const savePreparation = async () => {
    if (!goal.trim() || busy) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await saveCreativePreparation(project.project_id, {
        goal: goal.trim(),
        script,
        source_ids: selectedIds,
      });
      setMessage('Замысел, план и выбранные материалы сохранены как одно состояние проекта.');
      await onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось сохранить проект');
    } finally {
      setBusy(false);
    }
  };

  const renderAction = workflow.next_actions.find(action => action.action_id === 'render_general');

  return (
    <div className="mt-8">
      <section className="rounded-2xl border border-sky-900/70 bg-sky-950/20 p-6">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-sky-400">Следующий шаг</p>
        <h2 className="mt-2 text-xl font-medium">{plan.next_step}</h2>
        <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">
          План ниже строится из текущего состояния проекта и реально зарегистрированных возможностей. UV Studio не выбирает провайдера или платный сервис скрыто.
        </p>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">1 · Замысел и план</p>
            <h2 className="mt-2 text-xl font-medium">Что именно делаем</h2>
          </div>
          <button
            type="button"
            disabled={busy || !goal.trim()}
            onClick={() => void savePreparation()}
            className="rounded-lg bg-sky-400 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-300 disabled:opacity-40"
          >
            {busy ? 'Сохраняю…' : 'Сохранить подготовку'}
          </button>
        </div>

        <label className="mt-5 block text-sm text-slate-300">
          Замысел / результат
          <textarea
            aria-label="Замысел проекта"
            value={goal}
            onChange={event => setGoal(event.target.value)}
            rows={5}
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 leading-6 outline-none focus:border-sky-500"
          />
        </label>
        <label className="mt-4 block text-sm text-slate-300">
          Сценарий, план сцен или рабочие заметки <span className="text-slate-600">· можно дополнять постепенно</span>
          <textarea
            aria-label="Сценарий и план"
            value={script}
            onChange={event => setScript(event.target.value)}
            rows={8}
            placeholder="Напишите план вручную. Когда появится реально исполняемый text.generate, UV Studio сможет предложить помощь ИИ на этом же шаге."
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 leading-6 outline-none placeholder:text-slate-600 focus:border-sky-500"
          />
        </label>
      </section>

      <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">2 · Материалы</p>
        <h2 className="mt-2 text-xl font-medium">Из чего будет состоять ролик</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
          Собственные файлы — один из маршрутов, а не условие создания проекта. Когда для генерации появится реально исполняемый capability, он займёт соседний маршрут в этом же шаге.
        </p>

        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
            <span className="block font-medium">Добавить изображение</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Фото, иллюстрация, референс или готовый кадр.</span>
            <input aria-label="Добавить изображение" type="file" accept="image/*" disabled={busy} onChange={event => void upload('image', event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
          </label>
          <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
            <span className="block font-medium">Добавить видео</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Готовый клип или снятый материал.</span>
            <input aria-label="Добавить видео" type="file" accept="video/*" disabled={busy} onChange={event => void upload('video', event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
          </label>
          <label className="rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
            <span className="block font-medium">Добавить аудио</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Необязательно. Для первого черновика используется не более одной дорожки.</span>
            <input aria-label="Добавить аудио" type="file" accept="audio/*" disabled={busy} onChange={event => void upload('audio', event.target.files?.[0])} className="mt-3 block w-full text-xs text-slate-400" />
          </label>
        </div>

        {materialSources.length > 0 && (
          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {materialSources.map(source => {
              const selected = selectedIds.includes(source.id);
              return (
                <label key={source.id} className={`rounded-xl border p-4 text-sm ${selected ? 'border-sky-800 bg-sky-950/20' : 'border-slate-800 bg-slate-950/40'}`}>
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSource(source)}
                      aria-label={`Использовать ${sourceName(source)}`}
                      className="mt-1"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-slate-200">{sourceName(source)}</p>
                      <p className="mt-1 text-xs text-slate-500">{source.kind}</p>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        )}

        {orderedVisualIds.length > 1 && (
          <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
            <p className="text-sm font-medium text-slate-200">Порядок первого черновика</p>
            <div className="mt-3 space-y-2">
              {orderedVisualIds.map((id, index) => {
                const source = sourceById.get(id);
                if (!source) return null;
                return (
                  <div key={id} className="flex items-center gap-3 rounded-lg border border-slate-800 px-3 py-2 text-sm">
                    <span className="w-6 text-slate-600">{index + 1}</span>
                    <span className="min-w-0 flex-1 truncate text-slate-300">{sourceName(source)}</span>
                    <button type="button" disabled={index === 0} onClick={() => moveVisual(id, -1)} className="text-slate-400 disabled:opacity-20">↑</button>
                    <button type="button" disabled={index === orderedVisualIds.length - 1} onClick={() => moveVisual(id, 1)} className="text-slate-400 disabled:opacity-20">↓</button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </section>

      <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">3 · Пути выполнения</p>
        <h2 className="mt-2 text-xl font-medium">Что UV Studio реально может сделать сейчас</h2>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {plan.phases.filter(phase => phase.phase_id === 'plan' || phase.phase_id === 'visuals' || phase.phase_id === 'audio').map(phase => (
            <div key={phase.phase_id} className="rounded-xl border border-slate-800 bg-slate-950/35 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-medium text-slate-200">{phase.title}</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{phase.summary}</p>
                </div>
                <span className="shrink-0 rounded-full bg-slate-800 px-2.5 py-1 text-[11px] text-slate-400">{phaseBadge(phase)}</span>
              </div>
              <div className="mt-4 space-y-2">
                {phase.routes.map(route => (
                  <div key={route.route_id} className={`rounded-lg border p-3 ${routeClass(route)}`}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-medium">{route.title}</span>
                      <span className="text-[11px] opacity-80">{routeStatus(route)}</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 opacity-70">{route.reason}</p>
                    {route.state === 'ready' && route.capability_id && !isDirectlyUsableRoute(route) && (
                      <p className="mt-2 text-[11px] leading-5 text-slate-500">
                        Исполнитель зарегистрирован, но Studio пока не имеет стандартного входного контракта для запуска этого генеративного шага. Он не будет запускаться скрыто или с произвольными параметрами.
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6">
        <div className="mb-3">
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">4 · Сборка</p>
          <h2 className="mt-2 text-xl font-medium">Первый ролик</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
            После сохранения хотя бы одного выбранного изображения или видео UV Studio использует проверенную локальную сборку. Это внутренний execution path, а не отдельный тип проекта.
          </p>
        </div>
        <GeneralVideoPanel
          projectId={project.project_id}
          workflowAction={renderAction}
          currentOutcome={workflow.current_outcome}
          onProjectChanged={onRefresh}
        />
      </section>

      <section className="mb-8 mt-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">5 · Просмотр и правки</p>
        <h2 className="mt-2 text-xl font-medium">Меняйте проект, а не режим</h2>
        <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
          После первой сборки можно менять замысел, текст, набор и порядок материалов и собирать следующую ревизию. Специализированные инструменты редактирования будут подключаться к этому же проекту по необходимости.
        </p>
      </section>

      {message && <p className="mb-4 text-sm text-emerald-300">{message}</p>}
      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}
    </div>
  );
}
