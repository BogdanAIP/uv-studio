'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { DubbingPrecisionPanel } from '@/components/editor/DubbingPrecisionPanel';
import { DubbingSourceSetupPanel } from '@/components/editor/DubbingSourceSetupPanel';
import { DubbingSubtitleExportPanel } from '@/components/editor/DubbingSubtitleExportPanel';
import { DubbingWorkflowPanel } from '@/components/editor/DubbingWorkflowPanel';
import { MusicAssemblyPanel } from '@/components/editor/MusicAssemblyPanel';
import { MusicVideoPanel } from '@/components/editor/MusicVideoPanel';
import { MusicVideoReviewPanel } from '@/components/editor/MusicVideoReviewPanel';
import { PerformanceLipSyncPanel } from '@/components/editor/PerformanceLipSyncPanel';
import { ProjectEditor } from '@/components/editor/ProjectEditor';
import { SequenceContinuityPanel } from '@/components/editor/SequenceContinuityPanel';
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
  ready: 'Готово к следующему действию',
  setup_required: 'Нужна подготовка',
  partial: 'Сценарий переносится в новый процесс',
  unavailable: 'Сценарий пока недоступен',
};

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
  const hasProjectedWorkspace = projectedWorkspaceIds.size > 0;

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

  const refreshProject = async () => {
    setProject(await getUVProject(projectId));
  };

  const refreshProjectWorkflow = async () => {
    const [projectValue, workflowValue] = await Promise.all([
      getUVProject(projectId),
      getProjectWorkflow(projectId),
    ]);
    setProject(projectValue);
    setWorkflow(workflowValue);
  };

  const refreshMusicPrerequisites = async () => {
    await refreshProject();
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
              <p className="font-mono text-xs text-slate-600">{project.project_id}</p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight">{project.title}</h1>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-300">{workflow.recipe_title}</span>
                <span className="rounded-full bg-slate-900 px-3 py-1 text-slate-500">schema v{project.schema_version}</span>
              </div>
            </header>

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
                  sourceCount={project.sources.filter(source => source.kind === 'video').length}
                  onProjectChanged={refreshProjectWorkflow}
                />
                <DubbingWorkflowPanel
                  key={`dubbing-sources-${project.sources.length}`}
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

            <section className="grid gap-4 py-8 sm:grid-cols-2 lg:grid-cols-4">
              <ProjectStat label="Источники" value={project.sources.length} />
              <ProjectStat label="Артефакты" value={project.artifacts.length} />
              <ProjectStat label="Создан" value={new Date(project.created_at).toLocaleDateString()} />
              <ProjectStat label="Изменён" value={new Date(project.updated_at).toLocaleDateString()} />
            </section>

            {(project.recipe_id === 'story_video' || project.recipe_id === 'commercial_product') && (
              <Stage8CompositionPanel
                projectId={project.project_id}
                recipeId={project.recipe_id}
                sources={project.sources}
                onProjectChanged={refreshProject}
              />
            )}

            {!hasProjectedWorkspace && (
              <ProjectEditor
                projectId={project.project_id}
                onProjectChanged={refreshProject}
              />
            )}

            {project.recipe_id === 'music_video' && (
              <>
                <MusicVideoPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshMusicPrerequisites}
                />
                <MusicAssemblyPanel
                  key={workflowRefresh}
                  projectId={project.project_id}
                  onProjectChanged={refreshProject}
                />
                <MusicVideoReviewPanel
                  key={`review-${project.artifacts.length}`}
                  projectId={project.project_id}
                  refreshRevision={project.artifacts.length}
                  onProjectChanged={refreshProject}
                />
              </>
            )}

            {project.recipe_id === 'performance_lip_sync' && (
              <PerformanceLipSyncPanel
                projectId={project.project_id}
                sources={project.sources}
                onProjectChanged={refreshProject}
              />
            )}

            {!hasProjectedWorkspace && (
              <>
                <SequenceContinuityPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProject}
                />

                <DubbingWorkflowPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProject}
                />

                <DubbingPrecisionPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProject}
                />

                <DubbingSubtitleExportPanel
                  projectId={project.project_id}
                  onProjectChanged={refreshProject}
                />
              </>
            )}

            <section className="mb-6 mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wider text-slate-500">Product Orchestrator</p>
                  <h2 className="mt-2 text-xl font-medium">{readinessLabels[workflow.readiness]}</h2>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs ${
                  workflow.readiness === 'ready'
                    ? 'bg-emerald-950 text-emerald-300'
                    : workflow.readiness === 'setup_required' || workflow.readiness === 'partial'
                      ? 'bg-amber-950 text-amber-300'
                      : 'bg-slate-800 text-slate-400'
                }`}>
                  {workflow.readiness}
                </span>
              </div>
              <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-400">{workflow.summary}</p>

              {workflow.prerequisites.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-sm font-medium text-slate-200">Что нужно для следующего действия</h3>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    {workflow.prerequisites.map(prerequisite => (
                      <div key={prerequisite.prerequisite_id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-sm text-slate-200">{prerequisite.title}</span>
                          <span className={`text-xs ${prerequisite.satisfied ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {prerequisite.satisfied ? 'Готово' : 'Требуется'}
                          </span>
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-500">{prerequisite.explanation}</p>
                        {prerequisite.resolution && (
                          <p className="mt-2 text-xs leading-5 text-amber-300">{prerequisite.resolution}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
              <h2 className="text-lg font-medium">Проект и восстановление</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                Проект хранится по стабильному UV Studio ID и может быть перенесён целиком в `.uvproj.zip`. Даже если тип задачи пока нельзя выполнить в этой сборке, данные проекта остаются доступными.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href={projectArchiveUrl(project.project_id)}
                  download={`${project.project_id}.uvproj.zip`}
                  className="rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
                >
                  Скачать архив проекта
                </a>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}

function ProjectStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-600">{label}</p>
      <p className="mt-2 text-lg font-medium text-slate-200">{value}</p>
    </div>
  );
}
