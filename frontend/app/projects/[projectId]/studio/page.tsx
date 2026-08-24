'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { CreativeProjectWorkspace } from '@/components/creative/CreativeProjectWorkspace';
import {
  getCreativePlan,
  isIntentFirstProject,
  type CreativePlan,
} from '@/lib/creativeProjectApi';
import {
  getProjectWorkflow,
  type ProjectWorkflowState,
} from '@/lib/productWorkflowApi';
import {
  getUVProject,
  projectArchiveUrl,
  type UVProject,
} from '@/lib/projectsApi';

export default function CreativeStudioPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  const [project, setProject] = useState<UVProject | null>(null);
  const [plan, setPlan] = useState<CreativePlan | null>(null);
  const [workflow, setWorkflow] = useState<ProjectWorkflowState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [legacyProject, setLegacyProject] = useState(false);

  const refresh = async () => {
    setError(null);
    const projectValue = await getUVProject(projectId);
    if (!isIntentFirstProject(projectValue)) {
      setProject(projectValue);
      setLegacyProject(true);
      setPlan(null);
      setWorkflow(null);
      return;
    }
    const [planValue, workflowValue] = await Promise.all([
      getCreativePlan(projectId),
      getProjectWorkflow(projectId),
    ]);
    setProject(projectValue);
    setPlan(planValue);
    setWorkflow(workflowValue);
    setLegacyProject(false);
  };

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const projectValue = await getUVProject(projectId);
        if (!active) return;
        if (!isIntentFirstProject(projectValue)) {
          setProject(projectValue);
          setLegacyProject(true);
          return;
        }
        const [planValue, workflowValue] = await Promise.all([
          getCreativePlan(projectId),
          getProjectWorkflow(projectId),
        ]);
        if (!active) return;
        setProject(projectValue);
        setPlan(planValue);
        setWorkflow(workflowValue);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось открыть проект');
      }
    })();
    return () => {
      active = false;
    };
  }, [projectId]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-[1500px] px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href="/projects" className="text-sm text-sky-400 hover:text-sky-300">← Все проекты</Link>
          {project && (
            <a
              href={projectArchiveUrl(project.project_id)}
              download={`${project.project_id}.uvproj.zip`}
              className="text-sm text-slate-500 hover:text-slate-300"
            >
              Скачать архив проекта
            </a>
          )}
        </div>

        {error ? (
          <div className="mt-8 rounded-xl border border-red-900/70 bg-red-950/40 p-5 text-red-200">{error}</div>
        ) : !project ? (
          <div className="mt-8 text-slate-400">Открываю проект…</div>
        ) : legacyProject ? (
          <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <h1 className="text-3xl font-semibold">{project.title}</h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-400">
              Этот проект создан в предыдущей структуре UV Studio и не содержит канонического замысла нового Studio. Данные не мигрируются автоматически и не подменяются.
            </p>
            <Link
              href={`/projects/${encodeURIComponent(project.project_id)}`}
              className="mt-5 inline-flex rounded-lg bg-slate-200 px-4 py-2.5 text-sm font-medium text-slate-950"
            >
              Открыть совместимый интерфейс
            </Link>
          </section>
        ) : !plan || !workflow ? (
          <div className="mt-8 text-slate-400">Строю производственный план…</div>
        ) : (
          <>
            <header className="mt-8 border-b border-slate-800 pb-7">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-sky-400">Единый проект</p>
              <h1 className="mt-2 text-4xl font-semibold tracking-tight">{project.title}</h1>
              <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">{plan.goal}</p>
            </header>
            <CreativeProjectWorkspace
              project={project}
              plan={plan}
              workflow={workflow}
              onRefresh={refresh}
            />
          </>
        )}
      </div>
    </main>
  );
}
