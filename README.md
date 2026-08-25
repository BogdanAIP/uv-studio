# UV Studio

Universal Video Studio — open-source desktop/local-first AI video production and editing workspace.

The project reuses proven open-source video-production components instead of rebuilding the whole media stack. The initial technical donor is the modern `HITsz-TMG/VideoClaw` application, pinned and tracked as upstream; donor application concepts are not UV Studio product authority.

## Product scope

UV Studio uses multiple **Production Directions** over one shared production/application core. A direction changes how a production is organized; it does not create a separate editor engine or choose a hidden AI provider.

Initial directions:

- **Микродрама / сюжетное видео** — story, characters, locations and scene organization;
- **Реклама / продукт** — brief, product, brand, audience and concepts;
- **Музыкальный клип** — song, Music Map, sections and visual direction;
- **Видео с диктором** — script, voice, semantic segments, visual plan and subtitles;
- **Киноозвучка / Кинобатл** — source scene, dialogue, cast and mix policy;
- **Свободный проект** — unconstrained Studio work without mandatory production-domain structure.

Where directions share real production concepts, they reuse one **Production Semantic Core** rather than fork them. In particular, Scene/Shot/Take/accepted-material identities, semantic bindings and continuity links are shared contracts when applicable. A direction may add specialized documents, and a project does not have to instantiate semantic entities it does not need.

All directions share Project Store, Media/Assets, Preview, canonical multitrack Timeline, Inspector/AI tools, application commands, transaction/undo foundation, Model Registry/Job Manager direction and export infrastructure.

Operation-level features remain contextual Studio tools rather than project identities, including targeted range editing, ordinary dubbing/translation, slideshow/visualizer, action transfer, talking character, lip-sync and image/video/audio generation/transforms.

A **Shot is not a Timeline Clip**: the Shot carries production intent/context and accepted Take; the Timeline carries final temporal assembly.

See `docs/architecture/CURRENT_ARCHITECTURE.md`, D-064 (Production Directions) and D-065 (shared production semantics).

## Development source of truth

Repository and GitHub state are durable project memory. Coding agents and new development chats start with `AGENTS.md`; it defines reading order, active-slice contract and ownership rules. Do not rely on an old chat transcript for current implementation state.

Every meaningful development slice ends with one integration branch/PR, synchronized `ACTIVE_SLICE.json`, truthful `PROJECT_STATE.md`, one concrete `NEXT_TASK.md`, required tests/evidence and ADR updates when long-term behavior changes. See `DEVELOPMENT_PROTOCOL.md`.
