'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, ChevronLeft, ChevronRight, FolderKanban, PanelLeftOpen, Settings } from 'lucide-react';
import clsx from 'clsx';
import { useEffect, useState, type CSSProperties } from 'react';

const NAV_ITEMS = [
  { href: '/projects', label: 'Проекты', icon: FolderKanban },
  { href: '/diagnostics', label: 'Диагностика', icon: Activity },
  { href: '/settings', label: 'Настройки', icon: Settings },
];

const SIDEBAR_OPEN_KEY = 'uv-studio.sidebar-open';
const LEGACY_SIDEBAR_OPEN_KEY = 'video-claw.sidebar-open';

function loadSidebarOpen(): boolean {
  if (typeof window === 'undefined') return false;
  const current = window.localStorage.getItem(SIDEBAR_OPEN_KEY);
  if (current !== null) return current === 'true';
  return window.localStorage.getItem(LEGACY_SIDEBAR_OPEN_KEY) === 'true';
}

function saveSidebarOpen(open: boolean) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SIDEBAR_OPEN_KEY, open ? 'true' : 'false');
  window.localStorage.removeItem(LEGACY_SIDEBAR_OPEN_KEY);
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(loadSidebarOpen());
  }, []);

  const setSidebarOpen = (nextOpen: boolean) => {
    setOpen(nextOpen);
    saveSidebarOpen(nextOpen);
  };

  return (
    <div
      className="min-h-screen bg-gray-50 text-gray-800"
      style={{ '--app-sidebar-width': open ? '15rem' : '0px' } as CSSProperties}
    >
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-40 border-r border-gray-200 bg-white shadow-sm transition-all duration-300',
          open ? 'w-60' : 'w-0 border-r-0'
        )}
      >
        <div className={clsx('flex h-full flex-col overflow-hidden transition-opacity duration-200', open ? 'opacity-100' : 'opacity-0')}>
          <div className="flex h-16 items-center border-b border-gray-100 px-4">
            <div className="flex min-w-0 items-center gap-2">
              <PanelLeftOpen className="h-4 w-4 flex-shrink-0 text-blue-500" />
              <span className="truncate text-sm font-semibold text-gray-800">UV Studio</span>
            </div>
          </div>
          <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-3">
            {NAV_ITEMS.map(item => {
              const Icon = item.icon;
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={clsx(
                    'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                    active
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-800'
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      {open ? (
        <button
          type="button"
          onClick={() => setSidebarOpen(false)}
          className="fixed left-60 top-1/2 z-50 flex h-14 w-7 -translate-y-1/2 items-center justify-center rounded-r-xl border border-l-0 border-gray-200 bg-white text-gray-400 shadow-sm transition-all hover:w-9 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
          title="Свернуть боковую панель"
          aria-label="Свернуть боковую панель"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="fixed left-0 top-1/2 z-50 flex h-14 w-7 -translate-y-1/2 items-center justify-center rounded-r-xl border border-l-0 border-gray-200 bg-white text-gray-400 shadow-sm transition-all hover:w-9 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
          title="Открыть боковую панель"
          aria-label="Открыть боковую панель"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      )}

      <main className={clsx('min-h-screen min-w-0 overflow-x-hidden transition-[margin] duration-300', open ? 'ml-60' : 'ml-0')}>
        {children}
      </main>
    </div>
  );
}
