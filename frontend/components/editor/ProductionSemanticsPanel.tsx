'use client';

import {
  BookOpen,
  Check,
  Clapperboard,
  Loader2,
  MapPin,
  Plus,
  RefreshCw,
  UserRound,
  Video,
  X,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ProjectReference, UVProject } from '@/lib/projectsApi';
import {
  executeProductionCommand,
  getMicroDramaDocument,
  getProductionSemantics,
  type MicroDramaCharacter,
  type MicroDramaDocument,
  type MicroDramaLocation,
  type MicroDramaSceneContinuity,
  type ProductionSemantics,
  type ProductionShot,
  type ProductionTake,
} from '@/lib/productionApi';

const IMAGE_DEFAULT_DURATION_US = 3_000_000;

function createId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID()}`;
}

function metadataNumber(reference: ProjectReference | null, key: string): number | null {
  if (!reference) return null;
  const value = reference.metadata[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function metadataText(reference: ProjectReference | null, key: string): string | null {
  if (!reference) return null;
  const value = reference.metadata[key];
  return typeof value === 'string' && value.trim() ? value : null;
}

function referenceLabel(reference: ProjectReference): string {
  return metadataText(reference, 'original_name') ?? reference.id;
}

function takeDuration(reference: ProjectReference | null): number | null {
  if (!reference) return null;
  if (reference.kind === 'image') return IMAGE_DEFAULT_DURATION_US;
  if (reference.kind !== 'video') return null;
  const duration = metadataNumber(reference, 'duration_us');
  return duration && duration > 0 ? Math.round(duration) : null;
}

function seconds(us: number): string {
  return (us / 1_000_000).toFixed(us % 1_000_000 === 0 ? 0 : 2);
}

interface ProductionSemanticsPanelProps {
  projectId: string;
  project: UVProject;
  selectedSource: ProjectReference | null;
  timelineDurationUs: number;
  historyCursor: number;
  onProjectChanged: () => Promise<unknown>;
}

export function ProductionSemanticsPanel({
  projectId,
  project,
  selectedSource,
  timelineDurationUs,
  historyCursor,
  onProjectChanged,
}: ProductionSemanticsPanelProps) {
  const directionId = project.product_identity.direction_id;
  const isMicroDrama = directionId === 'micro_drama';
  const [production, setProduction] = useState<ProductionSemantics | null>(null);
  const [microDrama, setMicroDrama] = useState<MicroDramaDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [sceneTitle, setSceneTitle] = useState('');
  const [sceneSummary, setSceneSummary] = useState('');
  const [shotSceneId, setShotSceneId] = useState('');
  const [shotIntent, setShotIntent] = useState('');
  const [takeShotId, setTakeShotId] = useState('');

  const [storyTitle, setStoryTitle] = useState('');
  const [storyPremise, setStoryPremise] = useState('');
  const [storySynopsis, setStorySynopsis] = useState('');
  const [characters, setCharacters] = useState<MicroDramaCharacter[]>([]);
  const [locations, setLocations] = useState<MicroDramaLocation[]>([]);
  const [continuity, setContinuity] = useState<MicroDramaSceneContinuity[]>([]);
  const [characterName, setCharacterName] = useState('');
  const [characterDescription, setCharacterDescription] = useState('');
  const [locationName, setLocationName] = useState('');
  const [locationDescription, setLocationDescription] = useState('');
  const [continuitySceneId, setContinuitySceneId] = useState('');
  const [continuityLocationId, setContinuityLocationId] = useState('');
  const [continuityCharacterIds, setContinuityCharacterIds] = useState<string[]>([]);
  const [canonFactsText, setCanonFactsText] = useState('');
  const [continuityNotes, setContinuityNotes] = useState('');

  const hydrateMicroDrama = useCallback((document: MicroDramaDocument) => {
    setMicroDrama(document);
    setStoryTitle(document.story?.title ?? '');
    setStoryPremise(document.story?.premise ?? '');
    setStorySynopsis(document.story?.synopsis ?? '');
    setCharacters(document.characters);
    setLocations(document.locations);
    setContinuity(document.scene_continuity);
  }, []);

  const load = useCallback(async () => {
    const productionValue = await getProductionSemantics(projectId);
    setProduction(productionValue);
    setShotSceneId(current =>
      current && productionValue.scenes.some(scene => scene.scene_id === current)
        ? current
        : productionValue.scenes[0]?.scene_id ?? '',
    );
    setTakeShotId(current =>
      current && productionValue.shots.some(shot => shot.shot_id === current)
        ? current
        : productionValue.shots[0]?.shot_id ?? '',
    );
    setContinuitySceneId(current =>
      current && productionValue.scenes.some(scene => scene.scene_id === current)
        ? current
        : productionValue.scenes[0]?.scene_id ?? '',
    );
    if (isMicroDrama) {
      hydrateMicroDrama(await getMicroDramaDocument(projectId));
    } else {
      setMicroDrama(null);
    }
  }, [hydrateMicroDrama, isMicroDrama, projectId]);

  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void load()
        .catch(err => {
          if (active) {
            setError(err instanceof Error ? err.message : 'Не удалось загрузить структуру производства');
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 0);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [historyCursor, load]);

  useEffect(() => {
    if (!continuitySceneId) {
      setContinuityLocationId('');
      setContinuityCharacterIds([]);
      setCanonFactsText('');
      setContinuityNotes('');
      return;
    }
    const current = continuity.find(item => item.scene_id === continuitySceneId);
    setContinuityLocationId(current?.location_id ?? '');
    setContinuityCharacterIds(current?.character_ids ?? []);
    setCanonFactsText(current?.canon_facts.join('\n') ?? '');
    setContinuityNotes(current?.notes ?? '');
  }, [continuity, continuitySceneId]);

  const referenceById = useCallback((referenceId: string): ProjectReference | null => {
    return project.sources.find(item => item.id === referenceId)
      ?? project.artifacts.find(item => item.id === referenceId)
      ?? null;
  }, [project.artifacts, project.sources]);

  const selectedVisualSource = useMemo(() => {
    if (!selectedSource) return null;
    return selectedSource.kind === 'video' || selectedSource.kind === 'image' ? selectedSource : null;
  }, [selectedSource]);

  async function mutate(operation: () => Promise<unknown>) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await operation();
      await Promise.all([load(), onProjectChanged()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось изменить производственную структуру');
    } finally {
      setBusy(false);
    }
  }

  function createScene() {
    const title = sceneTitle.trim();
    if (!title) {
      setError('Введите название сцены.');
      return;
    }
    void mutate(async () => {
      const result = await executeProductionCommand(projectId, {
        command: 'create_scene',
        scene_id: createId('scene'),
        title,
        summary: sceneSummary.trim(),
      });
      setProduction(result.production);
      setSceneTitle('');
      setSceneSummary('');
    });
  }

  function createShot() {
    const intent = shotIntent.trim();
    if (!shotSceneId || !intent) {
      setError('Выберите сцену и опишите замысел кадра.');
      return;
    }
    void mutate(async () => {
      const result = await executeProductionCommand(projectId, {
        command: 'create_shot',
        shot_id: createId('shot'),
        scene_id: shotSceneId,
        intent,
        reference_ids: selectedVisualSource ? [selectedVisualSource.id] : [],
      });
      setProduction(result.production);
      setShotIntent('');
    });
  }

  function registerTake() {
    if (!takeShotId || !selectedVisualSource) {
      setError('Выберите кадр и видео/изображение в Media Bin.');
      return;
    }
    void mutate(async () => {
      const result = await executeProductionCommand(projectId, {
        command: 'register_take',
        take_id: createId('take'),
        shot_id: takeShotId,
        reference_id: selectedVisualSource.id,
        label: referenceLabel(selectedVisualSource),
      });
      setProduction(result.production);
    });
  }

  function acceptTake(shot: ProductionShot, take: ProductionTake) {
    if (shot.accepted_take_id) return;
    const reference = referenceById(take.reference_id);
    const durationUs = takeDuration(reference);
    if (!reference || !durationUs) {
      setError('Для этого дубля не удалось определить безопасную длительность.');
      return;
    }
    void mutate(async () => {
      const result = await executeProductionCommand(projectId, {
        command: 'accept_take',
        take_id: take.take_id,
        timeline_start_us: timelineDurationUs,
        source_start_us: 0,
        duration_us: durationUs,
      });
      setProduction(result.production);
    });
  }

  function addCharacter() {
    const name = characterName.trim();
    if (!name) return;
    setCharacters(current => [
      ...current,
      {
        character_id: createId('char'),
        name,
        description: characterDescription.trim(),
      },
    ]);
    setCharacterName('');
    setCharacterDescription('');
  }

  function removeCharacter(characterId: string) {
    setCharacters(current => current.filter(item => item.character_id !== characterId));
    setContinuity(current => current.map(item => ({
      ...item,
      character_ids: item.character_ids.filter(id => id !== characterId),
    })));
    setContinuityCharacterIds(current => current.filter(id => id !== characterId));
  }

  function addLocation() {
    const name = locationName.trim();
    if (!name) return;
    setLocations(current => [
      ...current,
      {
        location_id: createId('loc'),
        name,
        description: locationDescription.trim(),
      },
    ]);
    setLocationName('');
    setLocationDescription('');
  }

  function removeLocation(locationId: string) {
    setLocations(current => current.filter(item => item.location_id !== locationId));
    setContinuity(current => current.map(item => (
      item.location_id === locationId ? { ...item, location_id: null } : item
    )));
    if (continuityLocationId === locationId) setContinuityLocationId('');
  }

  function toggleContinuityCharacter(characterId: string) {
    setContinuityCharacterIds(current =>
      current.includes(characterId)
        ? current.filter(item => item !== characterId)
        : [...current, characterId],
    );
  }

  function saveMicroDrama() {
    if (!isMicroDrama) return;
    const cleanStoryTitle = storyTitle.trim();
    const cleanPremise = storyPremise.trim();
    const cleanSynopsis = storySynopsis.trim();
    if (!cleanStoryTitle && (cleanPremise || cleanSynopsis)) {
      setError('Если заполнена история, укажите её название.');
      return;
    }

    const canonFacts = canonFactsText
      .split('\n')
      .map(item => item.trim())
      .filter(Boolean);
    const nextContinuity = continuitySceneId
      ? [
          ...continuity.filter(item => item.scene_id !== continuitySceneId),
          {
            scene_id: continuitySceneId,
            character_ids: continuityCharacterIds,
            location_id: continuityLocationId || null,
            canon_facts: Array.from(new Set(canonFacts)),
            notes: continuityNotes.trim(),
          },
        ]
      : continuity;

    void mutate(async () => {
      const result = await executeProductionCommand(projectId, {
        command: 'set_micro_drama_context',
        document: {
          story: cleanStoryTitle
            ? { title: cleanStoryTitle, premise: cleanPremise, synopsis: cleanSynopsis }
            : null,
          characters,
          locations,
          scene_continuity: nextContinuity,
        },
      });
      if (result.micro_drama) hydrateMicroDrama(result.micro_drama);
    });
  }

  if (project.product_identity.kind !== 'modern_direction' || !directionId) return null;

  if (loading) {
    return (
      <section className="mb-3 rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <Loader2 size={16} className="animate-spin" /> Загружаем структуру производства…
        </div>
      </section>
    );
  }

  if (!production) {
    return (
      <section className="mb-3 rounded-2xl border border-red-900/70 bg-red-950/30 p-4 text-sm text-red-200">
        {error ?? 'Производственная структура недоступна.'}
      </section>
    );
  }

  return (
    <section className="mb-3 rounded-2xl border border-slate-800 bg-slate-900/55 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Clapperboard size={17} className="text-sky-300" />
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Production</p>
            <span className="rounded-full border border-slate-700 bg-slate-950 px-2 py-1 font-mono text-[10px] text-slate-500">
              {directionId}
            </span>
          </div>
          <h2 className="mt-2 text-base font-semibold text-slate-200">Сцены, кадры и дубли</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
            Кадр хранит производственный замысел и варианты дублей. Timeline остаётся монтажным представлением и получает только принятый материал.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load().catch(err => setError(err instanceof Error ? err.message : 'Не удалось обновить данные'))}
          disabled={busy}
          className="inline-flex items-center gap-2 self-start rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-400 hover:border-sky-700 hover:text-sky-300 disabled:opacity-40"
        >
          <RefreshCw size={13} /> Обновить
        </button>
      </div>

      {error ? (
        <div className="mt-3 rounded-xl border border-red-900/70 bg-red-950/35 px-3 py-2 text-xs text-red-200">
          {error}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 xl:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">1. Сцена</p>
          <input
            aria-label="Название новой сцены"
            value={sceneTitle}
            onChange={event => setSceneTitle(event.target.value)}
            placeholder="Например: Встреча в кафе"
            className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500"
          />
          <textarea
            aria-label="Описание новой сцены"
            value={sceneSummary}
            onChange={event => setSceneSummary(event.target.value)}
            placeholder="Что происходит в сцене"
            rows={2}
            className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-sky-500"
          />
          <button
            type="button"
            onClick={createScene}
            disabled={busy || !sceneTitle.trim()}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 py-2 text-xs text-slate-300 hover:border-sky-600 disabled:opacity-35"
          >
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Plus size={13} />} Добавить сцену
          </button>
          <div className="mt-3 space-y-1.5">
            {production.scenes.map(scene => (
              <button
                type="button"
                key={scene.scene_id}
                onClick={() => {
                  setShotSceneId(scene.scene_id);
                  setContinuitySceneId(scene.scene_id);
                }}
                className={`w-full rounded-lg border px-3 py-2 text-left text-xs ${
                  shotSceneId === scene.scene_id
                    ? 'border-sky-700 bg-sky-950/30 text-sky-200'
                    : 'border-slate-800 bg-slate-950/50 text-slate-400 hover:border-slate-700'
                }`}
              >
                <span className="block truncate">{scene.title}</span>
                <span className="mt-1 block font-mono text-[9px] text-slate-600">{scene.shot_ids.length} shots</span>
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">2. Кадр</p>
          <select
            aria-label="Сцена для нового кадра"
            value={shotSceneId}
            onChange={event => setShotSceneId(event.target.value)}
            className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-sky-500"
          >
            <option value="">Выберите сцену</option>
            {production.scenes.map(scene => (
              <option key={scene.scene_id} value={scene.scene_id}>{scene.title}</option>
            ))}
          </select>
          <textarea
            aria-label="Замысел нового кадра"
            value={shotIntent}
            onChange={event => setShotIntent(event.target.value)}
            placeholder="Крупность, действие, камера, драматургическая цель…"
            rows={3}
            className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-sky-500"
          />
          <p className="mt-2 text-[10px] leading-4 text-slate-600">
            {selectedVisualSource
              ? `Выбранное медиа станет референсом: ${referenceLabel(selectedVisualSource)}`
              : 'Можно создать кадр без медиа-референса.'}
          </p>
          <button
            type="button"
            onClick={createShot}
            disabled={busy || !shotSceneId || !shotIntent.trim()}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 py-2 text-xs text-slate-300 hover:border-sky-600 disabled:opacity-35"
          >
            <Plus size={13} /> Добавить кадр
          </button>
          <div className="mt-3 space-y-1.5">
            {production.shots.map(shot => {
              const scene = production.scenes.find(item => item.scene_id === shot.scene_id);
              return (
                <button
                  type="button"
                  key={shot.shot_id}
                  onClick={() => setTakeShotId(shot.shot_id)}
                  className={`w-full rounded-lg border px-3 py-2 text-left ${
                    takeShotId === shot.shot_id
                      ? 'border-violet-700 bg-violet-950/25'
                      : 'border-slate-800 bg-slate-950/50 hover:border-slate-700'
                  }`}
                >
                  <span className="block text-[10px] text-slate-600">{scene?.title ?? shot.scene_id}</span>
                  <span className="mt-1 block line-clamp-2 text-xs text-slate-300">{shot.intent}</span>
                  <span className="mt-1 block font-mono text-[9px] text-slate-600">
                    {shot.take_ids.length} takes · {shot.accepted_take_id ? 'accepted' : 'not accepted'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">3. Дубли и принятие</p>
          <select
            aria-label="Кадр для нового дубля"
            value={takeShotId}
            onChange={event => setTakeShotId(event.target.value)}
            className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-violet-500"
          >
            <option value="">Выберите кадр</option>
            {production.shots.map(shot => (
              <option key={shot.shot_id} value={shot.shot_id}>{shot.intent}</option>
            ))}
          </select>
          <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-500">
            {selectedVisualSource ? (
              <span className="flex items-center gap-2 text-slate-300">
                <Video size={13} className="text-violet-300" />
                <span className="min-w-0 truncate">{referenceLabel(selectedVisualSource)}</span>
              </span>
            ) : (
              'Выберите видео или изображение в Media Bin.'
            )}
          </div>
          <button
            type="button"
            onClick={registerTake}
            disabled={busy || !takeShotId || !selectedVisualSource}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-violet-800/70 py-2 text-xs text-violet-200 hover:border-violet-600 disabled:opacity-35"
          >
            <Plus size={13} /> Добавить как дубль
          </button>

          <div className="mt-3 space-y-2">
            {production.shots.map(shot => {
              const takes = shot.take_ids
                .map(takeId => production.takes.find(item => item.take_id === takeId) ?? null)
                .filter((item): item is ProductionTake => item !== null);
              if (takes.length === 0) return null;
              return (
                <div key={shot.shot_id} className="rounded-lg border border-slate-800 bg-slate-950/55 p-2.5">
                  <p className="line-clamp-1 text-[10px] text-slate-500">{shot.intent}</p>
                  <div className="mt-2 space-y-1.5">
                    {takes.map(take => {
                      const reference = referenceById(take.reference_id);
                      const accepted = shot.accepted_take_id === take.take_id;
                      return (
                        <div key={take.take_id} className="flex items-center gap-2 rounded-md border border-slate-800 px-2 py-2">
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-xs text-slate-300">{take.label || reference?.id || take.take_id}</p>
                            <p className="mt-0.5 font-mono text-[9px] text-slate-700">
                              {reference ? `${reference.kind} · ${takeDuration(reference) ? `${seconds(takeDuration(reference) ?? 0)}s` : 'duration?'}` : 'reference missing'}
                            </p>
                          </div>
                          {accepted ? (
                            <span className="inline-flex items-center gap-1 rounded-md border border-emerald-800/70 bg-emerald-950/35 px-2 py-1 text-[10px] text-emerald-300">
                              <Check size={11} /> Принят
                            </span>
                          ) : shot.accepted_take_id ? null : (
                            <button
                              type="button"
                              onClick={() => acceptTake(shot, take)}
                              disabled={busy || !takeDuration(reference)}
                              className="rounded-md bg-emerald-400 px-2 py-1 text-[10px] font-semibold text-slate-950 hover:bg-emerald-300 disabled:opacity-35"
                              title={`Добавить в конец timeline с ${seconds(timelineDurationUs)} сек`}
                            >
                              Принять
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {isMicroDrama && microDrama ? (
        <div className="mt-4 border-t border-slate-800 pt-4">
          <div className="flex items-center gap-2">
            <BookOpen size={16} className="text-amber-300" />
            <div>
              <p className="text-sm font-medium text-slate-200">Мини-драма: история и канон</p>
              <p className="mt-0.5 text-[10px] text-slate-600">Эти данные расширяют общие Scene/Shot/Take, а не заменяют их.</p>
            </div>
          </div>

          <div className="mt-3 grid gap-3 xl:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
              <p className="text-xs text-slate-400">История</p>
              <input
                aria-label="Название истории"
                value={storyTitle}
                onChange={event => setStoryTitle(event.target.value)}
                placeholder="Название"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-600"
              />
              <textarea
                aria-label="Премиса истории"
                value={storyPremise}
                onChange={event => setStoryPremise(event.target.value)}
                placeholder="Премиса"
                rows={2}
                className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
              />
              <textarea
                aria-label="Синопсис истории"
                value={storySynopsis}
                onChange={event => setStorySynopsis(event.target.value)}
                placeholder="Краткий синопсис"
                rows={3}
                className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
              />
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
              <div className="flex items-center gap-2 text-xs text-slate-400"><UserRound size={13} /> Персонажи</div>
              <input
                aria-label="Имя нового персонажа"
                value={characterName}
                onChange={event => setCharacterName(event.target.value)}
                placeholder="Имя персонажа"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-600"
              />
              <input
                aria-label="Описание нового персонажа"
                value={characterDescription}
                onChange={event => setCharacterDescription(event.target.value)}
                placeholder="Короткое описание"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
              />
              <button
                type="button"
                onClick={addCharacter}
                disabled={!characterName.trim()}
                className="mt-2 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-slate-700 py-2 text-[11px] text-slate-300 hover:border-amber-700 disabled:opacity-35"
              >
                <Plus size={12} /> Добавить персонажа
              </button>
              <div className="mt-2 space-y-1">
                {characters.map(character => (
                  <div key={character.character_id} className="flex items-center gap-2 rounded-md border border-slate-800 px-2 py-1.5">
                    <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300">{character.name}</span>
                    <button
                      type="button"
                      onClick={() => removeCharacter(character.character_id)}
                      aria-label={`Удалить персонажа ${character.name}`}
                      className="text-slate-600 hover:text-red-300"
                    ><X size={12} /></button>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
              <div className="flex items-center gap-2 text-xs text-slate-400"><MapPin size={13} /> Локации</div>
              <input
                aria-label="Название новой локации"
                value={locationName}
                onChange={event => setLocationName(event.target.value)}
                placeholder="Название локации"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-200 outline-none focus:border-amber-600"
              />
              <input
                aria-label="Описание новой локации"
                value={locationDescription}
                onChange={event => setLocationDescription(event.target.value)}
                placeholder="Короткое описание"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
              />
              <button
                type="button"
                onClick={addLocation}
                disabled={!locationName.trim()}
                className="mt-2 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-slate-700 py-2 text-[11px] text-slate-300 hover:border-amber-700 disabled:opacity-35"
              >
                <Plus size={12} /> Добавить локацию
              </button>
              <div className="mt-2 space-y-1">
                {locations.map(location => (
                  <div key={location.location_id} className="flex items-center gap-2 rounded-md border border-slate-800 px-2 py-1.5">
                    <span className="min-w-0 flex-1 truncate text-[11px] text-slate-300">{location.name}</span>
                    <button
                      type="button"
                      onClick={() => removeLocation(location.location_id)}
                      aria-label={`Удалить локацию ${location.name}`}
                      className="text-slate-600 hover:text-red-300"
                    ><X size={12} /></button>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/45 p-3">
            <p className="text-xs text-slate-400">Непрерывность выбранной сцены</p>
            <div className="mt-2 grid gap-2 lg:grid-cols-2">
              <select
                aria-label="Сцена для непрерывности"
                value={continuitySceneId}
                onChange={event => setContinuitySceneId(event.target.value)}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
              >
                <option value="">Выберите сцену</option>
                {production.scenes.map(scene => (
                  <option key={scene.scene_id} value={scene.scene_id}>{scene.title}</option>
                ))}
              </select>
              <select
                aria-label="Локация сцены"
                value={continuityLocationId}
                onChange={event => setContinuityLocationId(event.target.value)}
                disabled={!continuitySceneId}
                className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
              >
                <option value="">Локация не задана</option>
                {locations.map(location => (
                  <option key={location.location_id} value={location.location_id}>{location.name}</option>
                ))}
              </select>
            </div>
            {characters.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {characters.map(character => {
                  const active = continuityCharacterIds.includes(character.character_id);
                  return (
                    <button
                      type="button"
                      key={character.character_id}
                      onClick={() => toggleContinuityCharacter(character.character_id)}
                      disabled={!continuitySceneId}
                      className={`rounded-full border px-2 py-1 text-[10px] ${
                        active
                          ? 'border-amber-700 bg-amber-950/40 text-amber-200'
                          : 'border-slate-700 text-slate-500 hover:border-slate-600'
                      } disabled:opacity-40`}
                    >
                      {character.name}
                    </button>
                  );
                })}
              </div>
            ) : null}
            <textarea
              aria-label="Канонические факты сцены"
              value={canonFactsText}
              onChange={event => setCanonFactsText(event.target.value)}
              disabled={!continuitySceneId}
              placeholder="Один канонический факт на строку"
              rows={3}
              className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
            />
            <textarea
              aria-label="Заметки по непрерывности сцены"
              value={continuityNotes}
              onChange={event => setContinuityNotes(event.target.value)}
              disabled={!continuitySceneId}
              placeholder="Костюм, реквизит, состояние персонажей, свет…"
              rows={2}
              className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
            />
            <button
              type="button"
              onClick={saveMicroDrama}
              disabled={busy}
              className="mt-2 inline-flex items-center gap-2 rounded-lg bg-amber-300 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-amber-200 disabled:opacity-40"
            >
              {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Сохранить историю и канон
            </button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
