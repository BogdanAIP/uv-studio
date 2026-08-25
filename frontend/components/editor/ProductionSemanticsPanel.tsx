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

interface ContinuityDraft {
  sceneId: string;
  locationId: string;
  characterIds: string[];
  canonFactsText: string;
  notes: string;
}

const EMPTY_CONTINUITY_DRAFT: ContinuityDraft = {
  sceneId: '',
  locationId: '',
  characterIds: [],
  canonFactsText: '',
  notes: '',
};

function continuityDraft(
  sceneId: string,
  entries: MicroDramaSceneContinuity[],
): ContinuityDraft {
  if (!sceneId) return EMPTY_CONTINUITY_DRAFT;
  const saved = entries.find(item => item.scene_id === sceneId);
  return {
    sceneId,
    locationId: saved?.location_id ?? '',
    characterIds: saved?.character_ids ?? [],
    canonFactsText: saved?.canon_facts.join('\n') ?? '',
    notes: saved?.notes ?? '',
  };
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
  const [continuityForm, setContinuityForm] = useState<ContinuityDraft>(EMPTY_CONTINUITY_DRAFT);

  const hydrateMicroDrama = useCallback((document: MicroDramaDocument, sceneIds: string[]) => {
    setMicroDrama(document);
    setStoryTitle(document.story?.title ?? '');
    setStoryPremise(document.story?.premise ?? '');
    setStorySynopsis(document.story?.synopsis ?? '');
    setCharacters(document.characters);
    setLocations(document.locations);
    setContinuity(document.scene_continuity);
    setContinuityForm(current => {
      const sceneId = current.sceneId && sceneIds.includes(current.sceneId)
        ? current.sceneId
        : sceneIds[0] ?? '';
      return continuityDraft(sceneId, document.scene_continuity);
    });
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
    if (isMicroDrama) {
      const document = await getMicroDramaDocument(projectId);
      hydrateMicroDrama(document, productionValue.scenes.map(scene => scene.scene_id));
    } else {
      setMicroDrama(null);
      setContinuityForm(EMPTY_CONTINUITY_DRAFT);
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
      { character_id: createId('char'), name, description: characterDescription.trim() },
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
    setContinuityForm(current => ({
      ...current,
      characterIds: current.characterIds.filter(id => id !== characterId),
    }));
  }

  function addLocation() {
    const name = locationName.trim();
    if (!name) return;
    setLocations(current => [
      ...current,
      { location_id: createId('loc'), name, description: locationDescription.trim() },
    ]);
    setLocationName('');
    setLocationDescription('');
  }

  function removeLocation(locationId: string) {
    setLocations(current => current.filter(item => item.location_id !== locationId));
    setContinuity(current => current.map(item => (
      item.location_id === locationId ? { ...item, location_id: null } : item
    )));
    setContinuityForm(current => ({
      ...current,
      locationId: current.locationId === locationId ? '' : current.locationId,
    }));
  }

  function selectContinuityScene(sceneId: string) {
    setContinuityForm(continuityDraft(sceneId, continuity));
  }

  function toggleContinuityCharacter(characterId: string) {
    setContinuityForm(current => ({
      ...current,
      characterIds: current.characterIds.includes(characterId)
        ? current.characterIds.filter(item => item !== characterId)
        : [...current.characterIds, characterId],
    }));
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

    const canonFacts = continuityForm.canonFactsText
      .split('\n')
      .map(item => item.trim())
      .filter(Boolean);
    const nextContinuity = continuityForm.sceneId
      ? [
          ...continuity.filter(item => item.scene_id !== continuityForm.sceneId),
          {
            scene_id: continuityForm.sceneId,
            character_ids: continuityForm.characterIds,
            location_id: continuityForm.locationId || null,
            canon_facts: Array.from(new Set(canonFacts)),
            notes: continuityForm.notes.trim(),
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
      if (result.micro_drama && production) {
        hydrateMicroDrama(result.micro_drama, production.scenes.map(scene => scene.scene_id));
      }
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
            Кадр хранит производственный замысел и варианты дублей. Timeline получает только принятый материал.
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

      {error && (
        <div className="mt-3 rounded-lg border border-red-900/70 bg-red-950/30 px-3 py-2 text-xs text-red-200">
          {error}
        </div>
      )}

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">1. Сцена</p>
          <input
            aria-label="Название production-сцены"
            value={sceneTitle}
            onChange={event => setSceneTitle(event.target.value)}
            placeholder="Например: Встреча на платформе"
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-sky-600"
          />
          <textarea
            aria-label="Краткое описание production-сцены"
            value={sceneSummary}
            onChange={event => setSceneSummary(event.target.value)}
            placeholder="Что происходит в сцене"
            rows={2}
            className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-sky-600"
          />
          <button
            type="button"
            onClick={createScene}
            disabled={busy || !sceneTitle.trim()}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-400 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
          >
            <Plus size={13} /> Создать сцену
          </button>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">2. Кадр</p>
          <select
            aria-label="Сцена для кадра"
            value={shotSceneId}
            onChange={event => setShotSceneId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-sky-600"
          >
            <option value="">Выберите сцену</option>
            {production.scenes.map(scene => (
              <option key={scene.scene_id} value={scene.scene_id}>{scene.title}</option>
            ))}
          </select>
          <textarea
            aria-label="Замысел production-кадра"
            value={shotIntent}
            onChange={event => setShotIntent(event.target.value)}
            placeholder="Крупность, действие, камера, смысл"
            rows={2}
            className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-sky-600"
          />
          <button
            type="button"
            onClick={createShot}
            disabled={busy || !shotSceneId || !shotIntent.trim()}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-400 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
          >
            <Plus size={13} /> Создать кадр
          </button>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-950/45 p-3">
          <p className="text-xs font-medium text-slate-300">3. Дубль</p>
          <select
            aria-label="Кадр для дубля"
            value={takeShotId}
            onChange={event => setTakeShotId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-sky-600"
          >
            <option value="">Выберите кадр</option>
            {production.shots.map(shot => (
              <option key={shot.shot_id} value={shot.shot_id}>{shot.intent}</option>
            ))}
          </select>
          <div className="mt-2 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-500">
            {selectedVisualSource ? (
              <span className="inline-flex items-center gap-2 text-slate-300">
                <Video size={13} /> {referenceLabel(selectedVisualSource)}
              </span>
            ) : 'Сначала выберите видео или изображение выше.'}
          </div>
          <button
            type="button"
            onClick={registerTake}
            disabled={busy || !takeShotId || !selectedVisualSource}
            className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-sky-400 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
          >
            <Plus size={13} /> Добавить выбранное медиа как дубль
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {production.scenes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/30 px-4 py-6 text-center text-xs text-slate-600">
            Создайте первую сцену — затем внутри неё появятся кадры и варианты дублей.
          </div>
        ) : production.scenes.map(scene => {
          const shots = production.shots.filter(shot => shot.scene_id === scene.scene_id);
          return (
            <div key={scene.scene_id} className="rounded-xl border border-slate-800 bg-slate-950/35 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-200">{scene.title}</p>
                  {scene.summary && <p className="mt-1 text-xs text-slate-500">{scene.summary}</p>}
                </div>
                <span className="font-mono text-[10px] text-slate-700">{scene.scene_id}</span>
              </div>
              <div className="mt-3 space-y-2">
                {shots.length === 0 ? (
                  <p className="text-xs text-slate-600">В сцене пока нет кадров.</p>
                ) : shots.map(shot => {
                  const takes = production.takes.filter(take => take.shot_id === shot.shot_id);
                  return (
                    <div key={shot.shot_id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs text-slate-300">{shot.intent}</p>
                        {shot.accepted_take_id ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-950/50 px-2 py-1 text-[10px] text-emerald-300">
                            <Check size={11} /> Принят
                          </span>
                        ) : null}
                      </div>
                      {takes.length === 0 ? (
                        <p className="mt-2 text-[11px] text-slate-600">Дублей ещё нет.</p>
                      ) : (
                        <div className="mt-2 space-y-2">
                          {takes.map(take => {
                            const accepted = shot.accepted_take_id === take.take_id;
                            return (
                              <div key={take.take_id} className="flex flex-col gap-2 rounded-lg border border-slate-800 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0">
                                  <p className="truncate text-xs text-slate-300">{take.label || take.take_id}</p>
                                  <p className="mt-1 font-mono text-[9px] text-slate-700">{take.take_id}</p>
                                </div>
                                {accepted ? (
                                  <span className="text-[10px] text-emerald-300">
                                    Timeline: {shot.timeline_clip_ids.join(', ') || 'привязка создана'}
                                  </span>
                                ) : shot.accepted_take_id ? (
                                  <span className="text-[10px] text-slate-600">Другой дубль уже принят</span>
                                ) : (
                                  <button
                                    type="button"
                                    aria-label={`Принять дубль ${take.label || take.take_id}`}
                                    onClick={() => acceptTake(shot, take)}
                                    disabled={busy}
                                    className="rounded-lg border border-emerald-800 px-3 py-1.5 text-[10px] text-emerald-300 hover:bg-emerald-950/40 disabled:opacity-40"
                                  >
                                    Принять в Timeline
                                  </button>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {isMicroDrama && microDrama ? (
        <fieldset disabled={busy} className="m-0 min-w-0 border-0 p-0">
          <div className="mt-5 border-t border-slate-800 pt-4">
            <div className="flex items-center gap-2">
              <BookOpen size={15} className="text-amber-300" />
              <div>
                <p className="text-sm font-medium text-slate-200">История и непрерывность</p>
                <p className="mt-0.5 text-xs text-slate-600">Расширение направления micro-drama поверх общих Scene / Shot / Take.</p>
              </div>
            </div>

            <div className="mt-3 grid gap-3 lg:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <p className="text-xs text-slate-400">История</p>
                <input
                  aria-label="Название истории"
                  value={storyTitle}
                  onChange={event => setStoryTitle(event.target.value)}
                  placeholder="Название"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <input
                  aria-label="Завязка истории"
                  value={storyPremise}
                  onChange={event => setStoryPremise(event.target.value)}
                  placeholder="Завязка / premise"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <textarea
                  aria-label="Синопсис истории"
                  value={storySynopsis}
                  onChange={event => setStorySynopsis(event.target.value)}
                  placeholder="Краткий синопсис"
                  rows={3}
                  className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <p className="flex items-center gap-2 text-xs text-slate-400"><UserRound size={13} /> Персонажи</p>
                <input
                  aria-label="Имя персонажа"
                  value={characterName}
                  onChange={event => setCharacterName(event.target.value)}
                  placeholder="Имя"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <input
                  aria-label="Описание персонажа"
                  value={characterDescription}
                  onChange={event => setCharacterDescription(event.target.value)}
                  placeholder="Внешность / роль / состояние"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <button
                  type="button"
                  onClick={addCharacter}
                  disabled={!characterName.trim()}
                  className="mt-2 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-slate-700 py-2 text-xs text-slate-300 disabled:opacity-40"
                >
                  <Plus size={12} /> Добавить персонажа
                </button>
                <div className="mt-2 space-y-1">
                  {characters.map(character => (
                    <div key={character.character_id} className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 px-2 py-1.5">
                      <span className="truncate text-[11px] text-slate-400">{character.name}</span>
                      <button
                        type="button"
                        aria-label={`Удалить персонажа ${character.name}`}
                        onClick={() => removeCharacter(character.character_id)}
                        className="text-slate-700 hover:text-red-400"
                      ><X size={12} /></button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                <p className="flex items-center gap-2 text-xs text-slate-400"><MapPin size={13} /> Локации</p>
                <input
                  aria-label="Название локации"
                  value={locationName}
                  onChange={event => setLocationName(event.target.value)}
                  placeholder="Название"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <input
                  aria-label="Описание локации"
                  value={locationDescription}
                  onChange={event => setLocationDescription(event.target.value)}
                  placeholder="Вид, свет, важный реквизит"
                  className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs outline-none focus:border-amber-600"
                />
                <button
                  type="button"
                  onClick={addLocation}
                  disabled={!locationName.trim()}
                  className="mt-2 inline-flex w-full items-center justify-center gap-1 rounded-lg border border-slate-700 py-2 text-xs text-slate-300 disabled:opacity-40"
                >
                  <Plus size={12} /> Добавить локацию
                </button>
                <div className="mt-2 space-y-1">
                  {locations.map(location => (
                    <div key={location.location_id} className="flex items-center justify-between gap-2 rounded-lg border border-slate-800 px-2 py-1.5">
                      <span className="truncate text-[11px] text-slate-400">{location.name}</span>
                      <button
                        type="button"
                        aria-label={`Удалить локацию ${location.name}`}
                        onClick={() => removeLocation(location.location_id)}
                        className="text-slate-700 hover:text-red-400"
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
                  value={continuityForm.sceneId}
                  onChange={event => selectContinuityScene(event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600"
                >
                  <option value="">Выберите сцену</option>
                  {production.scenes.map(scene => (
                    <option key={scene.scene_id} value={scene.scene_id}>{scene.title}</option>
                  ))}
                </select>
                <select
                  aria-label="Локация сцены"
                  value={continuityForm.locationId}
                  onChange={event => setContinuityForm(current => ({ ...current, locationId: event.target.value }))}
                  disabled={!continuityForm.sceneId}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
                >
                  <option value="">Локация не задана</option>
                  {locations.map(location => (
                    <option key={location.location_id} value={location.location_id}>{location.name}</option>
                  ))}
                </select>
              </div>
              {characters.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {characters.map(character => {
                    const active = continuityForm.characterIds.includes(character.character_id);
                    return (
                      <button
                        type="button"
                        key={character.character_id}
                        aria-label={`Персонаж continuity ${character.name}`}
                        aria-pressed={active}
                        onClick={() => toggleContinuityCharacter(character.character_id)}
                        disabled={!continuityForm.sceneId}
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
                value={continuityForm.canonFactsText}
                onChange={event => setContinuityForm(current => ({ ...current, canonFactsText: event.target.value }))}
                disabled={!continuityForm.sceneId}
                placeholder="Один канонический факт на строку"
                rows={3}
                className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
              />
              <textarea
                aria-label="Заметки по непрерывности сцены"
                value={continuityForm.notes}
                onChange={event => setContinuityForm(current => ({ ...current, notes: event.target.value }))}
                disabled={!continuityForm.sceneId}
                placeholder="Костюм, реквизит, состояние персонажей, свет…"
                rows={2}
                className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 outline-none focus:border-amber-600 disabled:opacity-40"
              />
              <button
                type="button"
                onClick={saveMicroDrama}
                disabled={busy}
                className="mt-2 inline-flex items-center gap-2 rounded-lg bg-amber-300 px-4 py-2 text-xs font-semibold text-slate-950 disabled:opacity-40"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                Сохранить историю и непрерывность
              </button>
            </div>
          </div>
        </fieldset>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-3 font-mono text-[10px] text-slate-700">
        <span>production/semantics.json · v{production.schema_version}</span>
        <span>{production.scenes.length} scenes</span>
        <span>{production.shots.length} shots</span>
        <span>{production.takes.length} takes</span>
        <span>timeline end {seconds(timelineDurationUs)}s</span>
      </div>
    </section>
  );
}
