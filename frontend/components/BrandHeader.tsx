'use client';

import Link from 'next/link';
import { Activity, FolderKanban } from 'lucide-react';

export default function BrandHeader() {
  return (
    <>
      <header className="fixed top-0 right-0 left-[var(--app-sidebar-width)] z-30 h-14 bg-white border-b border-gray-200 flex items-center justify-between gap-4 px-4 min-w-0 transition-[left] duration-300">
        <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity flex-shrink-0">
          <img
            src="/logo.jpg"
            alt="UV Studio"
            className="w-8 h-8 rounded-lg object-contain"
          />
          <span className="font-bold text-sm text-gray-800 tracking-tight">
            UV Studio
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-xs sm:text-sm">
          <Link
            href="/projects"
            className="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-gray-500 transition hover:bg-gray-50 hover:text-gray-900"
          >
            <FolderKanban className="h-4 w-4" />
            <span className="hidden sm:inline">Проекты</span>
          </Link>
          <Link
            href="/diagnostics"
            className="inline-flex h-9 items-center gap-2 rounded-lg px-3 text-gray-500 transition hover:bg-gray-50 hover:text-gray-900"
          >
            <Activity className="h-4 w-4" />
            <span className="hidden sm:inline">Диагностика</span>
          </Link>
        </nav>
      </header>
      <div className="h-14 flex-shrink-0" />
    </>
  );
}
