'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getUVProject, type ProjectReference } from '@/lib/projectsApi';
import {
  executeMusicDirectionCommand,
  executeMusicMapCommand,
  getMusicDirection,
  getMusicMap,
  getRhythmAudit,
  projectAudioUrl,
  uploadProjectAudioSource,
  type MusicDirectionState,
  type MusicLyricPhrase,
  type MusicMapState,
  type MusicMarkerKind,
  type MusicSection,
  type MusicSectionKind,
  type MusicShotPlan,
  type MusicTimingMarker,
  type MusicTransition,
  type RhythmAudit,
} from '@/lib/musicVideoApi';

interface MusicVideoPanelProps {
  projectId: string;
  onProjectChanged?: () => void | Promise<void>;
}

interface SectionDraft {
  section_id: string;
  kind: MusicSectionKind;
  label: string;
  start: string;
  end: string;
}

interface MarkerDraft {
  marker_id: string;
  kind: MusicMarkerKind;
  time: string;
}

interface LyricDraft {
  phrase_id: string;
  start: string;
  end: string;
  text: string;
}

interface ShotDraft {
  shot_id: string;
  start_us: number;
  end_us: number;
  intent: string;
  sync_marker_id: string;
  transition_out: MusicTransition;
}

const sectionKinds: Array<{ value: MusicSectionKind; label: string }> = [
  { value: 'intro', label: 'Интро' },
  { value: 'verse', label: 'Куплет' },
  { value: 'pre_chorus', label: 'Пре-хорус' },
  { value: 'chorus', label: 'Припев' },
  { value: 'bridge', label: 'Бридж' },
  { value: 'drop', label: 'Дроп' },
  { value: 'breakdown', label: 'Брейкдаун' },
  { value: 'instrumental', label: 'Инструментал' },
  { value: 'outro', label: 'Аутро' },
  { value: 'other', label: 'Другое' },
];

const markerKinds: Array<{ value: MusicMarkerKind; label: string }> = [
  { value: 'beat', label: 'Бит' },
  { value: 'downbeat', label: 'Сильная доля' },
  { value: 'accent', label: 'Акцент' },
  { value: 'climax', label: 'Кульминация' },
  { value: 'phrase_boundary', label: 'Граница фразы' },
  { value: 'cut_point', label: 'Точка монтажа' },
];

const transitionLabels: Record<MusicTransition, string> = {
  cut: 'Склейка',
  dissolve: 'Наплыв',
  fade: 'Затемнение',
  match_cut: 'Match cut',
  other: 'Другое',
};

const inputClass = 'rounded border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs';

function seconds(us: number): string {
  return (us / 1_000_000).toFixed(3).replace(/\.000$/, '');
}

function secondsToUs(value: string, field: string): number {
  const parsed = Number(value.replace(',', '.'));
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new Error(`${field}: укажите неотрицательное число секунд`);
  }
  return Math.round(parsed * 1_000_000);
}

function sourceLabel(source: ProjectReference): string {
  const name = source.metadata.original_name;
  return typeof name === 'string' && name.trim() ? name : source.path;
}

function vttTimestamp(us: number): string {
  const totalMs = Math.max(0, Math.round(us / 1_000));
  const hours = Math.floor(totalMs / 3_600_000);
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000);
  const secs = Math.floor((totalMs % 60_000) / 1_000);
  const ms = totalMs % 1_000;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

function musicCaptionTrackUrl(map: MusicMapState | null, source: ProjectReference | null): string {
  const cues: string[] = [];
  if (map && map.lyric_phrases.length > 0) {
    for (const phrase of map.lyric_phrases) {
      cues.push(`${vttTimestamp(phrase.start_us)} --> ${vttTimestamp(phrase.end_us)}\n${phrase.text}`);
    }
  } else if (map && map.sections.length > 0) {
    for (const section of map.sections) {
      cues.push(`${vttTimestamp(section.start_us)} --> ${vttTimestamp(section.end_us)}\n${section.label}`);
    }
  } else {
    const duration = source?.metadata.duration_us;
    const endUs = typeof duration === 'number' && Number.isFinite(duration) && duration > 0
      ? duration
      : 30_000_000;
    cues.push(`${vttTimestamp(0)} --> ${vttTimestamp(endUs)}\nМузыкальное превью. Music Map ещё не подтверждён.`);
  }
  return `data:text/vtt;charset=utf-8,${encodeURIComponent(`WEBVTT\n\n${cues.join('\n\n')}\n`)}`;
}

