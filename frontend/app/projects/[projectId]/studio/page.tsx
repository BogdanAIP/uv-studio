'use client';

import { useParams } from 'next/navigation';
import { useMemo } from 'react';
import { StudioWorkspace } from '@/components/editor/StudioWorkspace';

export default function StudioProjectPage() {
  const params = useParams<{ projectId: string }>();
  const projectId = useMemo(() => decodeURIComponent(params.projectId), [params.projectId]);
  return <StudioWorkspace projectId={projectId} />;
}
