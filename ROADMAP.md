# UV Studio Roadmap

The roadmap targets the full product. Historical Stage numbering records how the repository got here, but **D-064 is the current product-composition authority**: one shared Studio Core with first-class Production Directions. Recipe/Stage/Product-Orchestrator details below are historical where D-063/D-064 supersede them.

## Program completion gate

The initial UV Studio program is complete when Stage 9 produces a distributable Windows release **after the Product Truth Recovery Gate passes**, and the release candidate proves the permanent regression scenarios through user-facing workflows rather than manual API calls or test-only state seeding.

The completion gate requires:

- clean-machine installation without a separately prepared Python, Node/npm or FFmpeg toolchain;
- canonical projects that survive restart, export/import, upgrade, backup and recovery;
- truthful user-facing Production Direction/tool readiness backed by actually mounted executable product paths;
- one shared Studio Core and one application/command authority rather than direction-specific engines;
- local/free baseline implementations wherever a viable local path exists, with remote/paid providers remaining explicit optional choices;
- real media fixtures and evidence-based output checks on Windows and Linux;
- cold-start user-outcome evidence without hidden API/test fixture setup;
- cancellation, diagnostics, migration and rollback behavior suitable for user data;
- license/security/dependency audit and signed release artifacts;
- no mandatory dependency on VideoClaw, Qwen, MCP, a particular model vendor or a paid API in canonical project state.

After this gate passes, additional Production Directions, tools, providers and refinements belong to a versioned post-release backlog. They do not postpone the initial product indefinitely.

## Stage completion rule

A stage is not complete merely because its backend contract exists.

Every product stage must satisfy both gates that apply to it:

1. **Engineering gate** — provider-neutral contracts, portable state, security/permission boundaries, rollback behavior and representative automated tests are real.
2. **User-outcome gate** — the intended workflow can be completed through the product UI without manual API calls, hidden provider/runtime assumptions or test-only pre-seeded state.

Infrastructure-only stages may have no end-user UI, but they must prove the runtime boundary they claim. Security, dependency ownership and real-media verification are progressive obligations and must not be deferred wholesale to Stage 9.

A failed clean installed-app human journey is product evidence and may block release even when automated engineering/release checks are green.

## Permanent architecture rules

- no single mandatory film/music/micro-drama pipeline;
- one shared Studio Core may host multiple first-class Production Directions with different domain state/navigation;
- a Production Direction is not a RecipeDefinition/provider/execution engine;
- operation-level transforms remain contextual Studio tools unless an evidence-backed decision proves a distinct production model;
- paid AI APIs are optional capabilities, never hidden baseline dependencies;
- prefer deterministic/local tools for deterministic work;
- local/free implementations may coexist with paid providers behind the same semantic capability;
- provider/model choice and expected paid cost must remain explicit when creatively or financially significant;
- capability discovery/ordering is metadata, not permission to execute or spend;
- all product execution paths that can contact a remote or non-free provider must pass the product-owned authorization boundary; legacy compatibility routes may not bypass it;
- user-visible readiness must be backed by an actually reachable UV-owned execution path; an unmounted or historical route is never `available` product functionality;
- users express intent and product decisions; internal plan/candidate/review/runtime state is progressively disclosed only when actionable;
- GUI, AI, MCP and scripts converge on one product-owned semantic action/command model;
- secrets and machine-only runtime configuration stay outside portable project state and outside commit-prone vendor configuration;
- professional workflow policy (source review, planning, sample-first generation, scene/take gates, evidence-based review) is separate from the provider that performs an AI operation;
- OpenClaw, Qwen-MM-Plugins and other MCP/runtime packages are optional adapters, not the canonical project state or mandatory execution layer;
- reuse mature editor/media components before growing a UV-owned generic NLE surface;
- Windows remains a first-class target even when an optional third-party package currently requires WSL2.

## Stage 0 — Clean baseline

Goal: establish a reproducible modern VideoClaw-derived baseline and repository discipline.

- pin upstream `HITsz-TMG/VideoClaw` commit;
- import only modern `video-claw/video-claw` application paths required by runtime;
- preserve MIT notices;
- identify/remove unreachable historical code only after dependency checks;
- make backend/frontend start reproducibly;
- add baseline CI and smoke tests;
- document Windows setup;
- verify existing narrated, action-transfer, digital-human and film workflows where credentials are available.

Exit: clean buildable baseline with tracked upstream provenance.

## Stage 1 — Universal Project Store

Goal: project state survives chats, restarts and task failures independently of UI sessions.

