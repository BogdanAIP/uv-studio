'use client';

import {
  ArrowLeft,
  Captions,
  Download,
  Film,
  Languages,
  Link2,
  Music2,
  PackageCheck,
  Sparkles,
  WandSparkles,
} from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { DubbingPrecisionPanel } from '@/components/editor/DubbingPrecisionPanel';
import { DubbingSubtitleExportPanel } from '@/components/editor/DubbingSubtitleExportPanel';
import { DubbingWorkflowPanel } from '@/components/editor/DubbingWorkflowPanel';
import { MusicAssemblyPanel } from '@/components/editor/MusicAssemblyPanel';
import { MusicVideoPanel } from '@/components/editor/MusicVideoPanel';
import { MusicVideoReviewPanel } from '@/components/editor/MusicVideoReviewPanel';
import { PerformanceLipSyncPanel } from '@/components/editor/PerformanceLipSyncPanel';
import { ProjectEditor } from '@/components/editor/ProjectEditor';
import { ProjectExportWorkspace } from '@/components/editor/ProjectExportWorkspace';
import { SequenceContinuityPanel } from '@/components/editor/SequenceContinuityPanel';
import { Stage8CompositionPanel } from '@/components/editor/Stage8CompositionPanel';
import { Stage8MediaPanel } from '@/components/editor/Stage8MediaPanel';
import {
  getProjectExecutionPlan,
  getUVProject,
  projectArchiveUrl,
  type ProjectExecutionPlan,
  type UVProject,
} from '@/lib/projectsApi';

type WorkspaceId = 'edit' | 'task' | 'dubbing' | 'continuity' | 'export';

const TASK_RECIPES = new Set([
  'music_video',
  'story_video',
  'commercial_product',
  'free_project',
  'photo_to_video',
  'visualizer',
  'performance_lip_sync',
]);

