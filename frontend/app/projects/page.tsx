'use client';

import Link from 'next/link';
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import {
  createUVProject,
  importUVProjectArchive,
  listUVProjects,
  UVProject,
} from '@/lib/projectsApi';
import { listUVRecipes, UVRecipe } from '@/lib/recipesApi';

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<UVProject[]>([]);
  const [recipes, setRecipes] = useState<UVRecipe[]>([]);
  const [selectedRecipeId, setSelectedRecipeId] = useState('');
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedRecipe = useMemo(
    () => recipes.find(recipe => recipe.recipe_id === selectedRecipeId) ?? null,
    [recipes, selectedRecipeId],
  );
  const recipeTitles = useMemo(
    () => new Map(recipes.map(recipe => [recipe.recipe_id, recipe.title])),
    [recipes],
  );

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [projectList, recipeList] = await Promise.all([listUVProjects(), listUVRecipes()]);
      setProjects(projectList);
      setRecipes(recipeList);
      setSelectedRecipeId(current => {
        if (current && recipeList.some(recipe => recipe.recipe_id === current)) return current;
        const preferred = recipeList.find(recipe => recipe.ui.featured) ?? recipeList[0];
        return preferred?.recipe_id ?? '';
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить проекты и типы задач');
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
    const normalized = title.trim();
    if (!normalized || !selectedRecipe || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createUVProject({
        title: normalized,
        recipe_id: selectedRecipe.recipe_id,
      });
      setTitle('');
      setProjects(current => [project, ...current.filter(item => item.project_id !== project.project_id)]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось создать проект');
    } finally {
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
            <p className="mt-3 max-w-2xl text-slate-400">
              Выберите задачу — студия подключит только нужные этапы. Музыка, диктор, continuity и дополнительные проверки не являются обязательными для каждого проекта.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
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
        </div>

        <form onSubmit={createProject} className="mb-8 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="mb-4">
            <p className="text-sm font-medium text-slate-200">Что нужно сделать?</p>
            <p className="mt-1 text-xs text-slate-500">Тип задачи определяет рабочий процесс, а не конкретного поставщика ИИ.</p>
          </div>

          {recipes.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {recipes.map(recipe => {
                const selected = recipe.recipe_id === selectedRecipeId;
                return (
                  <button
                    key={recipe.recipe_id}
                    type="button"
                    onClick={() => setSelectedRecipeId(recipe.recipe_id)}
                    className={`rounded-xl border p-4 text-left transition ${
                      selected
                        ? 'border-sky-500 bg-sky-500/10 ring-1 ring-sky-500/30'
                        : 'border-slate-800 bg-slate-950/60 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="font-medium text-slate-100">{recipe.title}</span>
                      {selected && <span className="text-xs text-sky-400">Выбрано</span>}
                    </div>
                    <p className="mt-2 text-xs leading-5 text-slate-500">{recipe.description}</p>
                  </button>
                );
              })}
            </div>
          ) : !loading ? (
            <div className="rounded-xl border border-amber-900/60 bg-amber-950/30 p-4 text-sm text-amber-200">
              Каталог типов задач недоступен. Создание нового проекта временно отключено.
            </div>
          ) : null}

          {selectedRecipe && (
            <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-sm text-slate-400">
              <span className="text-slate-200">Основной ввод:</span> {selectedRecipe.ui.primary_input_label}
              <span className="mx-2 text-slate-700">•</span>
              {selectedRecipe.steps.length} этапа/этапов в описании процесса
            </div>
          )}

          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <input
              value={title}
              onChange={event => setTitle(event.target.value)}
              placeholder="Название нового проекта"
              maxLength={500}
              className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none transition placeholder:text-slate-600 focus:border-sky-500"
            />
            <button
              type="submit"
              disabled={!title.trim() || !selectedRecipe || creating}
              className="rounded-lg bg-sky-500 px-5 py-3 font-medium text-slate-950 transition hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {creating ? 'Создание…' : 'Создать проект'}
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
            <h2 className="text-lg font-medium">Проектов пока нет</h2>
            <p className="mt-2 text-sm text-slate-500">Создайте новый проект или импортируйте переносимый архив `.uvproj.zip`.</p>
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
                  <span className="shrink-0 rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">
                    {recipeTitles.get(project.recipe_id) ?? project.recipe_id}
                  </span>
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
