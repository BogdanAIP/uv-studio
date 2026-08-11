'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { getUVProject, projectArchiveUrl, UVProject } from '@/lib/projectsApi';

export default function ProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  const [project, setProject] = useState<UVProject | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setProject(null);
    setError(null);
    getUVProject(projectId)
      .then(value => {
        if (active) setProject(value);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить проект');
      });
    return () => {
      active = false;
    };
  }, [projectId]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-5xl px-6 py-10">
        <Link href="/projects" className="text-sm text-sky-400 hover:text-sky-300">← Все проекты</Link>

        {error ? (
          <div className="mt-8 rounded-xl border border-red-900/70 bg-red-950/40 p-5 text-red-200">{error}</div>
        ) : !project ? (
          <div className="mt-8 text-slate-400">Загрузка проекта…</div>
        ) : (
          <>
            <header className="mt-8 border-b border-slate-800 pb-8">
              <p className="font-mono text-xs text-slate-600">{project.project_id}</p>
              <h1 className="mt-3 text-4xl font-semibold tracking-tight">{project.title}</h1>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                <span className="rounded-full bg-slate-800 px-3 py-1 text-slate-300">{project.recipe_id}</span>
                <span className="rounded-full bg-slate-900 px-3 py-1 text-slate-500">schema v{project.schema_version}</span>
              </div>
            </header>

            <section className="grid gap-4 py-8 sm:grid-cols-2 lg:grid-cols-4">
              <ProjectStat label="Источники" value={project.sources.length} />
              <ProjectStat label="Артефакты" value={project.artifacts.length} />
              <ProjectStat label="Создан" value={new Date(project.created_at).toLocaleDateString()} />
              <ProjectStat label="Изменён" value={new Date(project.updated_at).toLocaleDateString()} />
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
              <h2 className="text-lg font-medium">Рабочая область проекта</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                Канонический проект выбран по стабильному UV Studio ID. Его можно сохранить целиком в переносимый архив и восстановить на другой установке UV Studio без зависимости от старых VideoClaw session ID.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href={projectArchiveUrl(project.project_id)}
                  download={`${project.project_id}.uvproj.zip`}
                  className="rounded-lg bg-sky-500 px-4 py-2.5 text-sm font-medium text-slate-950 transition hover:bg-sky-400"
                >
                  Скачать архив проекта
                </a>
                <Link
                  href="/"
                  className="rounded-lg border border-slate-700 px-4 py-2.5 text-sm text-slate-200 transition hover:border-slate-500 hover:bg-slate-800"
                >
                  Открыть существующие производственные инструменты
                </Link>
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
