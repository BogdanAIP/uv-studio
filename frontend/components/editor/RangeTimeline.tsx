'use client';

/*
 * Interaction structure is selectively adapted from OpenCut Classic timeline
 * components (ruler/playhead/snap separation and visible-tick buffering) at
 * cf5e79e919144200294fb9fed22a222592a0aeea (MIT).
 * OpenCut persistence/editor stores are deliberately not used. UV Project Store
 * and the UV Command API remain authoritative. See third_party/opencut-classic/LICENSE.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { AcceptedRangeEdit, RangeContinuityBrief } from '@/lib/editorApi';
import {
  formatRulerLabel,
  formatTimelineTime,
  getTimelineRulerConfig,
  MAX_TIMELINE_ZOOM,
  MIN_TIMELINE_ZOOM,
  pixelsPerSecond,
  pixelsToTimeUs,
  snapTimelineTime,
  timeUsToPixels,
} from '@/lib/timelineMath';

export interface TimelineSelection {
  startUs: number;
  endUs: number;
}

interface RangeTimelineProps {
  durationUs: number;
  sourceName: string;
  sourcePath: string;
  playheadUs: number;
  selection: TimelineSelection | null;
  zoomLevel: number;
  briefs: RangeContinuityBrief[];
  acceptedEdits: AcceptedRangeEdit[];
  onSeek: (timeUs: number) => void;
  onSelectionChange: (selection: TimelineSelection | null) => void;
  onZoomChange: (zoom: number) => void;
}

type DragState = {
  mode: 'new' | 'start' | 'end';
  pointerId: number;
  anchorUs: number;
};

export function RangeTimeline({
  durationUs,
  sourceName,
  sourcePath,
  playheadUs,
  selection,
  zoomLevel,
  briefs,
  acceptedEdits,
  onSeek,
  onSelectionChange,
  onZoomChange,
}: RangeTimelineProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [viewport, setViewport] = useState({ scrollLeft: 0, width: 900 });
  const [snapActive, setSnapActive] = useState(false);

  const pxPerSecond = pixelsPerSecond(zoomLevel);
  const { labelIntervalUs, tickIntervalUs } = getTimelineRulerConfig(pxPerSecond);
  const timelineWidth = Math.max(
    viewport.width,
    timeUsToPixels(Math.max(durationUs, 1), pxPerSecond),
  );

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;

    const update = () => {
      setViewport({ scrollLeft: element.scrollLeft, width: element.clientWidth });
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const snapCandidates = useMemo(() => {
    const result: number[] = [];
    for (const brief of briefs) {
      if (brief.source_path === sourcePath) result.push(brief.start_us, brief.end_us);
    }
    for (const edit of acceptedEdits) {
      if (edit.source_path === sourcePath) result.push(edit.start_us, edit.end_us);
    }
    return result;
  }, [acceptedEdits, briefs, sourcePath]);

  const ticks = useMemo(() => {
    const bufferPx = Math.max(240, viewport.width * 0.2);
    const startUs = Math.max(
      0,
      pixelsToTimeUs(Math.max(0, viewport.scrollLeft - bufferPx), pxPerSecond),
    );
    const endUs = Math.min(
      durationUs,
      pixelsToTimeUs(viewport.scrollLeft + viewport.width + bufferPx, pxPerSecond),
    );
    const firstIndex = Math.max(0, Math.floor(startUs / tickIntervalUs));
    const lastIndex = Math.ceil(endUs / tickIntervalUs);
    const result: Array<{ timeUs: number; major: boolean }> = [];
    for (let index = firstIndex; index <= lastIndex; index += 1) {
      const timeUs = index * tickIntervalUs;
      if (timeUs > durationUs) break;
      result.push({
        timeUs,
        major: timeUs % labelIntervalUs === 0,
      });
    }
    return result;
  }, [durationUs, labelIntervalUs, pxPerSecond, tickIntervalUs, viewport]);

  const pointToTime = (clientX: number) => {
    const element = timelineRef.current;
    if (!element) return 0;
    const rect = element.getBoundingClientRect();
    const raw = pixelsToTimeUs(clientX - rect.left, pxPerSecond);
    const snapped = snapTimelineTime(raw, {
      durationUs,
      pxPerSecond,
      gridIntervalUs: tickIntervalUs,
      candidateTimesUs: snapCandidates,
    });
    setSnapActive(snapped.snapped);
    return snapped.timeUs;
  };

  const handleRulerPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    onSeek(pointToTime(event.clientX));
  };

  const handleTrackPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    const anchorUs = pointToTime(event.clientX);
    dragRef.current = { mode: 'new', pointerId: event.pointerId, anchorUs };
    event.currentTarget.setPointerCapture(event.pointerId);
    onSelectionChange({ startUs: anchorUs, endUs: anchorUs });
    onSeek(anchorUs);
  };

  const handleTrackPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const timeUs = pointToTime(event.clientX);

    if (drag.mode === 'new') {
      onSelectionChange({
        startUs: Math.min(drag.anchorUs, timeUs),
        endUs: Math.max(drag.anchorUs, timeUs),
      });
      return;
    }

    if (!selection) return;
    if (drag.mode === 'start') {
      onSelectionChange({
        startUs: Math.min(timeUs, selection.endUs),
        endUs: selection.endUs,
      });
    } else {
      onSelectionChange({
        startUs: selection.startUs,
        endUs: Math.max(timeUs, selection.startUs),
      });
    }
  };

  const finishDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setSnapActive(false);
  };

  const beginHandleDrag = (
    mode: 'start' | 'end',
    event: React.PointerEvent<HTMLButtonElement>,
  ) => {
    if (!selection) return;
    event.stopPropagation();
    dragRef.current = {
      mode,
      pointerId: event.pointerId,
      anchorUs: mode === 'start' ? selection.startUs : selection.endUs,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const playheadLeft = timeUsToPixels(Math.min(playheadUs, durationUs), pxPerSecond);
  const visibleBriefs = briefs.filter(brief => brief.source_path === sourcePath);
  const visibleAccepted = acceptedEdits.filter(edit => edit.source_path === sourcePath);

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Timeline</p>
          <p className="mt-1 text-sm text-slate-200">{sourceName}</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <button
            type="button"
            className="rounded-md border border-slate-700 px-2 py-1 hover:border-slate-500"
            onClick={() => onZoomChange(Math.max(MIN_TIMELINE_ZOOM, zoomLevel / 1.25))}
            aria-label="Уменьшить масштаб timeline"
          >
            −
          </button>
          <input
            aria-label="Масштаб timeline"
            type="range"
            min={MIN_TIMELINE_ZOOM}
            max={MAX_TIMELINE_ZOOM}
            step={0.05}
            value={zoomLevel}
            onChange={event => onZoomChange(Number(event.target.value))}
            className="w-28 accent-sky-400"
          />
          <button
            type="button"
            className="rounded-md border border-slate-700 px-2 py-1 hover:border-slate-500"
            onClick={() => onZoomChange(Math.min(MAX_TIMELINE_ZOOM, zoomLevel * 1.25))}
            aria-label="Увеличить масштаб timeline"
          >
            +
          </button>
          <span className="w-12 text-right font-mono">{zoomLevel.toFixed(2)}×</span>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="overflow-x-auto overflow-y-hidden"
        onScroll={event =>
          setViewport({
            scrollLeft: event.currentTarget.scrollLeft,
            width: event.currentTarget.clientWidth,
          })
        }
        onWheel={event => {
          if (!event.ctrlKey && !event.metaKey) return;
          event.preventDefault();
          const direction = event.deltaY > 0 ? 0.9 : 1.1;
          onZoomChange(Math.min(MAX_TIMELINE_ZOOM, Math.max(MIN_TIMELINE_ZOOM, zoomLevel * direction)));
        }}
      >
        <div
          ref={timelineRef}
          className="relative select-none"
          style={{ width: `${timelineWidth}px` }}
        >
          <div
            role="slider"
            tabIndex={0}
            aria-label="Линейка времени"
            aria-valuemin={0}
            aria-valuemax={durationUs}
            aria-valuenow={playheadUs}
            className="relative h-9 cursor-col-resize border-b border-slate-800 bg-slate-900/70"
            onPointerDown={handleRulerPointerDown}
            onKeyDown={event => {
              if (event.key === 'ArrowLeft') onSeek(Math.max(0, playheadUs - tickIntervalUs));
              if (event.key === 'ArrowRight') onSeek(Math.min(durationUs, playheadUs + tickIntervalUs));
            }}
          >
            {ticks.map(tick => (
              <div
                key={tick.timeUs}
                className="pointer-events-none absolute bottom-0 border-l border-slate-600"
                style={{
                  left: `${timeUsToPixels(tick.timeUs, pxPerSecond)}px`,
                  height: tick.major ? '22px' : '10px',
                }}
              >
                {tick.major && (
                  <span className="absolute bottom-4 left-1 whitespace-nowrap font-mono text-[10px] text-slate-500">
                    {formatRulerLabel(tick.timeUs, labelIntervalUs)}
                  </span>
                )}
              </div>
            ))}
          </div>

          <div
            className="relative h-24 cursor-crosshair bg-slate-950"
            onPointerDown={handleTrackPointerDown}
            onPointerMove={handleTrackPointerMove}
            onPointerUp={finishDrag}
            onPointerCancel={finishDrag}
          >
            <div className="absolute inset-x-0 top-4 h-14 rounded-md border border-slate-700 bg-slate-800/80">
              <div className="flex h-full items-center gap-3 overflow-hidden px-4">
                <span className="rounded bg-slate-950/70 px-2 py-1 font-mono text-[10px] text-slate-500">V1</span>
                <span className="truncate text-xs text-slate-300">{sourceName}</span>
              </div>
            </div>

            {visibleBriefs.map(brief => (
              <TimelineMarker
                key={brief.edit_id}
                startUs={brief.start_us}
                endUs={brief.end_us}
                pxPerSecond={pxPerSecond}
                className="top-4 h-14 border-amber-400/70 bg-amber-400/10"
                label="Brief"
              />
            ))}

            {visibleAccepted.map(edit => (
              <TimelineMarker
                key={edit.edit_id}
                startUs={edit.start_us}
                endUs={edit.end_us}
                pxPerSecond={pxPerSecond}
                className="top-4 h-14 border-emerald-400/80 bg-emerald-400/15"
                label="Accepted"
              />
            ))}

            {selection && (
              <div
                className="pointer-events-none absolute top-2 h-18 border-y-2 border-sky-400 bg-sky-400/15"
                style={{
                  left: `${timeUsToPixels(selection.startUs, pxPerSecond)}px`,
                  width: `${Math.max(2, timeUsToPixels(selection.endUs - selection.startUs, pxPerSecond))}px`,
                }}
              >
                <button
                  type="button"
                  aria-label="Изменить начало диапазона"
                  className="pointer-events-auto absolute -left-1.5 top-0 h-full w-3 cursor-ew-resize rounded bg-sky-400"
                  onPointerDown={event => beginHandleDrag('start', event)}
                />
                <button
                  type="button"
                  aria-label="Изменить конец диапазона"
                  className="pointer-events-auto absolute -right-1.5 top-0 h-full w-3 cursor-ew-resize rounded bg-sky-400"
                  onPointerDown={event => beginHandleDrag('end', event)}
                />
              </div>
            )}

            <div
              className="pointer-events-none absolute top-0 h-full w-px bg-fuchsia-400"
              style={{ left: `${playheadLeft}px` }}
            >
              <span className="absolute -left-1.5 top-0 h-3 w-3 rounded-full bg-fuchsia-400" />
            </div>

            {snapActive && (
              <div className="pointer-events-none absolute right-3 bottom-2 rounded bg-slate-900 px-2 py-1 text-[10px] text-sky-300">
                snap
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-slate-800 px-4 py-2 text-[11px] text-slate-500">
        <span>Playhead: <strong className="font-mono font-normal text-slate-300">{formatTimelineTime(playheadUs)}</strong></span>
        {selection && (
          <>
            <span>Начало: <strong className="font-mono font-normal text-sky-300">{formatTimelineTime(selection.startUs)}</strong></span>
            <span>Конец: <strong className="font-mono font-normal text-sky-300">{formatTimelineTime(selection.endUs)}</strong></span>
            <span>Длина: <strong className="font-mono font-normal text-slate-300">{formatTimelineTime(Math.max(0, selection.endUs - selection.startUs))}</strong></span>
          </>
        )}
        <span className="ml-auto">Выделение: перетащите по дорожке · seek: линейка</span>
      </div>
    </section>
  );
}

function TimelineMarker({
  startUs,
  endUs,
  pxPerSecond,
  className,
  label,
}: {
  startUs: number;
  endUs: number;
  pxPerSecond: number;
  className: string;
  label: string;
}) {
  return (
    <div
      className={`pointer-events-none absolute overflow-hidden border-x ${className}`}
      style={{
        left: `${timeUsToPixels(startUs, pxPerSecond)}px`,
        width: `${Math.max(2, timeUsToPixels(endUs - startUs, pxPerSecond))}px`,
      }}
    >
      <span className="absolute left-1 top-1 rounded bg-slate-950/70 px-1.5 py-0.5 text-[9px] text-slate-300">
        {label}
      </span>
    </div>
  );
}