const TASK_LABELS: Record<string, string> = {
  music_video: 'Клип',
  story_video: 'История',
  commercial_product: 'Реклама',
  free_project: 'Подготовка',
  photo_to_video: 'Фото → видео',
  visualizer: 'Визуализатор',
  performance_lip_sync: 'Lip-sync',
};

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  const [project, setProject] = useState<UVProject | null>(null);
  const [executionPlan, setExecutionPlan] = useState<ProjectExecutionPlan | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceId>('edit');
  const [workflowRefresh, setWorkflowRefresh] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([getUVProject(projectId), getProjectExecutionPlan(projectId)])
      .then(([projectValue, planValue]) => {
        if (!active) return;
        setProject(projectValue);
        setExecutionPlan(planValue);
        setWorkspace(TASK_RECIPES.has(projectValue.recipe_id) ? 'task' : 'edit');
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось открыть проект');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  const refreshProject = async () => {
    const next = await getUVProject(projectId);
    setProject(next);
  };

  const refreshMusicPrerequisites = async () => {
    await refreshProject();
    setWorkflowRefresh(current => current + 1);
  };

  if (error) {
    return (
      <main className="min-h-screen p-6 sm:p-8">
        <div className="mx-auto max-w-3xl rounded-2xl border border-rose-400/20 bg-rose-400/10 p-6 text-rose-200">
          <h1 className="text-lg font-medium">Проект не открылся</h1>
          <p className="mt-2 text-sm">{error}</p>
          <Link href="/projects" className="mt-5 inline-flex items-center gap-2 text-sm text-rose-100 underline underline-offset-4">
            <ArrowLeft size={15} /> Вернуться к проектам
          </Link>
        </div>
      </main>
    );
  }

  if (!project || !executionPlan) {
    return (
      <main className="min-h-screen p-6 sm:p-8">
        <div className="mx-auto max-w-6xl animate-pulse rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-8 text-sm text-zinc-600">
          Открываем проект…
        </div>
      </main>
    );
  }

  const hasTask = TASK_RECIPES.has(project.recipe_id);
  const hasVideo = [...project.sources, ...project.artifacts].some(item => item.kind === 'video');
  const tabs: Array<{ id: WorkspaceId; label: string; icon: typeof Film }> = [
    { id: 'edit', label: 'Монтаж', icon: Film },
  ];
  if (hasTask) tabs.push({ id: 'task', label: TASK_LABELS[project.recipe_id] ?? 'Рабочий режим', icon: Sparkles });
  if (hasVideo) {
    tabs.push({ id: 'dubbing', label: 'Дубляж', icon: Languages });
    tabs.push({ id: 'continuity', label: 'Связность', icon: Link2 });
    tabs.push({ id: 'export', label: 'Экспорт', icon: PackageCheck });
  }

  if (!tabs.some(tab => tab.id === workspace)) {
    queueMicrotask(() => setWorkspace(hasTask ? 'task' : 'edit'));
  }

  return (
    <main className="min-h-screen bg-[var(--uv-bg)]">
      <header className="sticky top-0 z-30 border-b border-[var(--uv-border)] bg-[rgba(9,10,13,0.9)] px-4 backdrop-blur-xl sm:px-6">
        <div className="flex min-h-16 items-center gap-3">
          <Link
            href="/projects"
            aria-label="Все проекты"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-zinc-600 transition hover:bg-white/[0.04] hover:text-zinc-200"
          >
            <ArrowLeft size={17} />
          </Link>
          <div className="min-w-0 flex-1">
            <div className="flex min-w-0 items-center gap-2">
              <h1 className="truncate text-sm font-semibold text-zinc-100 sm:text-base">{project.title}</h1>
              <span className="hidden rounded-md border border-[var(--uv-border)] bg-[var(--uv-surface-1)] px-2 py-0.5 text-[10px] text-zinc-600 md:inline">{executionPlan.recipe_title}</span>
            </div>
            <p className="mt-0.5 text-[10px] text-zinc-700">Локальный проект · изменения сохраняются автоматически в рабочем состоянии</p>
          </div>
          <AvailabilityBadge compatibility={executionPlan.compatibility} />
          <a
            href={projectArchiveUrl(project.project_id)}
            download={`${project.project_id}.uvproj.zip`}
            title="Скачать архив проекта"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--uv-border)] bg-[var(--uv-surface-1)] text-zinc-500 transition hover:text-zinc-200"
          >
            <Download size={15} />
          </a>
        </div>

        <nav className="flex gap-1 overflow-x-auto pb-2" aria-label="Рабочие разделы проекта">
          {tabs.map(tab => {
            const Icon = tab.icon;
            const active = workspace === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                data-testid={`workspace-${tab.id}`}
                onClick={() => setWorkspace(tab.id)}
                className={`inline-flex h-9 shrink-0 items-center gap-2 rounded-lg px-3 text-xs font-medium transition ${
                  active
                    ? 'bg-violet-400/12 text-violet-200 ring-1 ring-inset ring-violet-400/20'
                    : 'text-zinc-600 hover:bg-white/[0.035] hover:text-zinc-300'
                }`}
              >
                <Icon size={14} strokeWidth={1.8} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </header>

      <div className="mx-auto max-w-[1760px] p-3 sm:p-5 lg:p-6">
        {executionPlan.compatibility !== 'available' && workspace === 'edit' && (
          <AvailabilityNotice compatibility={executionPlan.compatibility} />
        )}

        {workspace === 'edit' && (
          <ProjectEditor projectId={project.project_id} onProjectChanged={refreshProject} />
        )}

        {workspace === 'task' && hasTask && (
          <TaskWorkspace
            project={project}
            workflowRefresh={workflowRefresh}
            refreshProject={refreshProject}
            refreshMusicPrerequisites={refreshMusicPrerequisites}
          />
        )}

        {workspace === 'dubbing' && hasVideo && (
          <DubbingWorkspace projectId={project.project_id} onProjectChanged={refreshProject} />
        )}

        {workspace === 'continuity' && hasVideo && (
          <WorkspaceFrame
            eyebrow="Связанные кадры"
            title="Связность сцен"
            description="Используйте этот инструмент только там, где следующий кадр должен продолжать принятый предыдущий."
          >
            <SequenceContinuityPanel projectId={project.project_id} onProjectChanged={refreshProject} />
          </WorkspaceFrame>
        )}

        {workspace === 'export' && hasVideo && (
          <ProjectExportWorkspace
            projectId={project.project_id}
            archiveUrl={projectArchiveUrl(project.project_id)}
            onProjectChanged={refreshProject}
          />
        )}
      </div>
    </main>
  );
}

function AvailabilityBadge({ compatibility }: { compatibility: ProjectExecutionPlan['compatibility'] }) {
  if (compatibility === 'available') {
    return <span className="hidden rounded-full bg-emerald-400/10 px-2.5 py-1 text-[10px] text-emerald-300 sm:inline">Готово к работе</span>;
  }
  if (compatibility === 'partial') {
    return <span className="hidden rounded-full bg-amber-400/10 px-2.5 py-1 text-[10px] text-amber-200 sm:inline">Часть функций требует настройки</span>;
  }
  return <span className="hidden rounded-full bg-zinc-800 px-2.5 py-1 text-[10px] text-zinc-500 sm:inline">Монтаж доступен</span>;
}

function AvailabilityNotice({ compatibility }: { compatibility: ProjectExecutionPlan['compatibility'] }) {
  const partial = compatibility === 'partial';
  return (
    <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-400/15 bg-amber-400/[0.06] px-4 py-3 text-xs leading-5 text-zinc-500">
      <WandSparkles size={16} className="mt-0.5 shrink-0 text-amber-300" />
      <span>
        {partial
          ? 'Часть автоматических действий для этого типа проекта требует подключения. Монтаж, материалы и локальная работа доступны сейчас.'
          : 'Автоматическое выполнение этого шаблона пока не подключено. Можно импортировать материалы, монтировать и использовать доступные инструменты без подмены задачи другим режимом.'}
      </span>
    </div>
  );
}

function WorkspaceFrame({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-zinc-600">{eyebrow}</p>
        <h2 className="mt-2 text-xl font-medium text-zinc-100">{title}</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-500">{description}</p>
      </section>
      {children}
    </div>
  );
}

function TaskWorkspace({
  project,
  workflowRefresh,
  refreshProject,
  refreshMusicPrerequisites,
}: {
  project: UVProject;
  workflowRefresh: number;
  refreshProject: () => Promise<void>;
  refreshMusicPrerequisites: () => Promise<void>;
}) {
  const [musicSection, setMusicSection] = useState<'plan' | 'assembly' | 'review'>('plan');

  if (project.recipe_id === 'music_video') {
    return (
      <WorkspaceFrame eyebrow="Музыкальный проект" title="Музыкальный клип" description="Сначала разметьте музыку и режиссуру, затем соберите визуалы и проверьте готовый клип.">
        <div className="flex gap-1 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-1.5">
          {([
            ['plan', 'Музыка и план'],
            ['assembly', 'Сборка'],
            ['review', 'Проверка'],
          ] as const).map(([id, label]) => (
            <button key={id} type="button" onClick={() => setMusicSection(id)} className={`rounded-lg px-3 py-2 text-xs transition ${musicSection === id ? 'bg-violet-400/12 text-violet-200' : 'text-zinc-600 hover:text-zinc-300'}`}>{label}</button>
          ))}
        </div>
        {musicSection === 'plan' && <MusicVideoPanel projectId={project.project_id} onProjectChanged={refreshMusicPrerequisites} />}
        {musicSection === 'assembly' && <MusicAssemblyPanel key={workflowRefresh} projectId={project.project_id} onProjectChanged={refreshProject} />}
        {musicSection === 'review' && <MusicVideoReviewPanel key={`review-${project.artifacts.length}`} projectId={project.project_id} refreshRevision={project.artifacts.length} onProjectChanged={refreshProject} />}
      </WorkspaceFrame>
    );
  }

  if (project.recipe_id === 'story_video' || project.recipe_id === 'commercial_product' || project.recipe_id === 'free_project') {
    return (
      <WorkspaceFrame eyebrow="Подготовка" title={TASK_LABELS[project.recipe_id] ?? 'Материалы'} description="Задача и исходные материалы этого проекта. Монтаж остаётся в отдельной вкладке и использует те же данные проекта.">
        <Stage8CompositionPanel projectId={project.project_id} recipeId={project.recipe_id} sources={project.sources} onProjectChanged={refreshProject} />
      </WorkspaceFrame>
    );
  }

  if (project.recipe_id === 'photo_to_video' || project.recipe_id === 'visualizer') {
    return (
      <WorkspaceFrame eyebrow="Локальная сборка" title={TASK_LABELS[project.recipe_id]} description="Сборка выполняется локально из материалов этого проекта без обязательного внешнего сервиса.">
        <Stage8MediaPanel projectId={project.project_id} recipeId={project.recipe_id} sources={project.sources} onProjectChanged={refreshProject} />
      </WorkspaceFrame>
    );
  }

  if (project.recipe_id === 'performance_lip_sync') {
    return (
      <WorkspaceFrame eyebrow="Performance" title="Lip-sync" description="Подготовьте персонажа и речь, затем проверьте результат перед использованием.">
        <PerformanceLipSyncPanel projectId={project.project_id} sources={project.sources} onProjectChanged={refreshProject} />
      </WorkspaceFrame>
    );
  }

  return null;
}

function DubbingWorkspace({ projectId, onProjectChanged }: { projectId: string; onProjectChanged: () => Promise<void> }) {
  const [section, setSection] = useState<'main' | 'precision' | 'subtitles'>('main');
  return (
    <WorkspaceFrame eyebrow="Речь и язык" title="Дубляж" description="Распознавание, перевод, подготовленная речь и экспорт субтитров собраны в одном инструменте, но показываются по шагам.">
      <div className="flex gap-1 rounded-xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-1.5">
        <button type="button" onClick={() => setSection('main')} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${section === 'main' ? 'bg-violet-400/12 text-violet-200' : 'text-zinc-600'}`}><Languages size={14} /> Дубляж</button>
        <button type="button" onClick={() => setSection('precision')} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${section === 'precision' ? 'bg-violet-400/12 text-violet-200' : 'text-zinc-600'}`}><Sparkles size={14} /> Точность</button>
        <button type="button" onClick={() => setSection('subtitles')} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs ${section === 'subtitles' ? 'bg-violet-400/12 text-violet-200' : 'text-zinc-600'}`}><Captions size={14} /> Субтитры</button>
      </div>
      {section === 'main' && <DubbingWorkflowPanel projectId={projectId} onProjectChanged={onProjectChanged} />}
      {section === 'precision' && <DubbingPrecisionPanel projectId={projectId} onProjectChanged={onProjectChanged} />}
      {section === 'subtitles' && <DubbingSubtitleExportPanel projectId={projectId} onProjectChanged={onProjectChanged} />}
    </WorkspaceFrame>
  );
}
