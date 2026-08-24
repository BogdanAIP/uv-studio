'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import {
  createCreativeProject,
  isIntentFirstProject,
} from '@/lib/creativeProjectApi';
import {
  importUVProjectArchive,
  listUVProjects,
  UVProject,
} from '@/lib/projectsApi';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function creativeGoal(project: UVProject): string | null {
  const extension = project.extensions?.creative_project;
  if (!extension || typeof extension !== 'object' || Array.isArray(extension)) return null;
  const value = (extension as Record<string, unknown>).goal;
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<UVProject[]>([]);
  const [goal, setGoal] = useState('');
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
    const timer = window.setTimeout(() => {
      void refresh();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    const normalizedGoal = goal.trim();
    if (!normalizedGoal || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createCreativeProject({
        goal: normalizedGoal,
        ...(title.trim() ? { title: title.trim() } : {}),
      });
      router.push(`/projects/${encodeURIComponent(project.project_id)}/studio`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать проект');
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
        <div className="mb-10 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium uppercase tracking-[0.2em] text-sky-400">UV Studio</p>
            <h1 className="text-4xl font-semibold tracking-tight">Проекты</h1>
            <p className="mt-3 max-w-3xl text-slate-400">
              Начните не с выбора технологии, модели или режима. Опишите результат, который хотите получить —
              UV Studio построит производственный путь из реально доступных инструментов и ваших материалов.
            </p>
          </div>
          <label className={`inline-flex h-10 cursor-pointer items-center justify-center rounded-lg border border-slate-700 px-4 text-sm text-slate-200 transition hover:border-sky-600 hover:bg-slate-900 ${importing ? 'pointer-events-none opacity-50' : ''}`}>
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

        <form onSubmit={createProject} className="mb-10 rounded-2xl border border-sky-900/70 bg-slate-900/60 p-6 shadow-2xl shadow-sky-950/10">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-sky-400">Новый проект</p>
          <h2 className="mt-2 text-2xl font-medium">Что хотите создать?</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Например: «Сделай минутный рекламный ролик про новую кофейню, уютный вечерний стиль».
            Можно начать только с идеи. Свои файлы, генераторы и параметры появятся дальше как варианты выполнения шагов, а не как условие создания проекта.
          </p>

          <textarea
            aria-label="Что хотите создать?"
            value={goal}
            onChange={event => setGoal(event.target.value)}
            rows={6}
            maxLength={20_000}
            placeholder="Опишите идею, цель, аудиторию, желаемый стиль или любые важные ограничения…"
            className="mt-5 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-base leading-7 outline-none transition placeholder:text-slate-600 focus:border-sky-500"
          />

          <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
            <label className="text-sm text-slate-400">
              Название проекта <span className="text-slate-600">· необязательно</span>
              <input
                aria-label="Название проекта"
                value={title}
                onChange={event => setTitle(event.target.value)}
                placeholder="Если оставить пустым, название возьмётся из идеи"
                maxLength={500}
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-sky-500"
              />
            </label>
            <button
              type="submit"
              disabled={!goal.trim() || creating}
              className="self-end rounded-lg bg-sky-400 px-6 py-3 font-medium text-slate-950 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {creating ? 'Создаю проект…' : 'Начать проект'}
            </button>
          </div>

          <div className="mt-5 grid gap-3 text-xs leading-5 text-slate-500 md:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <span className="block font-medium text-slate-300">1 · Замысел</span>
              Фиксируется как часть переносимого проекта, а не как временная форма интерфейса.
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <span className="block font-medium text-slate-300">2 · План</span>
              UV Studio покажет, что можно сделать локально, что требует подключения и где можно использовать свои материалы.
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
              <span className="block font-medium text-slate-300">3 · Результат</span>
              Генерация, сборка и правки остаются шагами одного проекта, а не отдельными «режимами» продукта.
            </div>
          </div>
        </form>

        {error && (
          <div className="mb-6 rounded-xl border border-red-900/70 bg-red-950/40 px-4 py-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-medium">Ваши проекты</h2>
            <p className="mt-1 text-sm text-slate-500">Новые проекты открываются в единой студии. Старые совместимые проекты остаются доступны без миграции данных.</p>
          </div>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-8 text-slate-400">Загрузка проектов…</div>
        ) : projects.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/30 p-10 text-center">
            <h3 className="text-lg font-medium">Проектов пока нет</h3>
            <p className="mt-2 text-sm text-slate-500">Опишите первую идею выше — больше ничего выбирать для старта не нужно.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects.map(project => {
              const intentFirst = isIntentFirstProject(project);
              const goalSummary = creativeGoal(project);
              const href = intentFirst
                ? `/projects/${encodeURIComponent(project.project_id)}/studio`
                : `/projects/${encodeURIComponent(project.project_id)}`;
              return (
                <Link
                  key={project.project_id}
                  href={href}
                  className="group rounded-2xl border border-slate-800 bg-slate-900/55 p-5 transition hover:-translate-y-0.5 hover:border-sky-700 hover:bg-slate-900"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate text-lg font-medium text-white">{project.title}</h3>
                      <p className="mt-1 truncate font-mono text-xs text-slate-600">{project.project_id}</p>
                    </div>
                    <span className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] ${intentFirst ? 'bg-sky-950 text-sky-300' : 'bg-slate-800 text-slate-400'}`}>
                      {intentFirst ? 'Проект по замыслу' : 'Ранее созданный'}
                    </span>
                  </div>
                  <p className="mt-4 line-clamp-3 min-h-[3.75rem] text-sm leading-5 text-slate-400">
                    {goalSummary ?? 'Совместимый проект из предыдущей структуры UV Studio.'}
                  </p>
                  <div className="mt-5 flex items-end justify-between gap-4 text-xs text-slate-500">
                    <span>Изменён: {formatDate(project.updated_at)}</span>
                    <span className="text-sky-400 opacity-0 transition group-hover:opacity-100">Открыть →</span>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
