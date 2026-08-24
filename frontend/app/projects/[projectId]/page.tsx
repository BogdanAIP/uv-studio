'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { DubbingPrecisionPanel } from '@/components/editor/DubbingPrecisionPanel';
import { DubbingSourceSetupPanel } from '@/components/editor/DubbingSourceSetupPanel';
import { DubbingSubtitleExportPanel } from '@/components/editor/DubbingSubtitleExportPanel';
import { DubbingWorkflowPanel } from '@/components/editor/DubbingWorkflowPanel';
import { GeneralVideoPanel } from '@/components/editor/GeneralVideoPanel';
import { MusicAssemblyPanel } from '@/components/editor/MusicAssemblyPanel';
import { MusicVideoPanel } from '@/components/editor/MusicVideoPanel';
import { MusicVideoReviewPanel } from '@/components/editor/MusicVideoReviewPanel';
import { NarratedVideoPanel } from '@/components/editor/NarratedVideoPanel';
import { ProjectEditor } from '@/components/editor/ProjectEditor';
import { Stage8CompositionPanel } from '@/components/editor/Stage8CompositionPanel';
import { Stage8MediaPanel } from '@/components/editor/Stage8MediaPanel';
import {
  getProjectWorkflow,
  type ProjectWorkflowState,
} from '@/lib/productWorkflowApi';
import {
  getUVProject,
  projectArchiveUrl,
  UVProject,
} from '@/lib/projectsApi';

const readinessLabels: Record<ProjectWorkflowState['readiness'], string> = {
  ready: 'Текущая подготовка выполнена',
  setup_required: 'Есть следующий шаг',
  partial: 'Доступна только часть процесса',
  unavailable: 'Этот путь пока недоступен',
};

type JourneyNotice = {
  title: string;
  description: string;
  steps: string[];
  tone: 'ready' | 'partial' | 'neutral';
};

function journeyNotice(recipeId: string): JourneyNotice | null {
  if (recipeId === 'general_video') {
    return {
      title: 'Как получить готовый ролик',
      description: 'Это самый короткий полностью поддерживаемый путь в текущей сборке. Он собирает готовый локальный видеофайл из ваших изображений и/или видеоклипов.',
      steps: [
        'Опишите, что нужно показать.',
        'Добавьте хотя бы одно своё изображение или видео.',
        'Сохраните задачу и порядок материалов.',
        'Нажмите «Собрать обычный видеоролик».',
      ],
      tone: 'ready',
    };
  }
  if (recipeId === 'narrated_video') {
    return {
      title: 'Как получить видео с диктором',
      description: 'Этот путь можно завершить локально после подготовки текста, изображений и речевой дорожки.',
      steps: [
        'Опишите задачу и введите текст диктора.',
        'Добавьте изображения для визуального ряда.',
        'Подготовьте или импортируйте речевую дорожку.',
        'После выполнения требований соберите итоговое видео.',
      ],
      tone: 'ready',
    };
  }
  if (recipeId === 'story_video') {
    return {
      title: 'Сейчас это подготовка истории, а не генератор готового фильма',
      description: 'В текущей сборке можно сохранить идею, сценарий и свои материалы, но полного проверенного пути «идея → сцены → генерация → монтаж → финальный сюжетный ролик» ещё нет. UV Studio не будет выдавать подготовленную историю за готовое видео.',
      steps: [
        'Опишите идею истории — для старта файлы не нужны.',
        'При желании добавьте собственные референсы или готовые материалы.',
        'Сохраните подготовку проекта.',
        'Для проверки полного пути до видео сейчас используйте «Обычный видеоролик».',
      ],
      tone: 'partial',
    };
  }
  if (recipeId === 'commercial_product') {
    return {
      title: 'Сейчас это подготовка рекламного проекта',
      description: 'Можно зафиксировать задачу, сценарий и материалы продукта, но проверенного end-to-end рекламного рендера в этой сборке пока нет.',
      steps: [
        'Опишите продукт, задачу и желаемый результат.',
        'Добавьте фото или видео продукта, если его идентичность должна быть сохранена.',
        'Сохраните подготовку проекта.',
        'Финальный рекламный render/export появится только после отдельной продуктовой интеграции.',
      ],
      tone: 'partial',
    };
  }
  return null;
}

