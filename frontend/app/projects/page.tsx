'use client';

import Link from 'next/link';
import { FormEvent, useEffect, useState } from 'react';
import { createUVProject, listUVProjects, UVProject } from '@/lib/projectsApi';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<UVProject[]>([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      setProjects(await listUVProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить проекты');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const normalized = title.trim();
    if (!normalized || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createUVProject({ title: normalized, recipe_id: 'general_video' });
      setTitle('');
      setProjects(current => [project, ...current.filter(item => item.project_id !== project.project_id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать проект');
    } finally {
      setCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-10 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium uppercase tracking-[0.2em] text-sky-400">UV Studio</p>
            <h1 className="text-4xl font-semibold tracking-tight">Проекты</h1>
            <p className="mt-3 max-w-2xl text-slate-400">
              Канонические проекты UV Studio сохраняются отдельно от старых сессий производственного интерфейса.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-700 px-4 text-sm text-slate-200 transition hover:border-slate-500 hover:bg-slate-900"
          >
            Производственный интерфейс
          </Link>
        </div>

        <form onSubmit={createProject} className="mb-8 flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:flex-row">
          <input
            value={title}
            onChange={event => setTitle(event.target.value)}
            placeholder="Название нового проекта"
            maxLength={500}
            className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition placeholder:text-slate-600 focus:border-sky-500"
          />
          <button
            type="submit"
            disabled={!title.trim() || creating}
            className="rounded-lg bg-sky-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {creating ? 'Создание…' : 'Создать проект'}
          </button>
        </form>

        {error && (
          <div className="mb-6 rounded-xl border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-slate-400">Загрузка проектов…</div>
        ) : projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/30 p-10 text-center">
            <h2 className="text-lg font-medium">Проектов пока нет</h2>
            <p className="mt-2 text-sm text-slate-500">Создайте первый проект. Тип рабочего процесса будет развиваться через Recipe Registry на следующем этапе.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map(project => (
              <Link
                key={project.project_id}
                href={`/projects/${encodeURIComponent(project.project_id)}`}
                className="group rounded-2xl border border-slate-800 bg-slate-900/55 p-5 transition hover:-translate-y-0.5 hover:border-sky-700 hover:bg-slate-900"
              >
                <div className="mb-6 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h2 className="truncate text-lg font-medium text-white">{project.title}</h2>
                    <p className="mt-1 truncate font-mono text-xs text-slate-600">{project.project_id}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{project.recipe_id}</span>
                </div>
                <div className="flex items-end justify-between gap-4 text-xs text-slate-500">
                  <span>Изменён: {formatDate(project.updated_at)}</span>
                  <span className="text-sky-400 opacity-0 transition group-hover:opacity-100">Открыть →</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
