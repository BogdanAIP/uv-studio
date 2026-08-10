'use client';

import Link from 'next/link';
import { Suspense } from 'react';
import WorkflowPanel from '@/components/WorkflowPanel';

function Loading() {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-gray-500">加载中...</p>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="relative">
      <Link
        href="/projects"
        className="fixed right-5 top-5 z-[100] rounded-lg bg-slate-950/90 px-4 py-2 text-sm font-medium text-white shadow-lg ring-1 ring-white/15 backdrop-blur transition hover:bg-slate-800"
      >
        UV Studio · Проекты
      </Link>
      <Suspense fallback={<Loading />}>
        <WorkflowPanel />
      </Suspense>
    </div>
  );
}