function hydrateSections(map: MusicMapState | null): SectionDraft[] {
  return (map?.sections ?? []).map(item => ({
    section_id: item.section_id,
    kind: item.kind,
    label: item.label,
    start: seconds(item.start_us),
    end: seconds(item.end_us),
  }));
}

function hydrateMarkers(map: MusicMapState | null): MarkerDraft[] {
  return (map?.markers ?? []).map(item => ({
    marker_id: item.marker_id,
    kind: item.kind,
    time: seconds(item.time_us),
  }));
}

function hydrateLyrics(map: MusicMapState | null): LyricDraft[] {
  return (map?.lyric_phrases ?? []).map(item => ({
    phrase_id: item.phrase_id,
    start: seconds(item.start_us),
    end: seconds(item.end_us),
    text: item.text,
  }));
}

function directionDraft(map: MusicMapState): ShotDraft[] {
  const boundaries = new Set<number>([map.excerpt.start_us, map.excerpt.end_us]);
  for (const section of map.sections) {
    boundaries.add(section.start_us);
    boundaries.add(section.end_us);
  }
  for (const marker of map.markers) {
    if (marker.kind === 'cut_point') boundaries.add(marker.time_us);
  }
  const ordered = [...boundaries]
    .filter(value => value >= map.excerpt.start_us && value <= map.excerpt.end_us)
    .sort((left, right) => left - right);
  const markerAt = new Map(map.markers.map(marker => [marker.time_us, marker]));
  const result: ShotDraft[] = [];
  for (let index = 0; index < ordered.length - 1; index += 1) {
    const start = ordered[index];
    const end = ordered[index + 1];
    if (end <= start) continue;
    const midpoint = start + Math.floor((end - start) / 2);
    const section = map.sections.find(item => midpoint >= item.start_us && midpoint < item.end_us);
    result.push({
      shot_id: `mv_shot_${String(result.length + 1).padStart(2, '0')}`,
      start_us: start,
      end_us: end,
      intent: section ? `${section.label}: визуальный план` : 'Переход между музыкальными участками',
      sync_marker_id: markerAt.get(end)?.marker_id ?? '',
      transition_out: index === ordered.length - 2 ? 'fade' : 'cut',
    });
  }
  return result;
}