- project schema/versioning;
- atomic local persistence;
- source/artifact/task references;
- validated `.uvproj.zip` project archives with checksums and traversal protection;
- import/export;
- backups/migrations/recovery helpers;
- Projects API/UI.

Engineering exit: canonical project storage and archives are traversal-safe, atomic and migration-aware.

User exit: close/reopen application, export/import a complete project, and resume without data loss.

## Stage 2 — Historical Recipe Registry + Production Policy foundation

**Historical note:** recipe-first product identity is superseded by D-063/D-064. Existing recipe code remains compatibility/reference material; new v2 product growth uses Production Directions plus contextual tools over one Studio Core.

Original useful outcomes retained from this stage:

- provider-neutral production policy hooks;
- source-review gates for workflows based on real footage;
- optional creative direction/taste contracts;
- sample-first generation policy;
- scene/take ledger concepts where multi-scene work needs them;
- plan/review gate contracts;
- evidence-based final review with timestamps/frame references;
- reusable task/domain knowledge that can migrate into Production Direction metadata/domain services or Studio tools.

Do not add a new `RecipeDefinition` to ship a v2 feature.

## Stage 3 — Capability Registry & Adapters

Goal: stable semantic interface to replaceable local, MCP and provider capabilities without a mandatory intermediate runtime.

- semantic contracts for image/video/speech/media-understanding operations;
- capability registry with availability, locality, cost class and safe implementation metadata;
- separate registry metadata from `SelectionPolicy` and execution permission;
- fail-closed `local_free_first`: only `available + free + local`, never implicit remote/paid fallback;
- project-scoped local execution with no arbitrary shell/FFmpeg command surface;
- direct MCP client/adapter with explicit semantic tool bindings;
- local-tool adapter;
- native VideoClaw adapter during migration;
- optional OpenClaw adapter/runtime;
- optional Qwen-MM-Plugins profile/binding pack after generic MCP support is proven;
- exact provider/model selection for paid media;
- explicit consent/cost boundary before potentially-paid or paid execution;
- cost/error/job metadata;
- `local_free_first`, `pinned_offer`, `manual`, and later explicit best-available/budget-aware policies where their permission semantics are defined;
- never require DashScope for a baseline UV Studio feature when an adequate local/free path exists;
- keep Qwen cloud generation/Omni/video-memory capabilities optional for users who explicitly configure their API access.

Engineering exit: UV Studio-owned semantic capability execution is real for local, direct-MCP and exact compatibility offers, with no silent paid/remote widening.

Stage 3 is not considered application-wide complete until Stage 3.5 removes legacy routes that can bypass those guarantees.

## Stage 3.5 — Runtime Independence & Security

Goal: make the running application obey the same provider-neutral, secret-safe and permission-safe boundaries already established in the UV Studio capability layer.

### Runtime boundary

- UV Studio owns the application/runtime boundary instead of treating the complete VideoClaw FastAPI app as the permanent product root;
- legacy VideoClaw routes are explicitly isolated, migrated, wrapped or disabled by default;
- no legacy sandbox/pipeline/provider route may contact a remote or non-free provider outside D-017-equivalent product authorization;
- local development CORS is restricted to deliberate application origins rather than wildcard browser access;
- static/file routes expose only intended application data.

### Secrets and configuration

- secrets never live in canonical project state;
- provider credentials are stored outside the vendored source tree and cannot appear as ordinary Git working-tree files;
- configuration read APIs never return raw stored secrets;
- updates use explicit secret write semantics instead of round-tripping credentials through the browser;
- logs, provenance and error payloads remain secret-safe.

### Dependency ownership

- UV Studio declares its own core Python runtime dependencies instead of receiving them incidentally from `vendor/videoclaw-app/backend/requirements.txt`;
- provider/runtime extras remain optional and independently installable;
- baseline development does not install OpenAI, DashScope, Playwright, Edge TTS or another provider stack merely because VideoClaw contains it;
- frontend dependency versions, lint configuration and known advisories are audited and brought under explicit CI policy.

### Development-state lifecycle

- repository development state can represent a merged/idle handoff instead of leaving an already-merged PR as the live slice;
- live PR changed paths are eventually checked against declared write scope;
- slice-specific quality gates can extend the baseline check catalog safely.

Engineering exit:

- a browser page cannot read raw provider keys from the local backend;
- a legacy endpoint cannot perform unauthorized remote/non-free execution;
- saving credentials does not create a commit-prone plaintext vendor config file;
- the UV Studio core can be installed/tested from UV Studio-owned dependency declarations;
- frontend lint/dependency audit is a real CI gate or has explicitly accepted, narrowly scoped residual exceptions.

