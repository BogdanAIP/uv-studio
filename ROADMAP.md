# UV Studio Roadmap

The roadmap targets the full product. Early stages create useful working slices, but the architecture must remain compatible with later stages.

## Program completion gate

The initial UV Studio program is complete when Stage 9 produces a distributable Windows release **after the Product Truth Recovery Gate passes**, and the release candidate proves all five permanent regression scenarios through user-facing workflows rather than manual API calls or test-only state seeding.

The completion gate requires:

- clean-machine installation without a separately prepared Python, Node/npm or FFmpeg toolchain;
- canonical projects that survive restart, export/import, upgrade, backup and recovery;
- complete UI paths for general video, narrated video, music-video excerpt, dubbing and targeted existing-video range edit;
- truthful recipe/workflow readiness backed by actually mounted executable product paths;
- a product-level orchestration contract that exposes prerequisites and next actions instead of requiring the frontend to reconstruct independent backend state machines;
- local/free baseline implementations wherever a viable local path exists, with remote/paid providers remaining explicit optional choices;
- real media fixtures and evidence-based output checks on Windows and Linux;
- cold-start user-outcome evidence without hidden API/test fixture setup;
- cancellation, diagnostics, migration and rollback behavior suitable for user data;
- license/security/dependency audit and signed release artifacts;
- no mandatory dependency on VideoClaw, Qwen, MCP, a particular model vendor or a paid API in canonical project state.

After this gate passes, additional recipes, providers and refinements belong to a versioned post-release backlog. They do not postpone the initial product indefinitely.

## Stage completion rule

A stage is not complete merely because its backend contract exists.

Every product stage must satisfy both gates that apply to it:

1. **Engineering gate** — provider-neutral contracts, portable state, security/permission boundaries, rollback behavior and representative automated tests are real.
2. **User-outcome gate** — the intended workflow can be completed through the product UI without manual API calls, hidden provider/runtime assumptions or test-only pre-seeded state.

Infrastructure-only stages may have no end-user UI, but they must prove the runtime boundary they claim. Security, dependency ownership and real-media verification are progressive obligations and must not be deferred wholesale to Stage 9.

A failed clean installed-app human journey is product evidence and may block release even when automated engineering/release checks are green.

## Permanent architecture rules

- no single mandatory film/music/micro-drama pipeline;
- paid AI APIs are optional capabilities, never hidden baseline dependencies;
- prefer deterministic/local tools for deterministic work;
- local/free implementations may coexist with paid providers behind the same semantic capability;
- provider choice and expected paid cost must remain explicit for chargeable generation;
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

## Stage 2 — Recipe Registry + Production Policy

Goal: one studio supports different tasks without one mandatory pipeline, while professional production discipline is reusable across recipes.

- recipe schema/registry;
- required/optional capabilities;
- UI schema/progressive disclosure;
- wrap existing VideoClaw pipelines;
- add `general_video` and rename narrated semantics clearly;
- provider-neutral production policy hooks;
- source-review gate for workflows based on real footage;
- optional creative direction/taste contract;
- sample-first generation policy;
- scene/take ledger where multi-scene work needs it;
- plan/review gate contracts;
- evidence-based final review with timestamps/frame references;
- use/adapt suitable Apache-2.0 Qwen-MM-Plugins `video-edit` workflow ideas without inheriting its DashScope dependency.

Engineering exit: recipes compose provider-neutral capabilities and policies without embedding concrete runtime/provider IDs.

User exit: user selects a task and only the relevant workflow/UI is presented.

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

## Stage 7 — Music Video Mode

Goal: professional music-driven video workflow.

- integrate `musical-mv-storyboard` through adapter boundary;
- song/lyrics/structure analysis;
- Music Map UI;
- Music Director;
- music-aware shot timing;
- beat-sync and audio-first editing craft;
- sample-first generated assets;
- rhythm audit/final assembly;
- evidence-based review of timing/scene transitions.

Engineering exit: music-specific policy composes existing project/capability/media primitives rather than becoming a new universal engine.

User exit: 20–30 second music excerpt completes a music-aware production workflow without making music mandatory for other video types.

## Stage 8 — Additional recipes

Goal: broaden product by composing existing primitives, not new engines.

- story video;
- commercial/product;
- photo-to-video;
- visualizer;
- performance/lip-sync;
- free project.

Exit: each mode is mostly recipe + capability mapping + production policy + minimal UI and passes its relevant user-facing regression path.

## Product Truth Recovery — mandatory gate before Stage 9 merge

The first installed-app human review and subsequent repository/history audit showed that the engineering foundation and packaged runtime can be healthy while product-level workflow truth is not.

This recovery is defined in `docs/architecture/PRODUCT_RECOVERY_PLAN.md` and accepted by D-062. It restores product coherence without redefining UV Studio's already-set identity as a hybrid local-first production **and editing** workspace.

Ordered phases:

1. **Product Truth Inventory** — map every visible action to frontend handler, mounted API, domain command, capability/adapter and actual result. **Completed in PR #42; keep the inventory current.**
2. **Recipe/execution contract repair** — remove false `available` states and stale launch paths. **Base repair completed in PR #42.**
3. **Product Orchestrator** — project readiness, prerequisites, relevant workspaces and semantic next actions so React is not the primary orchestrator. **Foundation implemented for Photo -> Video in PR #43; expand recipe-by-recipe.**
4. **D-033 editor conformance** — audit the live implementation against the already accepted UV + MLT + selective OpenCut ownership map; repair command/authority bypasses and record incomplete work before generic NLE growth. This is **not** a new choice between UV Studio, OpenCut and MLT and not a product-identity decision.
5. **Core intent-to-result journeys** — recover targeted edit, dubbing, music video, narrated video and general video in that order, keeping setup/remote cost explicit and internal domain state progressively disclosed.
6. **Additional recipe rationalization** — retain Photo as the first orchestrated deterministic reference, migrate Visualizer as the second, turn composition-only modes into real workflows, and gate optional ML modes truthfully.
7. **Cold-start product verification** — clean-state UI-only regression without hidden state seeding, plus human installed-app acceptance.
8. **Resume Stage 9** — reconcile preserved packaging/native-shell work with the recovered product, then finish signing/publication.

Recovery exit:

- every visible recipe/action has a truthful readiness state backed by a current executable path;
- no execution-plan target points to an unmounted endpoint;
- the frontend consumes Product Orchestrator next actions/prerequisites/relevant workspaces for migrated journeys rather than reconstructing hidden workflow state;
- D-033 conformance is established, with generic editor growth blocked behind the accepted reuse/command boundaries rather than a new foundation debate;
- all five permanent scenarios complete through UI without manual API calls or test-only state seeding;
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

A. 30–60 s general video without required song/narration.  
B. 60 s narrated video with visuals/subtitles.  
C. 20–30 s music-video excerpt.  
D. Existing-video dubbing.  
E. 5–10 s targeted existing-video edit.

Major architecture must remain compatible with all five scenarios and must not make a paid third-party API mandatory for scenarios that have a viable local/free implementation.