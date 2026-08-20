'use client';

import clsx from 'clsx';
import { FolderKanban, Settings, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const projectsActive = pathname === '/' || pathname.startsWith('/projects');
  const settingsActive = pathname.startsWith('/settings');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-40 border-b border-slate-800/90 bg-slate-950/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/projects" className="flex items-center gap-3" aria-label="UV Studio — проекты">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500 text-slate-950">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-wide text-white">UV Studio</span>
              <span className="block text-[10px] uppercase tracking-[0.18em] text-slate-500">Product workspace</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1" aria-label="Основная навигация">
            <Link
              href="/projects"
              className={clsx(
                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition',
                projectsActive
                  ? 'bg-sky-500/15 text-sky-300'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200',
              )}
            >
              <FolderKanban className="h-4 w-4" aria-hidden="true" />
              Проекты
            </Link>
            <Link
              href="/settings"
              className={clsx(
                'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition',
                settingsActive
                  ? 'bg-sky-500/15 text-sky-300'
                  : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200',
              )}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
              Настройки
            </Link>
          </nav>
        </div>
      </header>
      <main className="min-h-[calc(100vh-4rem)]">{children}</main>
    </div>
  );
}