Only after this gate may later product stages rely on the runtime boundary as a product-wide invariant.

## Stage 4 — Existing Video / Range Edit

Goal: professionally edit only the requested range of an existing video without turning a short edit into mandatory regeneration or whole-video analysis.

### Stage 4A — Mechanical editing foundation

- import/probe and actual source technical inspection;
- canonical integer-microsecond `ProjectMediaRange`;
- bounded context before/after;
- deterministic FFmpeg extraction;
- deterministic prepared-replacement reinsertion;
- no caller-controlled raw FFmpeg/filtergraph/output-path surface;
- real FFmpeg/FFprobe golden fixtures on Windows and Linux covering representative CFR/VFR, audio/no-audio and timestamp cases;
- non-destructive edit-decision/timeline direction for repeated edits so full lossless re-encoding is not the permanent state model.

Engineering exit: exact range extraction/reinsertion works against real encoded fixtures with verified boundaries, geometry, audio policy and rollback behavior.

### Stage 4B — Edit intelligence

- provider-neutral bounded range/context evidence model;
- typed `RangeContinuityBrief` or equivalent versioned contract;
- separate mechanical facts, evidence, observations, constraints and review targets;
- edit-direction/pacing/audio-first/beat-sync policies where relevant;
- optional Scene Ledger for multi-scene edits;
- plan gate before designed assembly;
- sample-first rule for generated replacement assets;
- generative transform capability only when needed;
- independent evidence-based review for produced replacements;
- no silent downgrade from an approved method/provider to a weaker result.

Engineering exit: the exact requested range and mechanical constraints survive storage/archive round-trip and can be consumed by replaceable generation/review adapters without provider IDs entering canonical state.

### Stage 4C — User workflow

- video preview and integer-microsecond timeline/range selector;
- visible bounded context and replacement brief/review state;
- choose deterministic edit or optional prepared/generated replacement path;
- preview before acceptance;
- explicit accept/reject and failure/cost states;
- project-owned non-destructive edit state;
- explicit final export/render;
- frontend unit/accessibility coverage and browser E2E for the complete targeted-range workflow.

User exit: user opens an existing video, selects a 5–10 second range, requests a change, reviews the result in context, accepts/rejects it and exports the edited video without regenerating the whole source workflow or issuing manual API calls.

Under D-064 this is a contextual Studio tool, not a top-level Production Direction.

## Stage 5 — Dubbing / Translation

Goal: revoice an existing video without running filmmaking workflow.

- speech extraction;
- local/free ASR path (for example Whisper-compatible/WhisperX) as baseline;
- optional cloud ASR/Omni adapters;
- optional translation;
- speech synthesis/recorded voice;
- alignment/subtitles;
- optional lip-sync;
- mix/export;
- audio-preservation/loudness checks;
- representative real-media/audio fixtures and browser E2E before stage completion.

Engineering exit: ASR/translation/TTS/alignment remain replaceable capabilities with local/free baseline where viable and explicit authorization for remote/non-free alternatives.

User exit: existing video can be dubbed independently without requiring Qwen/DashScope or another paid media API.

Under D-064 ordinary dubbing/translation remains a contextual Studio tool. It is distinct from the `dub_battle` Production Direction, which is organized around scene/characters/dialogue/cast/takes/mix.

## Stage 6 — Optional Sequence Continuity & Review

Goal: robust linked-shot generation only where continuity matters.

- planned/observed state;
- locks/allowed changes;
- accepted/rejected takes;
- re-anchor policy;
- optional VLM take review;
- human confirmation fallback;
- provider-neutral structured review schema;
- reuse professional scene/take gate concepts without forcing them on standalone clips.

Engineering exit: continuity state is optional, typed and provider-neutral.

User exit: connected generated clips continue from accepted observed state; simple projects do not pay this complexity.

Under D-064 this logic is especially relevant to `micro_drama`, but remains optional and reusable rather than globally mandatory.

## Stage 7 — Music Video production domain

Goal: professional music-driven video production inside the `music_video` Production Direction.

- integrate `musical-mv-storyboard` through adapter boundary where useful;
- song/lyrics/structure analysis;
- Music Map UI;
- Music Director / visual direction;
- music-aware shot timing;
- beat-sync and audio-first editing craft;
- sample-first generated assets;
- rhythm audit/final assembly;
- evidence-based review of timing/scene transitions.

Engineering exit: music-specific domain state/policy composes the shared Project/Studio/Capability primitives rather than becoming a separate editor engine.

User exit: a music project can move from song/Music Map through visual direction/shots into the shared Timeline without making music mandatory for other directions.

