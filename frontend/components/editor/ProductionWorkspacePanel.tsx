'use client';

import { Loader2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ProductionSemanticsPanel } from '@/components/editor/ProductionSemanticsPanel';
import { getUVProject, type UVProject } from '@/lib/projectsApi';
import {
  getProjectHistory,
  getStudioTimeline,
  type ProjectHistoryState,
  type StudioTimeline,
} from '@/lib/timelineApi';

function timelineEnd(timeline: StudioTimeline): number {
  return timeline.tracks.reduce(
    (maximum, track) => Math.max(
      maximum,
      ...track.clips.map(clip => clip.timeline_start_us + clip.duration_us),
      0,
    ),
    0,
  );
}

interface ProductionWorkspacePanelProps {
  projectId: string;
  refreshRevision: number;
  onProjectChanged: () => void;
}

export function ProductionWorkspacePanel({
  projectId,
  refreshRevision,
  onProjectChanged,
}: ProductionWorkspacePanelProps) {
  const [project, setProject] = useState<UVProject | null>(null);
  const [timeline, setTimeline] = useState<StudioTimeline | null>(null);
  const [history, setHistory] = useState<ProjectHistoryState | null>(null);
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [projectValue, timelineValue, historyValue] = await Promise.all([
      getUVProject(projectId),
      getStudioTimeline(projectId),
      getProjectHistory(projectId),
    ]);
    setProject(projectValue);
    setTimeline(timelineValue);
    setHistory(historyValue);
    const visualSources = projectValue.sources.filter(
      source => source.kind === 'video' || source.kind === 'image',
    );
    setSelectedSourceId(current =>
      current && visualSources.some(source => source.id === current)
        ? current
        : visualSources[0]?.id ?? '',
    );
  }, [projectId]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void refresh()
        .catch(err => {
          if (active) setError(err instanceof Error ? err.message : 'Не удалось загрузить Production');
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [refresh, refreshRevision]);

  const visualSources = useMemo(
    () => project?.sources.filter(source => source.kind === 'video' || source.kind === 'image') ?? [],
    [project],
  );
  const selectedSource = useMemo(
    () => visualSources.find(source => source.id === selectedSourceId) ?? null,
    [selectedSourceId, visualSources],
  );

  const handleProjectChanged = useCallback(async () => {
    await refresh();
    onProjectChanged();
  }, [onProjectChanged, refresh]);

  if (loading) {
    return (
      <div className="bg-slate-950 px-3 pt-4 text-slate-100 sm:px-5">
        <div className="mx-auto max-w-[1800px] rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Loader2 size={15} className="animate-spin" /> Загружаем Production…
          </div>
        </div>
      </div>
    );
  }

  if (!project || !timeline || !history || project.product_identity.kind !== 'modern_direction') {
    if (!error) return null;
    return (
      <div className="bg-slate-950 px-3 pt-4 text-slate-100 sm:px-5">
        <div className="mx-auto max-w-[1800px] rounded-xl border border-red-900/70 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-950 px-3 pt-4 text-slate-100 sm:px-5">
      <div className="mx-auto max-w-[1800px]">
        <div className="mb-2 flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/45 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-600">Материал для дубля</p>
            <p className="mt-0.5 text-xs text-slate-500">
              Выберите уже импортированное видео или изображение. Импорт новых файлов остаётся в общем Media Bin ниже.
            </p>
          </div>
          <select
            aria-label="Медиа для production-дубля"
            value={selectedSourceId}
            onChange={event => setSelectedSourceId(event.target.value)}
            className="min-w-64 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-sky-500"
          >
            <option value="">Медиа не выбрано</option>
            {visualSources.map(source => {
              const originalName = source.metadata.original_name;
              const label = typeof originalName === 'string' && originalName.trim()
                ? originalName
                : source.id;
              return <option key={source.id} value={source.id}>{label}</option>;
            })}
          </select>
        </div>

        <ProductionSemanticsPanel
          projectId={projectId}
          project={project}
          selectedSource={selectedSource}
          timelineDurationUs={timelineEnd(timeline)}
          historyCursor={history.cursor}
          onProjectChanged={handleProjectChanged}
        />
      </div>
    </div>
  );
}
