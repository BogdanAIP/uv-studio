# UV Studio

Universal Video Studio — open-source desktop/local-first AI video production and editing workspace.

The project is built by reusing proven open-source video-production components instead of rebuilding the whole stack. The initial technical base is the modern `video-claw/video-claw` application from `HITsz-TMG/VideoClaw`, pinned and tracked as upstream.

## Product scope

UV Studio uses one shared Studio Core with multiple **Production Directions**. A direction changes how a production is organized; it does not create a separate editor engine or choose a hidden AI provider.

Initial directions:

- **Микродрама / сюжетное видео** — story, characters, locations, scenes, shots, takes and continuity where needed;
- **Реклама / продукт** — brief, product, brand, audience, concepts, shots and creative variants;
- **Музыкальный клип** — song, Music Map, sections, visual direction, shots and rhythm-aware assembly;
- **Видео с диктором** — script, voice, semantic segments, visual plan and subtitles;
- **Киноозвучка / Кинобатл** — source scene, characters, dialogue lines, cast, takes and final mix;
- **Свободный проект** — unconstrained Studio work without mandatory production-domain structure.

All directions share the same Project Store, Media/Assets, Preview, canonical multitrack Timeline, Inspector/AI tools, Model Registry/Job Manager direction, application commands and export infrastructure.

Operation-level features remain contextual Studio tools rather than project identities, including:

- targeted range editing;
- ordinary dubbing/translation;
- photo-to-video/slideshow;
- visualizer;
- action transfer;
- talking character/digital human;
- performance/lip-sync;
- image/video/audio generation and transforms.

Music, narration, characters, continuity and specialized review state are optional domain capabilities, not mandatory fields for every project.

See D-064 for the current product-composition architecture.

## Development source of truth

Repository and GitHub state are the durable project memory. Coding agents and new development chats must start with `AGENTS.md`; it defines the required reading order, active-slice contract and multi-agent ownership rules. Do not rely on an old chat transcript to know the current implementation state.

## Development rule

Every meaningful development slice must end with:

- code/tests committed to one integration branch;
- a PR describing what changed and what was verified;
- `project-context/ACTIVE_SLICE.json` synchronized with the PR and its single handoff;
- `PROJECT_STATE.md` updated to the actual repository state;
- `NEXT_TASK.md` containing one concrete next development target;
- architectural decisions recorded in `DECISIONS.md` when they change long-term behavior.

See `DEVELOPMENT_PROTOCOL.md` for the full cross-chat workflow.
