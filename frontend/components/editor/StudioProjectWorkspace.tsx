'use client';

import { useCallback, useEffect, useState } from 'react';
import { ProductionWorkspacePanel } from '@/components/editor/ProductionWorkspacePanel';
import { StudioWorkspace } from '@/components/editor/StudioWorkspace';
import { subscribeStudioProjectChanged } from '@/lib/projectEvents';

export function StudioProjectWorkspace({ projectId }: { projectId: string }) {
  const [revision, setRevision] = useState(0);
  const markChanged = useCallback(() => setRevision(current => current + 1), []);

  useEffect(() => subscribeStudioProjectChanged(projectId, markChanged), [markChanged, projectId]);

  return (
    <>
      <ProductionWorkspacePanel
        projectId={projectId}
        refreshRevision={revision}
        onProjectChanged={markChanged}
      />
      <StudioWorkspace key={`${projectId}:${revision}`} projectId={projectId} />
    </>
  );
}
