'use client';

import {
  ArrowRight,
  Film,
  FolderOpen,
  Image as ImageIcon,
  Layers3,
  Megaphone,
  Mic2,
  Music2,
  Plus,
  Sparkles,
  Upload,
  UserRound,
  type LucideIcon,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import {
  createUVProject,
  importUVProjectArchive,
  listUVProjects,
  type UVProject,
} from '@/lib/projectsApi';
import { listUVRecipes, type UVRecipe } from '@/lib/recipesApi';

const RECIPE_META: Record<string, { icon: LucideIcon; hint: string }> = {
  general_video: { icon: Film, hint: 'Универсальный монтаж и генерация' },
  narrated_video: { icon: Mic2, hint: 'Видео, построенное вокруг речи' },
  music_video: { icon: Music2, hint: 'Монтаж по музыке и ритму' },
  action_transfer: { icon: Sparkles, hint: 'Перенос движения из референса' },
  digital_human: { icon: UserRound, hint: 'Говорящий персонаж' },
  story_video: { icon: Layers3, hint: 'Сцены, история и связность' },
  commercial_product: { icon: Megaphone, hint: 'Продуктовый или рекламный ролик' },
  photo_to_video: { icon: ImageIcon, hint: 'Локальная сборка из фотографий' },
  visualizer: { icon: Music2, hint: 'Аудио с визуализатором' },
  performance_lip_sync: { icon: UserRound, hint: 'Performance и синхронизация речи' },
  free_project: { icon: FolderOpen, hint: 'Начать без заданного сценария' },
};

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return '';
  return new Intl.DateTimeFormat('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export default function ProjectsPage() {
  const router = useRouter();
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

  const orderedRecipes = useMemo(
    () => [...recipes].sort((a, b) => Number(b.ui.featured) - Number(a.ui.featured)),
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
        return recipeList.find(recipe => recipe.ui.featured)?.recipe_id ?? recipeList[0]?.recipe_id ?? '';
      });
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
    const normalized = title.trim();
    if (!normalized || !selectedRecipe || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createUVProject({
        title: normalized,
        recipe_id: selectedRecipe.recipe_id,
      });
      router.push(`/projects/${encodeURIComponent(project.project_id)}`);
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
      router.push(`/projects/${encodeURIComponent(project.project_id)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось импортировать проект');
      setImporting(false);
    }
  }

  return (
    <main className="min-h-screen px-5 py-8 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-[1480px]">
        <header className="flex flex-col gap-5 border-b border-[var(--uv-border)] pb-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-violet-300">Рабочее пространство</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-zinc-50 sm:text-4xl">Проекты</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-500">
              Создайте новый ролик, продолжите недавнюю работу или откройте переносимый проект.
            </p>
          </div>
          <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-[var(--uv-border-strong)] bg-[var(--uv-surface-1)] px-4 text-sm text-zinc-300 transition hover:border-zinc-500 hover:bg-[var(--uv-surface-2)]">
            <Upload size={16} />
            {importing ? 'Открываем…' : 'Открыть .uvproj.zip'}
            <input
              type="file"
              accept=".zip,.uvproj.zip,application/zip"
              className="hidden"
              onChange={importProject}
              disabled={importing}
            />
          </label>
        </header>

        {error && (
          <div className="mt-6 rounded-xl border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <section className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-medium text-zinc-100">Новый проект</h2>
                <p className="mt-1 text-sm text-zinc-600">Выберите тип задачи. Нужные инструменты появятся внутри проекта автоматически.</p>
              </div>
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300">
                <Plus size={18} />
              </span>
            </div>

            {orderedRecipes.length > 0 ? (
              <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {orderedRecipes.map(recipe => {
                  const selected = recipe.recipe_id === selectedRecipeId;
                  const meta = RECIPE_META[recipe.recipe_id] ?? { icon: Film, hint: recipe.description };
                  const Icon = meta.icon;
                  return (
                    <button
                      key={recipe.recipe_id}
                      type="button"
                      data-testid={`recipe-${recipe.recipe_id}`}
                      onClick={() => setSelectedRecipeId(recipe.recipe_id)}
                      className={`group rounded-xl border p-3.5 text-left transition ${
                        selected
                          ? 'border-violet-400/45 bg-violet-400/10 shadow-[0_0_0_1px_rgba(139,124,246,0.08)]'
                          : 'border-[var(--uv-border)] bg-[var(--uv-surface-1)] hover:border-[var(--uv-border-strong)] hover:bg-[var(--uv-surface-2)]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${selected ? 'bg-violet-400/15 text-violet-200' : 'bg-black/20 text-zinc-500 group-hover:text-zinc-300'}`}>
                          <Icon size={17} strokeWidth={1.7} />
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-zinc-200">{recipe.title}</p>
                          <p className="mt-0.5 truncate text-[11px] text-zinc-600">{meta.hint}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : !loading ? (
              <div className="mt-5 rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-200">
                Типы проектов сейчас недоступны. Проверьте состояние приложения в разделе «Система».
              </div>
            ) : (
              <div className="mt-5 h-28 animate-pulse rounded-xl bg-white/[0.025]" />
            )}

            <form onSubmit={createProject} className="mt-5 flex flex-col gap-3 sm:flex-row">
              <input
                value={title}
                onChange={event => setTitle(event.target.value)}
                placeholder="Название нового проекта"
                maxLength={500}
                className="min-w-0 flex-1 rounded-xl border border-[var(--uv-border)] bg-black/20 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-700 transition focus:border-violet-400/60"
              />
              <button
                type="submit"
                disabled={!title.trim() || !selectedRecipe || creating}
                className="inline-flex min-w-40 items-center justify-center gap-2 rounded-xl bg-violet-400 px-5 py-3 text-sm font-semibold text-zinc-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:bg-zinc-800 disabled:text-zinc-600"
              >
                {creating ? 'Создание…' : 'Создать проект'}
                {!creating && <ArrowRight size={16} />}
              </button>
            </form>
            {!title.trim() && (
              <p className="mt-2 text-xs text-zinc-700">Введите название — после создания проект откроется сразу.</p>
            )}
          </div>

          <div className="rounded-2xl border border-[var(--uv-border)] bg-gradient-to-b from-[var(--uv-surface-1)] to-[var(--uv-surface-0)] p-6">
            <Sparkles size={20} className="text-violet-300" />
            <h2 className="mt-4 text-lg font-medium text-zinc-100">Один проект — одно рабочее место</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-500">
              Монтаж, материалы, AI-инструменты и результат остаются внутри проекта. Специализированные возможности показываются только там, где они нужны.
            </p>
            {selectedRecipe && (
              <div className="mt-5 rounded-xl border border-[var(--uv-border)] bg-black/15 p-4">
                <p className="text-xs text-zinc-600">Выбрано</p>
                <p className="mt-1 text-sm font-medium text-zinc-200">{selectedRecipe.title}</p>
                <p className="mt-2 text-xs leading-5 text-zinc-600">{selectedRecipe.description}</p>
              </div>
            )}
          </div>
        </section>

        <section className="mt-10">
          <div className="mb-4 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-lg font-medium text-zinc-100">Недавние</h2>
              <p className="mt-1 text-sm text-zinc-600">Проекты хранятся локально на этом компьютере.</p>
            </div>
          </div>

          {loading ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map(item => <div key={item} className="h-32 animate-pulse rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)]" />)}
            </div>
          ) : projects.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[var(--uv-border-strong)] bg-[var(--uv-surface-0)] px-6 py-12 text-center">
              <FolderOpen className="mx-auto text-zinc-700" size={28} />
              <h3 className="mt-4 text-sm font-medium text-zinc-300">Здесь появятся ваши проекты</h3>
              <p className="mt-1 text-sm text-zinc-600">Создайте первый проект выше или откройте архив.</p>
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {projects.map(project => (
                <button
                  key={project.project_id}
                  type="button"
                  onClick={() => router.push(`/projects/${encodeURIComponent(project.project_id)}`)}
                  className="group rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 text-left transition hover:-translate-y-0.5 hover:border-violet-400/30 hover:bg-[var(--uv-surface-1)]"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-medium text-zinc-100">{project.title}</h3>
                      <p className="mt-1 truncate text-xs text-zinc-600">{recipeTitles.get(project.recipe_id) ?? 'Проект UV Studio'}</p>
                    </div>
                    <ArrowRight size={16} className="mt-1 shrink-0 text-zinc-700 transition group-hover:translate-x-0.5 group-hover:text-violet-300" />
                  </div>
                  <div className="mt-7 flex items-center justify-between gap-3 text-xs text-zinc-700">
                    <span>{project.sources.length} материалов · {project.artifacts.length} результатов</span>
                    <span>{formatDate(project.updated_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
