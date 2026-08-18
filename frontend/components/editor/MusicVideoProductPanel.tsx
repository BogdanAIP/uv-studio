'use client';

import { ListMusic, Loader2, Music2, Plus, RefreshCw, Sparkles, Trash2, Upload } from 'lucide-react';
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

interface Props { projectId: string; onProjectChanged?: () => void | Promise<void>; }
interface SectionDraft { section_id: string; kind: MusicSectionKind; label: string; start: string; end: string; }
interface MarkerDraft { marker_id: string; kind: MusicMarkerKind; time: string; }
interface LyricDraft { phrase_id: string; start: string; end: string; text: string; }
interface ShotDraft { shot_id: string; start_us: number; end_us: number; intent: string; sync_marker_id: string; transition_out: MusicTransition; }

const sectionKinds: Array<{ value: MusicSectionKind; label: string }> = [
  { value: 'intro', label: 'Интро' }, { value: 'verse', label: 'Куплет' }, { value: 'pre_chorus', label: 'Пре-хорус' },
  { value: 'chorus', label: 'Припев' }, { value: 'bridge', label: 'Бридж' }, { value: 'drop', label: 'Дроп' },
  { value: 'breakdown', label: 'Брейкдаун' }, { value: 'instrumental', label: 'Инструментал' }, { value: 'outro', label: 'Аутро' }, { value: 'other', label: 'Другое' },
];
const markerKinds: Array<{ value: MusicMarkerKind; label: string }> = [
  { value: 'beat', label: 'Бит' }, { value: 'downbeat', label: 'Сильная доля' }, { value: 'accent', label: 'Акцент' },
  { value: 'climax', label: 'Кульминация' }, { value: 'phrase_boundary', label: 'Граница фразы' }, { value: 'cut_point', label: 'Точка монтажа' },
];
const transitions: Record<MusicTransition, string> = { cut: 'Склейка', dissolve: 'Наплыв', fade: 'Затемнение', match_cut: 'Match cut', other: 'Другое' };

function sec(us: number) { return (us / 1_000_000).toFixed(3).replace(/\.000$/, ''); }
function toUs(value: string, field: string) { const n = Number(value.replace(',', '.')); if (!Number.isFinite(n) || n < 0) throw new Error(`${field}: укажите число секунд`); return Math.round(n * 1_000_000); }
function sourceName(source: ProjectReference) { const name = source.metadata.original_name; return typeof name === 'string' && name.trim() ? name : source.path.split('/').at(-1) ?? 'Аудио'; }
function hydrateSections(map: MusicMapState | null): SectionDraft[] { return (map?.sections ?? []).map(item => ({ section_id: item.section_id, kind: item.kind, label: item.label, start: sec(item.start_us), end: sec(item.end_us) })); }
function hydrateMarkers(map: MusicMapState | null): MarkerDraft[] { return (map?.markers ?? []).map(item => ({ marker_id: item.marker_id, kind: item.kind, time: sec(item.time_us) })); }
function hydrateLyrics(map: MusicMapState | null): LyricDraft[] { return (map?.lyric_phrases ?? []).map(item => ({ phrase_id: item.phrase_id, start: sec(item.start_us), end: sec(item.end_us), text: item.text })); }
function makeShots(map: MusicMapState): ShotDraft[] {
  const boundaries = new Set<number>([map.excerpt.start_us, map.excerpt.end_us]);
  map.sections.forEach(section => { boundaries.add(section.start_us); boundaries.add(section.end_us); });
  map.markers.filter(marker => marker.kind === 'cut_point').forEach(marker => boundaries.add(marker.time_us));
  const ordered = [...boundaries].filter(value => value >= map.excerpt.start_us && value <= map.excerpt.end_us).sort((a, b) => a - b);
  const markerAt = new Map(map.markers.map(marker => [marker.time_us, marker]));
  return ordered.slice(0, -1).flatMap((start, index) => {
    const end = ordered[index + 1]; if (end <= start) return [];
    const midpoint = start + Math.floor((end - start) / 2); const section = map.sections.find(item => midpoint >= item.start_us && midpoint < item.end_us);
    return [{ shot_id: `mv_shot_${String(index + 1).padStart(2, '0')}`, start_us: start, end_us: end, intent: section ? `${section.label}: визуальный план` : 'Переход между музыкальными участками', sync_marker_id: markerAt.get(end)?.marker_id ?? '', transition_out: index === ordered.length - 2 ? 'fade' as const : 'cut' as const }];
  });
}

