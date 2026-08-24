'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { ArrowRight, FolderOpen, Import, Plus, Wrench } from 'lucide-react';
import {
  importUVProjectArchive,
  listUVProjects,
  type UVProject,
} from '@/lib/projectsApi';
import { createStudioProject } from '@/lib/timelineApi';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function isStudioProject(project: UVProject): boolean {
  const studio = project.extensions.studio;
  return project.recipe_id === 'studio_v2'
    || (typeof studio === 'object' && studio !== null && !Array.isArray(studio));
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<UVProject[]>([]);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
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
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const normalized = title.trim();
    if (!normalized || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createStudioProject(normalized);
      setTitle('');
      router.push(`/projects/${encodeURIComponent(project.project_id)}/studio`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать Studio-проект');
      setCreating(false);
    }
  }

  async function importProject(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || importing) return;
    setImporting(true);
    setError(null);
    try {
      const project = await importUVProjectArchive(file);
      setProjects(current => [project, ...current.filter(item => item.project_id !== project.project_id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать архив проекта');
    } finally {
      setImporting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium uppercase tracking-[0.2em] text-sky-400">UV Studio</p>
            <h1 className="text-4xl font-semibold tracking-tight">Проекты</h1>
            <p className="mt-3 max-w-2xl text-slate-400">
              Один проект — одна студия: медиатека, preview, AI-инструменты и timeline. Тип ролика больше не создаёт отдельный движок или рабочее пространство.
            </p>
          </div>
          <label className={`inline-flex h-10 cursor-pointer items-center justify-center gap-2 rounded-lg border border-slate-700 px-4 text-sm text-slate-200 transition hover:border-sky-600 hover:bg-slate-900 ${importing ? 'pointer-events-none opacity-50' : ''}`}>
            <Import size={15} />
            {importing ? 'Импорт…' : 'Импортировать .uvproj.zip'}
            <input
              type="file"
              accept=".zip,.uvproj.zip,application/zip"
              className="hidden"
              onChange={importProject}
              disabled={importing}
            />
          </label>
        </div>

        <form onSubmit={createProject} className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-slate-200">
                <Plus size={16} className="text-sky-400" />
                <h2 className="text-sm font-medium">Новый Studio-проект</h2>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Никакого выбора recipe или технологии на старте. Добавьте медиа на timeline; AI-модель будет выбираться позже в конкретном инструменте.
              </p>
              <input
                value={title}
                onChange={event => setTitle(event.target.value)}
                placeholder="Название проекта"
                maxLength={500}
                autoFocus
                className="mt-4 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition placeholder:text-slate-600 focus:border-sky-500"
              />
            </div>
            <button
              type="submit"
              disabled={!title.trim() || creating}
              className="inline-flex h-12 items-center justify-center gap-2 rounded-lg bg-sky-400 px-5 font-semibold text-slate-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {creating ? 'Создание…' : 'Создать и открыть Studio'}
              {!creating && <ArrowRight size={16} />}
            </button>
          </div>
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
            <FolderOpen size={32} className="mx-auto text-slate-600" />
            <h2 className="mt-4 text-lg font-medium">Проектов пока нет</h2>
            <p className="mt-2 text-sm text-slate-500">Создайте Studio-проект выше или импортируйте переносимый архив.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map(project => {
              const studioProject = isStudioProject(project);
              return (
                <article
                  key={project.project_id}
                  className="rounded-2xl border border-slate-800 bg-slate-900/55 p-5"
                >
                  <div className="mb-5 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="truncate text-lg font-medium text-white">{project.title}</h2>
                      <p className="mt-1 truncate font-mono text-xs text-slate-600">{project.project_id}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-[10px] ${
                      studioProject
                        ? 'bg-sky-950 text-sky-300'
                        : 'bg-amber-950/70 text-amber-300'
                    }`}>
                      {studioProject ? 'Studio' : 'Старый проект'}
                    </span>
                  </div>

                  <div className="mb-5 grid grid-cols-2 gap-2 text-xs text-slate-500">
                    <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                      <span className="block text-[10px] uppercase tracking-wider text-slate-700">Медиа</span>
                      <span className="mt-1 block text-slate-300">{project.sources.length}</span>
                    </div>
                    <div className="rounded-lg bg-slate-950/50 px-3 py-2">
                      <span className="block text-[10px] uppercase tracking-wider text-slate-700">Изменён</span>
                      <span className="mt-1 block truncate text-slate-300">{formatDate(project.updated_at)}</span>
                    </div>
                  </div>

                  <Link
                    href={`/projects/${encodeURIComponent(project.project_id)}/studio`}
                    className="flex w-full items-center justify-between rounded-lg bg-sky-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-sky-300"
                  >
                    Открыть Studio <ArrowRight size={15} />
                  </Link>

                  {!studioProject && (
                    <Link
                      href={`/projects/${encodeURIComponent(project.project_id)}`}
                      className="mt-2 flex items-center justify-center gap-2 rounded-lg border border-slate-800 px-4 py-2 text-xs text-slate-500 transition hover:border-slate-600 hover:text-slate-300"
                    >
                      <Wrench size={13} /> Старый совместимый workflow
                    </Link>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
