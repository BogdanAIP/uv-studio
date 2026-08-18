'use client';

import clsx from 'clsx';
import {
  Activity,
  FolderKanban,
  Settings,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { CSSProperties } from 'react';

const PRIMARY_NAV = [
  { href: '/projects', label: 'Проекты', icon: FolderKanban },
  { href: '/settings', label: 'Настройки', icon: SlidersHorizontal },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const compact = /^\/projects\/[^/]+/.test(pathname);
  const sidebarWidth = compact ? '4.5rem' : '13.5rem';

  return (
    <div
      className="min-h-screen bg-[var(--uv-bg)] text-zinc-100"
      style={{ '--app-sidebar-width': sidebarWidth } as CSSProperties}
    >
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-[var(--uv-border)] bg-[rgba(13,15,19,0.96)] backdrop-blur-xl',
          compact ? 'w-[4.5rem]' : 'w-[13.5rem]',
        )}
      >
        <Link
          href="/projects"
          className={clsx(
            'flex h-16 items-center border-b border-[var(--uv-border)] transition hover:bg-white/[0.025]',
            compact ? 'justify-center px-3' : 'gap-3 px-4',
          )}
          aria-label="UV Studio — проекты"
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-violet-400/20 bg-violet-400/10 text-violet-300 shadow-[0_0_24px_rgba(139,124,246,0.08)]">
            <Sparkles size={18} strokeWidth={1.8} />
          </span>
          {!compact && (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight text-zinc-100">UV Studio</p>
              <p className="truncate text-[10px] text-zinc-600">Creative workspace</p>
            </div>
          )}
        </Link>

        <nav className="flex flex-1 flex-col gap-1 p-2.5">
          {PRIMARY_NAV.map(item => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                title={compact ? item.label : undefined}
                aria-label={item.label}
                className={clsx(
                  'group flex h-11 items-center rounded-xl text-sm transition',
                  compact ? 'justify-center px-2' : 'gap-3 px-3',
                  active
                    ? 'bg-violet-400/10 text-violet-200 ring-1 ring-inset ring-violet-400/15'
                    : 'text-zinc-500 hover:bg-white/[0.035] hover:text-zinc-200',
                )}
              >
                <Icon size={18} strokeWidth={1.7} className="shrink-0" />
                {!compact && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-[var(--uv-border)] p-2.5">
          <Link
            href="/diagnostics"
            title={compact ? 'Система' : undefined}
            aria-label="Система"
            className={clsx(
              'flex h-11 items-center rounded-xl text-sm text-zinc-600 transition hover:bg-white/[0.035] hover:text-zinc-300',
              compact ? 'justify-center px-2' : 'gap-3 px-3',
              pathname.startsWith('/diagnostics') && 'bg-white/[0.045] text-zinc-300',
            )}
          >
            <Activity size={18} strokeWidth={1.7} className="shrink-0" />
            {!compact && <span>Система</span>}
          </Link>
          {!compact && (
            <div className="mt-2 flex items-center gap-2 px-3 py-2 text-[10px] text-zinc-700">
              <Settings size={12} />
              <span>Локальное приложение</span>
            </div>
          )}
        </div>
      </aside>

      <main
        className="min-h-screen min-w-0 transition-[margin] duration-200"
        style={{ marginLeft: sidebarWidth }}
      >
        {children}
      </main>
    </div>
  );
}
