export const STUDIO_PROJECT_CHANGED_EVENT = 'uv-studio-project-changed';

export interface StudioProjectChangedDetail {
  projectId: string;
}

export function notifyStudioProjectChanged(projectId: string): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(
    new CustomEvent<StudioProjectChangedDetail>(STUDIO_PROJECT_CHANGED_EVENT, {
      detail: { projectId },
    }),
  );
}

export function subscribeStudioProjectChanged(
  projectId: string,
  listener: () => void,
): () => void {
  if (typeof window === 'undefined') return () => undefined;
  const handle = (event: Event) => {
    const detail = (event as CustomEvent<StudioProjectChangedDetail>).detail;
    if (detail?.projectId === projectId) listener();
  };
  window.addEventListener(STUDIO_PROJECT_CHANGED_EVENT, handle);
  return () => window.removeEventListener(STUDIO_PROJECT_CHANGED_EVENT, handle);
}
