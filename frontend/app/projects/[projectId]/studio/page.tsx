'use client';

import { useParams } from 'next/navigation';
import { useMemo } from 'react';
import { StudioProjectWorkspace } from '@/components/editor/StudioProjectWorkspace';

export default function StudioProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  return <StudioProjectWorkspace projectId={projectId} />;
}