function noticeClass(tone: JourneyNotice['tone']) {
  if (tone === 'ready') return 'border-emerald-900/70 bg-emerald-950/20';
  if (tone === 'partial') return 'border-amber-900/70 bg-amber-950/20';
  return 'border-slate-800 bg-slate-900/50';
}

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  const [project, setProject] = useState<UVProject | null>(null);
  const [workflow, setWorkflow] = useState<ProjectWorkflowState | null>(null);
  const [workflowRefresh, setWorkflowRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const projectedWorkspaceIds = useMemo(
    () => new Set((workflow?.relevant_workspaces ?? []).map(workspace => workspace.workspace_id)),
    [workflow],
  );

  useEffect(() => {
    let active = true;
    Promise.all([getUVProject(projectId), getProjectWorkflow(projectId)])
      .then(([projectValue, workflowValue]) => {
        if (!active) return;
        setProject(projectValue);
        setWorkflow(workflowValue);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить проект');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const refreshProjectWorkflow = async () => {
    const [projectValue, workflowValue] = await Promise.all([
      getUVProject(projectId),
      getProjectWorkflow(projectId),
    ]);
    setProject(projectValue);
    setWorkflow(workflowValue);
  };

  const refreshMusicPrerequisites = async () => {
    await refreshProjectWorkflow();
    setWorkflowRefresh(current => current + 1);
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1600px] px-4 py-8 sm:px-6 lg:px-8">
        <Link href="/projects" className="text-sm text-sky-400 hover:text-sky-300">← Все проекты</Link>

        {error ? (
          <div className="mt-8 rounded-xl border border-red-900/70 bg-red-950/40 p-5 text-red-200">{error}</div>
        ) : !project || !workflow ? (
          <div className="mt-8 text-slate-400">Загрузка проекта…</div>
        ) : (
          <>
            <header className="mt-8 border-b border-slate-800 pb-8">
              <h1 className="text-4xl font-semibold tracking-tight">{project.title}</h1>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-300">{workflow.recipe_title}</span>
              </div>
            </header>

            {journeyNotice(project.recipe_id) && (
              <JourneyGuide notice={journeyNotice(project.recipe_id)!} />
            )}

            {projectedWorkspaceIds.has('photo_composition') && (
              <Stage8MediaPanel
                projectId={project.project_id}
                recipeId="photo_to_video"
                sources={project.sources}
                workflowAction={workflow.next_actions.find(action => action.action_id === 'compose_photos')}
                workflowPrerequisites={workflow.prerequisites}
                onProjectChanged={refreshProjectWorkflow}
              />
            )}

            {projectedWorkspaceIds.has('audio_visualizer') && (
              <Stage8MediaPanel
                projectId={project.project_id}
                recipeId="visualizer"
                sources={project.sources}
                workflowAction={workflow.next_actions.find(action => action.action_id === 'render_visualizer')}
                workflowPrerequisites={workflow.prerequisites}
                onProjectChanged={refreshProjectWorkflow}
              />
            )}

            {projectedWorkspaceIds.has('targeted_edit') && (
              <ProjectEditor
                projectId={project.project_id}
                onProjectChanged={refreshProjectWorkflow}
                orchestrated
              />
            )}

            {projectedWorkspaceIds.has('dubbing') && (
              <>
                <DubbingSourceSetupPanel
                  projectId={project.project_id}
                  sources={project.sources}
                  transcriptAction={workflow.next_actions.find(action => action.action_id === 'import_dubbing_transcript')}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <DubbingWorkflowPanel
                  key={`dubbing-${project.sources.length}-${
                    workflow.prerequisites.find(item => item.prerequisite_id === 'dubbing.transcript')?.satisfied
                      ? 'transcript-ready'
                      : 'transcript-missing'
                  }`}
                  projectId={project.project_id}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <DubbingPrecisionPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <DubbingSubtitleExportPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProjectWorkflow}
                />
              </>
            )}

            {projectedWorkspaceIds.has('story_video') && (
              <Stage8CompositionPanel
                projectId={project.project_id}
                recipeId="story_video"
                sources={project.sources}
                onProjectChanged={refreshProjectWorkflow}
              />
            )}

            {projectedWorkspaceIds.has('commercial_product') && (
              <Stage8CompositionPanel
                projectId={project.project_id}
                recipeId="commercial_product"
                sources={project.sources}
                onProjectChanged={refreshProjectWorkflow}
              />
            )}

            {projectedWorkspaceIds.has('general_video') && (
              <>
                <Stage8CompositionPanel
                  projectId={project.project_id}
                  recipeId="general_video"
                  sources={project.sources}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <GeneralVideoPanel
                  projectId={project.project_id}
                  workflowAction={workflow.next_actions.find(action => action.action_id === 'render_general')}
                  currentOutcome={workflow.current_outcome}
                  onProjectChanged={refreshProjectWorkflow}
                />
              </>
            )}

            {projectedWorkspaceIds.has('narrated_video') && (
              <>
                <Stage8CompositionPanel
                  projectId={project.project_id}
                  recipeId="narrated_video"
                  sources={project.sources}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <NarratedVideoPanel
                  projectId={project.project_id}
                  artifacts={project.artifacts}
                  workflowAction={workflow.next_actions.find(action => action.action_id === 'render_narrated')}
                  currentOutcome={workflow.current_outcome}
                  onProjectChanged={refreshProjectWorkflow}
                />
              </>
            )}

            {projectedWorkspaceIds.has('music_video') && (
              <>
                <MusicVideoPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshMusicPrerequisites}
                />
                <MusicAssemblyPanel
                  key={workflowRefresh}
                  projectId={project.project_id}
                  onProjectChanged={refreshMusicPrerequisites}
                />
                <MusicVideoReviewPanel
                  key={`review-${project.artifacts.length}`}
                  projectId={project.project_id}
                  refreshRevision={project.artifacts.length}
                  onProjectChanged={refreshMusicPrerequisites}
                />
              </>
            )}

            <section className="mb-6 mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
              <h2 className="text-xl font-medium">Что делать дальше</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{workflow.summary}</p>

              {workflow.prerequisites.length > 0 && (
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {workflow.prerequisites.map(prerequisite => (
                    <div key={prerequisite.prerequisite_id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-200">{prerequisite.title}</span>
                        <span className={`text-xs ${prerequisite.satisfied ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {prerequisite.satisfied ? 'Готово' : 'Нужно сделать'}
                        </span>
                      </div>
                      <p className="mt-2 text-xs leading-5 text-slate-500">{prerequisite.explanation}</p>
                      {prerequisite.resolution && (
                        <p className="mt-2 text-xs leading-5 text-amber-300">{prerequisite.resolution}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-5 flex items-center gap-3 text-sm">
                <span className={`rounded-full px-3 py-1 ${
                  workflow.readiness === 'ready'
                    ? 'bg-emerald-950 text-emerald-300'
                    : workflow.readiness === 'setup_required' || workflow.readiness === 'partial'
                      ? 'bg-amber-950 text-amber-300'
                      : 'bg-slate-800 text-slate-400'
                }`}>
                  {readinessLabels[workflow.readiness]}
                </span>
              </div>
            </section>

            <details className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
              <summary className="cursor-pointer text-sm font-medium text-slate-300">Проект, перенос и техническая информация</summary>
              <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <ProjectStat label="Исходники" value={project.sources.length} />
                <ProjectStat label="Результаты" value={project.artifacts.length} />
                <ProjectStat label="Создан" value={new Date(project.created_at).toLocaleDateString()} />
                <ProjectStat label="Изменён" value={new Date(project.updated_at).toLocaleDateString()} />
              </div>
              <p className="mt-4 break-all font-mono text-xs text-slate-600">ID: {project.project_id} · schema v{project.schema_version}</p>
              <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400">
                Проект можно перенести целиком в `.uvproj.zip`. Даже если выбранный тип задачи пока нельзя завершить в этой сборке, сохранённые данные остаются доступны.
              </p>
              <a
                href={projectArchiveUrl(project.project_id)}
                download={`${project.project_id}.uvproj.zip`}
                className="mt-5 inline-flex rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
              >
                Скачать архив проекта
              </a>
            </details>
          </>
        )}
      </div>
    </main>
  );
}

function JourneyGuide({ notice }: { notice: JourneyNotice }) {
  return (
    <section className={`mt-8 rounded-2xl border p-6 ${noticeClass(notice.tone)}`}>
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Маршрут проекта</p>
      <h2 className="mt-2 text-xl font-medium">{notice.title}</h2>
      <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{notice.description}</p>
      <ol className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {notice.steps.map((step, index) => (
          <li key={step} className="rounded-xl border border-slate-800/80 bg-slate-950/40 p-4 text-sm leading-6 text-slate-300">
            <span className="mb-2 block text-xs font-medium text-sky-400">{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
    </section>
  );
}

function ProjectStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-600">{label}</p>
      <p className="mt-2 text-lg font-medium text-slate-200">{value}</p>
    </div>
  );
}