export function MusicVideoProductPanel({ projectId, onProjectChanged }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [audioSources, setAudioSources] = useState<ProjectReference[]>([]); const [musicMap, setMusicMap] = useState<MusicMapState | null>(null);
  const [direction, setDirection] = useState<MusicDirectionState | null>(null); const [audit, setAudit] = useState<RhythmAudit | null>(null);
  const [songId, setSongId] = useState(''); const [excerptStart, setExcerptStart] = useState('0'); const [excerptEnd, setExcerptEnd] = useState('30');
  const [sections, setSections] = useState<SectionDraft[]>([]); const [markers, setMarkers] = useState<MarkerDraft[]>([]); const [lyrics, setLyrics] = useState<LyricDraft[]>([]); const [shots, setShots] = useState<ShotDraft[]>([]);
  const [busy, setBusy] = useState(false); const [error, setError] = useState<string | null>(null); const [notice, setNotice] = useState<string | null>(null); const [directionWarning, setDirectionWarning] = useState(false);

  const refresh = useCallback(async () => {
    const [project, map] = await Promise.all([getUVProject(projectId), getMusicMap(projectId)]); const sources = project.sources.filter(reference => reference.kind === 'audio');
    setAudioSources(sources); setMusicMap(map); setSongId(current => current && sources.some(source => source.id === current) ? current : map?.song.reference_id ?? sources[0]?.id ?? '');
    if (map) { setExcerptStart(sec(map.excerpt.start_us)); setExcerptEnd(sec(map.excerpt.end_us)); setSections(hydrateSections(map)); setMarkers(hydrateMarkers(map)); setLyrics(hydrateLyrics(map)); }
    try {
      const dir = await getMusicDirection(projectId); setDirection(dir); setDirectionWarning(false);
      if (dir) { setShots(dir.shots.map(item => ({ shot_id: item.shot_id, start_us: item.start_us, end_us: item.end_us, intent: item.intent, sync_marker_id: item.sync_marker_ids[0] ?? '', transition_out: item.transition_out }))); setAudit(await getRhythmAudit(projectId)); } else setAudit(null);
    } catch { setDirection(null); setAudit(null); setDirectionWarning(true); }
  }, [projectId]);
  useEffect(() => { const timer = window.setTimeout(() => { void refresh().catch(reason => setError(reason instanceof Error ? reason.message : 'Не удалось загрузить музыкальный проект')); }, 0); return () => window.clearTimeout(timer); }, [refresh]);
  const selectedSong = useMemo(() => audioSources.find(source => source.id === songId) ?? null, [audioSources, songId]);
  const run = async (work: () => Promise<void>) => { setBusy(true); setError(null); setNotice(null); try { await work(); await refresh(); await onProjectChanged?.(); } catch (reason) { setError(reason instanceof Error ? reason.message : 'Операция не выполнена'); } finally { setBusy(false); } };

  const uploadSong = (file: File) => run(async () => { const reference = await uploadProjectAudioSource(projectId, file); setSongId(reference.id); setExcerptStart('0'); const duration = reference.metadata.duration_us; if (typeof duration === 'number') setExcerptEnd(sec(Math.min(duration, 30_000_000))); setSections([]); setMarkers([]); setLyrics([]); setShots([]); setNotice('Песня добавлена.'); });
  const saveMap = () => run(async () => {
    if (!songId) throw new Error('Сначала добавьте песню.'); const startUs = toUs(excerptStart, 'Начало'); const endUs = toUs(excerptEnd, 'Конец'); if (endUs <= startUs) throw new Error('Конец должен быть позже начала.');
    const sectionPayload: MusicSection[] = sections.map((item, index) => ({ section_id: item.section_id || `section_${index + 1}`, kind: item.kind, label: item.label.trim() || `Секция ${index + 1}`, start_us: toUs(item.start, 'Начало секции'), end_us: toUs(item.end, 'Конец секции') }));
    const markerPayload: MusicTimingMarker[] = markers.map((item, index) => ({ marker_id: item.marker_id || `marker_${index + 1}`, kind: item.kind, time_us: toUs(item.time, 'Время маркера') }));
    const lyricPayload: MusicLyricPhrase[] = lyrics.map((item, index) => ({ phrase_id: item.phrase_id || `phrase_${index + 1}`, start_us: toUs(item.start, 'Начало фразы'), end_us: toUs(item.end, 'Конец фразы'), text: item.text.trim() }));
    const result = await executeMusicMapCommand(projectId, { command: 'set_music_map', song_reference_id: songId, excerpt: { start_us: startUs, end_us: endUs }, sections: sectionPayload, markers: markerPayload, lyric_phrases: lyricPayload });
    const newMap = result.payload; if (!newMap) throw new Error('Разметка не сохранилась.'); if (direction && direction.music_map_revision_sha256 !== newMap.revision_sha256) await executeMusicDirectionCommand(projectId, { command: 'clear_music_direction' }); setNotice('Разметка музыки сохранена.');
  });
  const saveDirection = () => run(async () => { if (!musicMap || !shots.length) throw new Error('Сначала создайте кадры.'); const payload: MusicShotPlan[] = shots.map((shot, index) => ({ shot_id: shot.shot_id, order: index, start_us: shot.start_us, end_us: shot.end_us, intent: shot.intent.trim(), sync_marker_ids: shot.sync_marker_id ? [shot.sync_marker_id] : [], transition_out: shot.transition_out })); await executeMusicDirectionCommand(projectId, { command: 'set_music_direction', music_map_revision_sha256: musicMap.revision_sha256, shots: payload }); setNotice('Режиссёрский план сохранён.'); });

  return <section className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-0)] p-5 sm:p-6">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"><div className="flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-400/10 text-violet-300"><Music2 size={18}/></span><div><h2 className="text-lg font-medium text-zinc-100">Музыка и режиссура</h2><p className="mt-1 max-w-3xl text-sm leading-6 text-zinc-600">Разметьте структуру песни, точки монтажа и план кадров. Эти данные остаются частью проекта и не зависят от конкретного генератора.</p></div></div><button type="button" disabled={busy} onClick={() => void refresh()} className="secondary"><RefreshCw size={13}/> Обновить</button></div>
    {error && <Banner tone="error">{error}</Banner>}{notice && <Banner tone="ok">{notice}</Banner>}
    <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]"><div className="space-y-4">
      <Card n="1" title="Песня и рабочий фрагмент" desc="Выберите мастер-аудио и диапазон песни, который будет использован в клипе."><input ref={fileRef} type="file" accept="audio/*" className="hidden" aria-label="Файл песни" onChange={event => { const file = event.target.files?.[0]; if (file) void uploadSong(file); }}/><div className="flex flex-wrap gap-2"><button type="button" disabled={busy} onClick={() => fileRef.current?.click()} className="secondary"><Upload size={13}/> Добавить песню</button>{audioSources.length>0&&<select aria-label="Песня Music Video Mode" value={songId} onChange={event=>setSongId(event.target.value)} className="field min-w-56 flex-1">{audioSources.map(source=><option key={source.id} value={source.id}>{sourceName(source)}</option>)}</select>}</div>{selectedSong&&<audio className="mt-3 w-full" controls src={projectAudioUrl(projectId,selectedSong.id)}/>}<div className="mt-3 grid grid-cols-2 gap-2"><Num label="Начало, с" aria="Начало музыкального фрагмента" value={excerptStart} set={setExcerptStart}/><Num label="Конец, с" aria="Конец музыкального фрагмента" value={excerptEnd} set={setExcerptEnd}/></div></Card>
      <Card n="2" title="Структура песни" desc="Разбейте фрагмент на смысловые части."><div className="space-y-2">{sections.map((item,index)=><div key={item.section_id} className="grid gap-2 rounded-xl border border-[var(--uv-border)] bg-black/10 p-3 sm:grid-cols-[130px_1fr_90px_90px_auto]"><select aria-label={`Тип музыкальной секции ${index+1}`} value={item.kind} onChange={e=>setSections(c=>c.map((x,i)=>i===index?{...x,kind:e.target.value as MusicSectionKind}:x))} className="field">{sectionKinds.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select><input aria-label={`Название музыкальной секции ${index+1}`} value={item.label} onChange={e=>setSections(c=>c.map((x,i)=>i===index?{...x,label:e.target.value}:x))} className="field"/><input aria-label={`Начало музыкальной секции ${index+1}`} value={item.start} onChange={e=>setSections(c=>c.map((x,i)=>i===index?{...x,start:e.target.value}:x))} className="field"/><input aria-label={`Конец музыкальной секции ${index+1}`} value={item.end} onChange={e=>setSections(c=>c.map((x,i)=>i===index?{...x,end:e.target.value}:x))} className="field"/><button type="button" aria-label={`Удалить музыкальную секцию ${index+1}`} onClick={()=>setSections(c=>c.filter((_,i)=>i!==index))} className="icon"><Trash2 size={13}/></button></div>)}</div><button type="button" onClick={()=>setSections(c=>[...c,{section_id:`section_${c.length+1}`,kind:'other',label:`Секция ${c.length+1}`,start:excerptStart,end:excerptEnd}])} className="secondary mt-3"><Plus size={13}/> Добавить секцию</button></Card>
      <Card n="3" title="Точки монтажа" desc="Отметьте биты, акценты и естественные места смены кадра."><div className="space-y-2">{markers.map((item,index)=><div key={item.marker_id} className="grid gap-2 rounded-xl border border-[var(--uv-border)] bg-black/10 p-3 sm:grid-cols-[1fr_100px_auto]"><select aria-label={`Тип музыкального маркера ${index+1}`} value={item.kind} onChange={e=>setMarkers(c=>c.map((x,i)=>i===index?{...x,kind:e.target.value as MusicMarkerKind}:x))} className="field">{markerKinds.map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select><input aria-label={`Время музыкального маркера ${index+1}`} value={item.time} onChange={e=>setMarkers(c=>c.map((x,i)=>i===index?{...x,time:e.target.value}:x))} className="field"/><button type="button" onClick={()=>setMarkers(c=>c.filter((_,i)=>i!==index))} className="icon"><Trash2 size={13}/></button></div>)}</div><button type="button" onClick={()=>setMarkers(c=>[...c,{marker_id:`marker_${c.length+1}`,kind:'beat',time:excerptStart}])} className="secondary mt-3"><Plus size={13}/> Добавить маркер</button></Card>
      <details className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><summary className="cursor-pointer text-sm font-medium text-zinc-400">Текст / вокальные фразы <span className="text-xs text-zinc-700">необязательно</span></summary><div className="mt-3 space-y-2">{lyrics.map((x,i)=><div key={x.phrase_id} className="grid gap-2 sm:grid-cols-[90px_90px_1fr_auto]"><input value={x.start} onChange={e=>setLyrics(c=>c.map((v,j)=>j===i?{...v,start:e.target.value}:v))} className="field"/><input value={x.end} onChange={e=>setLyrics(c=>c.map((v,j)=>j===i?{...v,end:e.target.value}:v))} className="field"/><input value={x.text} onChange={e=>setLyrics(c=>c.map((v,j)=>j===i?{...v,text:e.target.value}:v))} className="field"/><button type="button" onClick={()=>setLyrics(c=>c.filter((_,j)=>j!==i))} className="icon"><Trash2 size={13}/></button></div>)}</div><button type="button" onClick={()=>setLyrics(c=>[...c,{phrase_id:`phrase_${c.length+1}`,start:excerptStart,end:excerptEnd,text:''}])} className="secondary mt-3"><Plus size={13}/> Добавить фразу</button></details>
      <button type="button" disabled={busy||!songId} onClick={saveMap} className="primary w-full">{busy?<Loader2 size={14} className="animate-spin"/>:<ListMusic size={14}/>} Сохранить разметку музыки</button>
    </div><div><Card n="4" title="Режиссёрский план" desc="Сформируйте кадры по структуре песни и опишите визуальный замысел каждого.">{!musicMap?<Hint>Сначала сохраните разметку музыки.</Hint>:<><button type="button" disabled={busy} onClick={()=>{setShots(makeShots(musicMap));setNotice('Черновик кадров создан.');}} className="secondary"><Sparkles size={13}/> Создать черновик кадров</button>{directionWarning&&<div className="mt-3 rounded-xl border border-amber-400/15 bg-amber-400/[0.05] p-3 text-xs text-amber-100/75">Разметка изменилась — проверьте и сохраните новый план.</div>}<div className="mt-4 space-y-2">{shots.map((shot,index)=><div key={shot.shot_id} className="rounded-xl border border-[var(--uv-border)] bg-black/10 p-3"><div className="flex items-center justify-between"><div><p className="text-xs font-medium text-zinc-300">Кадр {index+1}</p><p className="text-[10px] text-zinc-700">{sec(shot.start_us)}–{sec(shot.end_us)} с</p></div><select aria-label={`Переход музыкального кадра ${index+1}`} value={shot.transition_out} onChange={e=>setShots(c=>c.map((x,i)=>i===index?{...x,transition_out:e.target.value as MusicTransition}:x))} className="field w-32">{Object.entries(transitions).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></div><textarea aria-label={`Замысел музыкального кадра ${index+1}`} value={shot.intent} onChange={e=>setShots(c=>c.map((x,i)=>i===index?{...x,intent:e.target.value}:x))} rows={3} className="field mt-2"/></div>)}</div>{shots.length>0&&<button type="button" disabled={busy||shots.some(s=>!s.intent.trim())} onClick={saveDirection} className="primary mt-4 w-full">Сохранить режиссёрский план</button>}</>}</Card>{direction&&<div className="mt-4 rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><h3 className="text-sm font-medium text-zinc-200">Проверка ритма</h3><p className="mt-1 text-xs text-zinc-600">{!audit?'Проверяем…':audit.summary.cut_count===0?'Нет промежуточных склеек для проверки.':audit.summary.all_aligned?`Все ${audit.summary.cut_count} границ совпадают с музыкальными точками.`:`${audit.summary.unaligned_count} границ требуют внимания.`}</p></div>}</div></div>
    <style jsx global>{`.field{border:1px solid var(--uv-border);border-radius:9px;background:rgba(0,0,0,.18);padding:8px 10px;color:#d4d4d8;font-size:12px}.primary,.secondary{display:inline-flex;align-items:center;justify-content:center;gap:6px;border-radius:9px;font-size:11px}.primary{background:var(--uv-accent);padding:10px 14px;color:#090a0d;font-weight:650}.secondary{border:1px solid var(--uv-border-strong);padding:8px 11px;color:#a1a1aa}.primary:disabled{background:#27272a;color:#52525b}.icon{display:inline-flex;height:32px;width:32px;align-items:center;justify-content:center;color:#52525b}`}</style>
  </section>;
}
function Card({n,title,desc,children}:{n:string;title:string;desc:string;children:React.ReactNode}){return <div className="rounded-2xl border border-[var(--uv-border)] bg-[var(--uv-surface-1)] p-4"><div className="flex gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-400/10 text-xs text-violet-300">{n}</span><div><h3 className="text-sm font-medium text-zinc-200">{title}</h3><p className="mt-1 text-xs text-zinc-700">{desc}</p></div></div><div className="mt-4">{children}</div></div>}
function Num({label,aria,value,set}:{label:string;aria:string;value:string;set:(v:string)=>void}){return <label className="text-[11px] text-zinc-600">{label}<input aria-label={aria} value={value} onChange={e=>set(e.target.value)} className="field mt-1.5 w-full"/></label>}
function Hint({children}:{children:React.ReactNode}){return <div className="rounded-xl border border-dashed border-[var(--uv-border)] p-4 text-xs text-zinc-700">{children}</div>}
function Banner({tone,children}:{tone:'ok'|'error';children:React.ReactNode}){return <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${tone==='ok'?'border-emerald-400/20 bg-emerald-400/[0.06] text-emerald-200':'border-rose-400/20 bg-rose-400/[0.06] text-rose-200'}`}>{children}</div>}