export function MusicVideoPanel({ projectId, onProjectChanged }: MusicVideoPanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [audioSources, setAudioSources] = useState<ProjectReference[]>([]);
  const [musicMap, setMusicMap] = useState<MusicMapState | null>(null);
  const [direction, setDirection] = useState<MusicDirectionState | null>(null);
  const [audit, setAudit] = useState<RhythmAudit | null>(null);
  const [selectedSongId, setSelectedSongId] = useState('');
  const [excerptStart, setExcerptStart] = useState('0');
  const [excerptEnd, setExcerptEnd] = useState('30');
  const [sections, setSections] = useState<SectionDraft[]>([]);
  const [markers, setMarkers] = useState<MarkerDraft[]>([]);
  const [lyrics, setLyrics] = useState<LyricDraft[]>([]);
  const [shots, setShots] = useState<ShotDraft[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [directionWarning, setDirectionWarning] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [project, map] = await Promise.all([getUVProject(projectId), getMusicMap(projectId)]);
    const sources = project.sources.filter(reference => reference.kind === 'audio');
    setAudioSources(sources);
    setMusicMap(map);
    setSelectedSongId(current => {
      if (current && sources.some(source => source.id === current)) return current;
      return map?.song.reference_id ?? sources[0]?.id ?? '';
    });
    if (map) {
      setExcerptStart(seconds(map.excerpt.start_us));
      setExcerptEnd(seconds(map.excerpt.end_us));
      setSections(hydrateSections(map));
      setMarkers(hydrateMarkers(map));
      setLyrics(hydrateLyrics(map));
    }

    try {
      const currentDirection = await getMusicDirection(projectId);
      setDirection(currentDirection);
      setDirectionWarning(null);
      if (currentDirection) {
        setShots(currentDirection.shots.map(item => ({
          shot_id: item.shot_id,
          start_us: item.start_us,
          end_us: item.end_us,
          intent: item.intent,
          sync_marker_id: item.sync_marker_ids[0] ?? '',
          transition_out: item.transition_out,
        })));
        setAudit(await getRhythmAudit(projectId));
      } else {
        setAudit(null);
      }
    } catch (reason) {
      setDirection(null);
      setAudit(null);
      setDirectionWarning(reason instanceof Error ? reason.message : 'План кадров устарел');
    }
  }, [projectId]);

  useEffect(() => {
    let active = true;
    refresh().catch(reason => {
      if (active) setError(reason instanceof Error ? reason.message : 'Не удалось загрузить Music Video Mode');
    });
    return () => {
      active = false;
    };
  }, [refresh]);

  const selectedSong = useMemo(
    () => audioSources.find(source => source.id === selectedSongId) ?? null,
    [audioSources, selectedSongId],
  );
  const captionTrackUrl = useMemo(
    () => musicCaptionTrackUrl(musicMap, selectedSong),
    [musicMap, selectedSong],
  );

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await operation();
      await refresh();
      await onProjectChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Операция Music Video Mode не выполнена');
    } finally {
      setBusy(false);
    }
  };

  const uploadSong = (file: File) => run(async () => {
    const reference = await uploadProjectAudioSource(projectId, file);
    const duration = reference.metadata.duration_us;
    setSelectedSongId(reference.id);
    setExcerptStart('0');
    if (typeof duration === 'number' && Number.isFinite(duration)) {
      setExcerptEnd(seconds(Math.min(duration, 30_000_000)));
    }
    setSections([]);
    setMarkers([]);
    setLyrics([]);
    setShots([]);
    setNotice('Песня зарегистрирована как project-owned audio source. Теперь задайте рабочий фрагмент и Music Map.');
  });

  const saveMap = () => run(async () => {
    if (!selectedSongId) throw new Error('Сначала выберите или загрузите песню');
    const startUs = secondsToUs(excerptStart, 'Начало фрагмента');
    const endUs = secondsToUs(excerptEnd, 'Конец фрагмента');
    if (endUs <= startUs) throw new Error('Конец фрагмента должен быть позже начала');
    const sectionPayload: MusicSection[] = sections.map(item => ({
      section_id: item.section_id.trim(),
      kind: item.kind,
      label: item.label.trim(),
      start_us: secondsToUs(item.start, `Секция ${item.section_id}`),
      end_us: secondsToUs(item.end, `Секция ${item.section_id}`),
    }));
    const markerPayload: MusicTimingMarker[] = markers.map(item => ({
      marker_id: item.marker_id.trim(),
      kind: item.kind,
      time_us: secondsToUs(item.time, `Маркер ${item.marker_id}`),
    }));
    const lyricPayload: MusicLyricPhrase[] = lyrics.map(item => ({
      phrase_id: item.phrase_id.trim(),
      start_us: secondsToUs(item.start, `Фраза ${item.phrase_id}`),
      end_us: secondsToUs(item.end, `Фраза ${item.phrase_id}`),
      text: item.text.trim(),
    }));
    const result = await executeMusicMapCommand(projectId, {
      command: 'set_music_map',
      song_reference_id: selectedSongId,
      excerpt: { start_us: startUs, end_us: endUs },
      sections: sectionPayload,
      markers: markerPayload,
      lyric_phrases: lyricPayload,
    });
    const newMap = result.payload;
    if (!newMap) throw new Error('Music Map не был сохранён');
    if (directionWarning || (direction && direction.music_map_revision_sha256 !== newMap.revision_sha256)) {
      await executeMusicDirectionCommand(projectId, { command: 'clear_music_direction' });
      setShots([]);
    }
    setNotice('Music Map сохранён и привязан к точным байтам песни.');
  });

  const makeDirectionDraft = () => {
    if (!musicMap) {
      setError('Сначала сохраните Music Map');
      return;
    }
    setShots(directionDraft(musicMap));
    setNotice('Создан локальный черновик по границам секций и маркерам «Точка монтажа». Отредактируйте замысел перед сохранением.');
  };

  const saveDirection = () => run(async () => {
    if (!musicMap) throw new Error('Сначала сохраните Music Map');
    if (shots.length === 0) throw new Error('Создайте хотя бы один план кадра');
    const payload: MusicShotPlan[] = shots.map((item, index) => ({
      shot_id: item.shot_id,
      order: index,
      start_us: item.start_us,
      end_us: item.end_us,
      intent: item.intent.trim(),
      sync_marker_ids: item.sync_marker_id ? [item.sync_marker_id] : [],
      transition_out: item.transition_out,
    }));
    await executeMusicDirectionCommand(projectId, {
      command: 'set_music_direction',
      music_map_revision_sha256: musicMap.revision_sha256,
      shots: payload,
    });
    setNotice('Music Director сохранён для точной ревизии Music Map.');
  });

  return (
    <section className="mb-6 mt-8 rounded-2xl border border-violet-900/60 bg-slate-900/60 p-6">
      <p className="text-xs uppercase tracking-wider text-violet-400">Stage 7 · Music Video Mode</p>
      <h2 className="mt-2 text-xl font-medium">Песня → Music Map → музыкальная режиссура → проверка ритма</h2>
      <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-400">
        Песня хранится как обычный project-owned audio source. Music Map и план кадров привязаны к точным SHA/revision, а проверка ритма измеряет монтажные границы без обязательного ИИ или платного провайдера.
      </p>

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">1. Master-аудио и рабочий фрагмент</h3>
          <div className="mt-4 flex flex-wrap gap-3">
            <input
              ref={fileRef}
              type="file"
              accept="audio/*,.wav,.mp3,.flac,.m4a,.aac,.ogg,.opus"
              className="hidden"
              aria-label="Файл песни"
              onChange={event => {
                const file = event.target.files?.[0];
                if (file) void uploadSong(file);
              }}
            />
            <button
              type="button"
              disabled={busy}
              onClick={() => fileRef.current?.click()}
              className="rounded-lg bg-violet-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
            >
              Загрузить песню
            </button>
            {audioSources.length > 0 && (
              <select
                aria-label="Песня Music Video Mode"
                value={selectedSongId}
                onChange={event => setSelectedSongId(event.target.value)}
                className="min-w-64 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              >
                {audioSources.map(source => <option key={source.id} value={source.id}>{sourceLabel(source)}</option>)}
              </select>
            )}
          </div>
          {selectedSong && (
            <audio className="mt-4 w-full" controls src={projectAudioUrl(projectId, selectedSong.id)}>
              <track kind="captions" srcLang="ru" label="Music Map" src={captionTrackUrl} default />
            </audio>
          )}
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <NumberField label="Начало фрагмента, с" value={excerptStart} onChange={setExcerptStart} aria="Начало музыкального фрагмента" />
            <NumberField label="Конец фрагмента, с" value={excerptEnd} onChange={setExcerptEnd} aria="Конец музыкального фрагмента" />
          </div>
          {selectedSong && typeof selectedSong.metadata.duration_us === 'number' && (
            <p className="mt-2 text-xs text-slate-500">Длительность источника: {seconds(selectedSong.metadata.duration_us as number)} с</p>
          )}
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">2. Секции Music Map</h3>
          <p className="mt-1 text-xs text-slate-500">Секции не анализируются автоматически: это канонические данные, которые вы подтверждаете сами.</p>
          <div className="mt-4 space-y-3">
            {sections.map((item, index) => (
              <div key={`${item.section_id}-${index}`} className="grid gap-2 rounded-lg border border-slate-800 p-3 sm:grid-cols-6">
                <input aria-label={`ID музыкальной секции ${index + 1}`} value={item.section_id} onChange={event => setSections(current => current.map((entry, i) => i === index ? { ...entry, section_id: event.target.value } : entry))} className={`${inputClass} sm:col-span-1`} />
                <select aria-label={`Тип музыкальной секции ${index + 1}`} value={item.kind} onChange={event => setSections(current => current.map((entry, i) => i === index ? { ...entry, kind: event.target.value as MusicSectionKind } : entry))} className={`${inputClass} sm:col-span-1`}>
                  {sectionKinds.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <input aria-label={`Название музыкальной секции ${index + 1}`} value={item.label} onChange={event => setSections(current => current.map((entry, i) => i === index ? { ...entry, label: event.target.value } : entry))} className={`${inputClass} sm:col-span-2`} />
                <input aria-label={`Начало музыкальной секции ${index + 1}`} value={item.start} onChange={event => setSections(current => current.map((entry, i) => i === index ? { ...entry, start: event.target.value } : entry))} className={inputClass} />
                <div className="flex gap-1">
                  <input aria-label={`Конец музыкальной секции ${index + 1}`} value={item.end} onChange={event => setSections(current => current.map((entry, i) => i === index ? { ...entry, end: event.target.value } : entry))} className={`${inputClass} min-w-0 flex-1`} />
                  <button type="button" aria-label={`Удалить музыкальную секцию ${index + 1}`} onClick={() => setSections(current => current.filter((_, i) => i !== index))} className="px-2 text-slate-500 hover:text-red-300">×</button>
                </div>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setSections(current => [...current, {
              section_id: `section_${current.length + 1}`,
              kind: 'other',
              label: `Секция ${current.length + 1}`,
              start: excerptStart,
              end: excerptEnd,
            }])}
            className="mt-3 rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300"
          >
            + Добавить секцию
          </button>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">3. Ритмические и смысловые маркеры</h3>
          <div className="mt-4 space-y-2">
            {markers.map((item, index) => (
              <div key={`${item.marker_id}-${index}`} className="grid gap-2 sm:grid-cols-4">
                <input aria-label={`ID музыкального маркера ${index + 1}`} value={item.marker_id} onChange={event => setMarkers(current => current.map((entry, i) => i === index ? { ...entry, marker_id: event.target.value } : entry))} className={inputClass} />
                <select aria-label={`Тип музыкального маркера ${index + 1}`} value={item.kind} onChange={event => setMarkers(current => current.map((entry, i) => i === index ? { ...entry, kind: event.target.value as MusicMarkerKind } : entry))} className={`${inputClass} sm:col-span-2`}>
                  {markerKinds.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
                <div className="flex gap-1">
                  <input aria-label={`Время музыкального маркера ${index + 1}`} value={item.time} onChange={event => setMarkers(current => current.map((entry, i) => i === index ? { ...entry, time: event.target.value } : entry))} className={`${inputClass} min-w-0 flex-1`} />
                  <button type="button" aria-label={`Удалить музыкальный маркер ${index + 1}`} onClick={() => setMarkers(current => current.filter((_, i) => i !== index))} className="px-2 text-slate-500 hover:text-red-300">×</button>
                </div>
              </div>
            ))}
          </div>
          <button type="button" onClick={() => setMarkers(current => [...current, { marker_id: `marker_${current.length + 1}`, kind: 'beat', time: excerptStart }])} className="mt-3 rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300">+ Добавить маркер</button>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <h3 className="font-medium">4. Вокальные/текстовые фразы</h3>
          <div className="mt-4 space-y-2">
            {lyrics.map((item, index) => (
              <div key={`${item.phrase_id}-${index}`} className="grid gap-2 sm:grid-cols-6">
                <input aria-label={`ID вокальной фразы ${index + 1}`} value={item.phrase_id} onChange={event => setLyrics(current => current.map((entry, i) => i === index ? { ...entry, phrase_id: event.target.value } : entry))} className={inputClass} />
                <input aria-label={`Начало вокальной фразы ${index + 1}`} value={item.start} onChange={event => setLyrics(current => current.map((entry, i) => i === index ? { ...entry, start: event.target.value } : entry))} className={inputClass} />
                <input aria-label={`Конец вокальной фразы ${index + 1}`} value={item.end} onChange={event => setLyrics(current => current.map((entry, i) => i === index ? { ...entry, end: event.target.value } : entry))} className={inputClass} />
                <input aria-label={`Текст вокальной фразы ${index + 1}`} value={item.text} onChange={event => setLyrics(current => current.map((entry, i) => i === index ? { ...entry, text: event.target.value } : entry))} className={`${inputClass} sm:col-span-2`} />
                <button type="button" aria-label={`Удалить вокальную фразу ${index + 1}`} onClick={() => setLyrics(current => current.filter((_, i) => i !== index))} className="text-slate-500 hover:text-red-300">Удалить</button>
              </div>
            ))}
          </div>
          <button type="button" onClick={() => setLyrics(current => [...current, { phrase_id: `phrase_${current.length + 1}`, start: excerptStart, end: excerptEnd, text: '' }])} className="mt-3 rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300">+ Добавить фразу</button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button type="button" disabled={busy || !selectedSongId} onClick={saveMap} className="rounded-lg bg-violet-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">Сохранить Music Map</button>
        {musicMap && <span className="font-mono text-xs text-slate-600">map {musicMap.revision_sha256.slice(0, 12)}…</span>}
      </div>

      {musicMap && (
        <div className="mt-7 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-medium">5. Music Director</h3>
              <p className="mt-1 text-xs text-slate-500">План обязан покрывать весь excerpt без разрывов и привязан к ревизии Music Map.</p>
            </div>
            <button type="button" disabled={busy} onClick={makeDirectionDraft} className="rounded border border-violet-700 px-3 py-1.5 text-xs text-violet-300">Черновик по Music Map</button>
          </div>
          {directionWarning && <p className="mt-3 rounded-lg border border-amber-900 bg-amber-950/30 p-3 text-xs text-amber-300">Предыдущий план больше не текущий: {directionWarning}</p>}
          <div className="mt-4 space-y-3">
            {shots.map((shot, index) => {
              const availableMarkers = musicMap.markers.filter(marker => marker.time_us >= shot.start_us && marker.time_us <= shot.end_us);
              return (
                <div key={shot.shot_id} className="grid gap-3 rounded-lg border border-slate-800 p-4 lg:grid-cols-7">
                  <div className="text-xs text-slate-500 lg:col-span-1">
                    <p className="font-mono text-slate-300">{shot.shot_id}</p>
                    <p className="mt-1">{seconds(shot.start_us)}–{seconds(shot.end_us)} с</p>
                  </div>
                  <input aria-label={`Замысел музыкального кадра ${index + 1}`} value={shot.intent} onChange={event => setShots(current => current.map((entry, i) => i === index ? { ...entry, intent: event.target.value } : entry))} className="rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm lg:col-span-3" />
                  <select aria-label={`Синхронизация музыкального кадра ${index + 1}`} value={shot.sync_marker_id} onChange={event => setShots(current => current.map((entry, i) => i === index ? { ...entry, sync_marker_id: event.target.value } : entry))} className="rounded border border-slate-700 bg-slate-950 px-2 py-2 text-xs lg:col-span-2">
                    <option value="">Без явного sync</option>
                    {availableMarkers.map(marker => <option key={marker.marker_id} value={marker.marker_id}>{marker.marker_id} · {seconds(marker.time_us)} с</option>)}
                  </select>
                  <select aria-label={`Переход музыкального кадра ${index + 1}`} value={shot.transition_out} onChange={event => setShots(current => current.map((entry, i) => i === index ? { ...entry, transition_out: event.target.value as MusicTransition } : entry))} className="rounded border border-slate-700 bg-slate-950 px-2 py-2 text-xs">
                    {(Object.keys(transitionLabels) as MusicTransition[]).map(value => <option key={value} value={value}>{transitionLabels[value]}</option>)}
                  </select>
                </div>
              );
            })}
          </div>
          {shots.length > 0 && (
            <button type="button" disabled={busy || shots.some(shot => !shot.intent.trim())} onClick={saveDirection} className="mt-4 rounded-lg bg-sky-400 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50">Сохранить режиссёрский план</button>
          )}
        </div>
      )}

      {direction && audit && (
        <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="font-medium">6. Детерминированная проверка ритма</h3>
              <p className="mt-1 text-xs text-slate-500">Допуск ±{seconds(audit.tolerance_us)} с. Проверка ничего не меняет в проекте.</p>
            </div>
            <span className={`rounded-full px-3 py-1 text-xs ${audit.summary.all_aligned ? 'bg-emerald-950 text-emerald-300' : 'bg-amber-950 text-amber-300'}`}>
              {audit.summary.aligned_count}/{audit.summary.cut_count} границ в допуске
            </span>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {audit.cuts.map(cut => (
              <div key={cut.shot_id} className={`rounded-lg border p-3 text-xs ${cut.aligned ? 'border-emerald-900 bg-emerald-950/20' : 'border-amber-900 bg-amber-950/20'}`}>
                <p className="font-mono text-slate-300">{cut.shot_id}</p>
                <p className="mt-1 text-slate-500">cut {seconds(cut.cut_time_us)} с</p>
                <p className="mt-1 text-slate-300">{cut.target ? `${cut.target.kind}: ${seconds(cut.target.time_us)} с` : 'Нет цели'}</p>
                <p className={cut.aligned ? 'mt-1 text-emerald-300' : 'mt-1 text-amber-300'}>{cut.delta_us == null ? 'не измерено' : `${cut.delta_us >= 0 ? '+' : ''}${seconds(cut.delta_us)} с`}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {notice && <p className="mt-5 text-sm text-emerald-300">{notice}</p>}
      {error && <p className="mt-5 text-sm text-red-300">{error}</p>}
    </section>
  );
}

function NumberField({ label, value, onChange, aria }: { label: string; value: string; onChange: (value: string) => void; aria: string }) {
  return (
    <label className="block text-xs text-slate-500">
      {label}
      <input aria-label={aria} inputMode="decimal" value={value} onChange={event => onChange(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200" />
    </label>
  );
}