## Stage 8 — Production Directions and contextual tools

Historical Stage 8 originally grouped heterogeneous recipes. D-064 replaces that taxonomy with two levels.

### First-class Production Directions

- `micro_drama` — Микродрама / сюжетное видео;
- `commercial` — Реклама / продукт;
- `music_video` — Музыкальный клип;
- `narrated_video` — Видео с диктором;
- `dub_battle` — Киноозвучка / Кинобатл;
- `free_project` — Свободный проект.

### Contextual tools / quick actions

- photo-to-video/slideshow;
- visualizer;
- performance/lip-sync;
- talking character/digital human;
- action transfer;
- ordinary dubbing/translation;
- targeted edit and future transforms/generation tools.

Exit: direction selection changes production composition/domain context while all directions share one Studio Core and all tools use common application/capability boundaries.

## Product Truth Recovery — mandatory gate before Stage 9 merge

The first installed-app human review and subsequent repository/history audit showed that the engineering foundation and packaged runtime can be healthy while product-level workflow truth is not.

D-062 remains the truth/release gate. D-063/D-064 supersede the old plan to expand Product Orchestrator recipe-by-recipe as the long-term product center.

Current ordered recovery/product phases are:

1. **Product Truth Inventory** — completed in PR #42; keep the inventory current.
2. **Shared Studio editor spine** — completed in PR #61: Project -> Media -> canonical Timeline -> MLT -> deterministic export.
3. **Production Directions** — restore meaningful task/domain composition over the shared Studio Core without reviving recipe engines.
4. **Project Unit of Work / Undo-Redo** — atomic production-document + asset + timeline mutations.
5. **Direction-domain verticals** — prove real micro-drama/commercial/music/narrated/dub-battle domain journeys incrementally.
6. **Model Registry + Job Manager + named AI execution** — one visible model/job/result lifecycle shared across directions.
7. **Contextual-tool migration** — move useful targeted edit/dubbing/music/continuity behavior out of legacy workspace/orchestrator surfaces.
8. **Cold-start product verification** — clean-state UI-only regression plus human installed-app acceptance.
9. **Resume Stage 9** — reconcile preserved packaging/native-shell work with the accepted product, then finish signing/publication.

Recovery exit:

- every visible Production Direction and contextual tool has truthful readiness backed by current executable product paths;
- no modern path depends on Product Orchestrator/legacy execution-plan as its primary authority;
- D-033 editor conformance remains established;
- direction identity/domain state and common Studio state survive project round-trip;
- permanent regression scenarios complete through UI without manual API calls or test-only state seeding;
- cold-start automated evidence and human Windows installed-app review pass.

Until this gate passes, Stage 9 may remain an engineering/package reference but **must not merge as the maintained product baseline**.

## Stage 9 — Desktop Productization & Release Hardening

Goal: turn the secure, product-truth-verified runtime into a distributable Windows application.

Stage 9 packaging/native-shell work may be developed and preserved before the recovery gate is complete, but final merge/release readiness is blocked on Product Truth Recovery.

- bundled/provisioned frontend/backend/FFmpeg runtime;
- launcher and process supervision;
- installer/uninstaller;
- updater and versioned migration strategy;
- backup/recovery UX;
- cancellation and diagnostics UX;
- capability self-check and clear optional dependency diagnostics;
- clean-machine installation tests;
- weak-hardware and long-project verification;
- final license/security/dependency release audit building on earlier stage audits rather than introducing them for the first time;
- signed release artifacts;
- documentation/sample projects/release build.

Exit: user installs and runs UV Studio without manually preparing Python/Node/FFmpeg; the Product Truth Recovery Gate is green; all permanent regression scenarios pass through the packaged application from clean user-visible state; human installed-app review passes; optional WSL/cloud integrations do not prevent normal native-Windows use.

## Permanent regression scenarios

The existing engineering/user-outcome scenarios remain valuable and are reclassified under D-064:

A. **Free/general production** — 30–60 s video without required song/narration.  
B. **Narrated direction** — 60 s narrated video with visuals/subtitles.  
C. **Music-video direction** — 20–30 s music-driven excerpt.  
D. **Dubbing tool** — existing-video dubbing/translation.  
E. **Targeted-edit tool** — 5–10 s existing-video edit.  

Class-C discovery must additionally protect all six initial Production Direction cards and ensure operation-level tools are not accidentally promoted back into top-level project identity. Rich micro-drama, commercial and dub-battle journeys become permanent regression scenarios as their domain verticals are implemented.

Major architecture must remain compatible with these scenarios and must not make a paid third-party API mandatory for scenarios that have a viable local/free implementation.
