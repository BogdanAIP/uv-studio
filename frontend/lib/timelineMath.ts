/*
 * Timeline ruler interval selection is adapted from OpenCut Classic's
 * apps/web/src/timeline/ruler-utils.ts at
 * cf5e79e919144200294fb9fed22a222592a0aeea (MIT).
 *
 * UV Studio intentionally keeps canonical editor time in integer microseconds
 * and uses time-based ticks here instead of claiming frame-accurate snapping
 * from an average frame-rate value. See third_party/opencut-classic/LICENSE.
 */

export const BASE_TIMELINE_PIXELS_PER_SECOND = 80;
export const MIN_TIMELINE_ZOOM = 0.25;
export const MAX_TIMELINE_ZOOM = 4;

const INTERVALS_US = [
  100_000,
  200_000,
  500_000,
  1_000_000,
  2_000_000,
  3_000_000,
  5_000_000,
  10_000_000,
  15_000_000,
  30_000_000,
  60_000_000,
  120_000_000,
  300_000_000,
  600_000_000,
  900_000_000,
  1_800_000_000,
  3_600_000_000,
] as const;

const MIN_LABEL_SPACING_PX = 100;
const MIN_TICK_SPACING_PX = 18;

export interface TimelineRulerConfig {
  labelIntervalUs: number;
  tickIntervalUs: number;
}

export interface SnapResult {
  timeUs: number;
  snapped: boolean;
}

export function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, value));
}

export function pixelsPerSecond(zoomLevel: number): number {
  return BASE_TIMELINE_PIXELS_PER_SECOND * clamp(
    zoomLevel,
    MIN_TIMELINE_ZOOM,
    MAX_TIMELINE_ZOOM,
  );
}

export function timeUsToPixels(timeUs: number, pxPerSecond: number): number {
  return (timeUs / 1_000_000) * pxPerSecond;
}

export function pixelsToTimeUs(pixel: number, pxPerSecond: number): number {
  return Math.round((pixel / pxPerSecond) * 1_000_000);
}

function findInterval(pxPerSecond: number, minimumSpacingPx: number): number {
  for (const intervalUs of INTERVALS_US) {
    const spacing = timeUsToPixels(intervalUs, pxPerSecond);
    if (spacing >= minimumSpacingPx) return intervalUs;
  }
  return INTERVALS_US[INTERVALS_US.length - 1];
}

export function getTimelineRulerConfig(pxPerSecond: number): TimelineRulerConfig {
  const labelIntervalUs = findInterval(pxPerSecond, MIN_LABEL_SPACING_PX);
  let tickIntervalUs = findInterval(pxPerSecond, MIN_TICK_SPACING_PX);

  if (labelIntervalUs % tickIntervalUs !== 0) {
    const divisor = INTERVALS_US.find(
      interval =>
        interval <= labelIntervalUs &&
        labelIntervalUs % interval === 0 &&
        timeUsToPixels(interval, pxPerSecond) >= MIN_TICK_SPACING_PX,
    );
    tickIntervalUs = divisor ?? labelIntervalUs;
  }

  return { labelIntervalUs, tickIntervalUs };
}

export function formatTimelineTime(timeUs: number, includeMillis = true): string {
  const safeUs = Math.max(0, Math.round(timeUs));
  const totalMillis = Math.floor(safeUs / 1_000);
  const millis = totalMillis % 1_000;
  const totalSeconds = Math.floor(totalMillis / 1_000);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);

  const hh = hours > 0 ? `${hours.toString().padStart(2, '0')}:` : '';
  const mm = minutes.toString().padStart(2, '0');
  const ss = seconds.toString().padStart(2, '0');
  const ms = includeMillis ? `.${millis.toString().padStart(3, '0')}` : '';
  return `${hh}${mm}:${ss}${ms}`;
}

export function formatRulerLabel(timeUs: number, labelIntervalUs: number): string {
  return formatTimelineTime(timeUs, labelIntervalUs < 1_000_000);
}

export function snapTimelineTime(
  rawTimeUs: number,
  options: {
    durationUs: number;
    pxPerSecond: number;
    gridIntervalUs: number;
    candidateTimesUs?: number[];
    thresholdPx?: number;
  },
): SnapResult {
  const durationUs = Math.max(0, options.durationUs);
  const clamped = clamp(Math.round(rawTimeUs), 0, durationUs);
  const thresholdUs = pixelsToTimeUs(options.thresholdPx ?? 8, options.pxPerSecond);
  const candidates = [0, durationUs, ...(options.candidateTimesUs ?? [])];

  if (options.gridIntervalUs > 0) {
    const gridTime = Math.round(clamped / options.gridIntervalUs) * options.gridIntervalUs;
    candidates.push(clamp(gridTime, 0, durationUs));
  }

  let best = clamped;
  let bestDistance = thresholdUs + 1;
  for (const candidate of candidates) {
    const normalized = clamp(Math.round(candidate), 0, durationUs);
    const distance = Math.abs(normalized - clamped);
    if (distance <= thresholdUs && distance < bestDistance) {
      best = normalized;
      bestDistance = distance;
    }
  }

  return { timeUs: best, snapped: best !== clamped };
}
