# UV Studio Test Evidence Gaps

## Purpose

Existing browser E2E is valuable regression evidence. It is **not** sufficient cold-start product evidence. This distinction became release-critical after Stage 9 automation was green while the installed application failed human usability review.

The recovery does not delete or devalue existing tests. It assigns them the correct evidence class and adds a future cold-start class.

## Existing browser E2E strengths

The Stage 4C/5/6 browser suite now deliberately separates two product truths instead of forcing unrelated domains into one project:

- a dedicated `free_project` targeted-edit journey runs the real built Next.js frontend against the real UV-owned FastAPI server, imports real FFmpeg media fixtures and completes range selection, replacement preparation, evidence-based Review/Accept and final render through the Product Orchestrator semantic actions;
- the targeted project asserts that Dubbing, Sequence Continuity and the historical Stage 8 Free workspace are not mounted alongside the targeted editor;
- a separate non-migrated `general_video` compatibility project keeps the existing Dubbing and Sequence Continuity browser regressions alive until those domains receive their own Product Orchestrator migrations;
- real project/domain state and real media artifacts are validated rather than replacing execution with frontend mocks.

The Story/Commercial composition suite keeps the real round-trip tests for those preparation workspaces and now treats `free_project` as targeted-edit routing rather than as the old catch-all Stage 8 workspace.

The Music Video suite similarly drives Music Map, Direction, Assembly and render controls against the real application.

These tests are useful and should remain permanent regressions.

## Why they do not prove first-time usability

### 1. Targeted-edit E2E still knows the intended interaction sequence

The targeted path is now simpler than the historical `Brief -> Plan -> Candidate -> Review -> Accept` UI. The separate technical Plan step is hidden behind one semantic `prepare_replacement` action. However, the test still knows to perform:

```text
import source + replacement videos
-> select source
-> drag exact timeline range
-> describe the requested change
-> prepare replacement variant
-> mark every ReviewTarget using the shown candidate artifact
-> approve Review
-> accept into timeline
-> render master
```

This proves the orchestrated product path is executable and that the removed Plan step is not required from the user. It still does not prove that a first-time user discovers every action without test-author knowledge.

### 2. Dubbing compatibility test seeds prerequisite state through backend API

The Stage 5 compatibility path directly calls the real UV API to insert a reviewed transcript before continuing through browser controls:

```text
POST /api/uv/projects/{id}/editor/commands
command=import_dubbing_transcript
```

That remains legitimate deterministic Class B setup. It does not answer the cold-start question of what a normal user sees when ASR/runtime is not configured. The dedicated Dubbing Product Orchestrator slice must make that prerequisite visible before a Class C journey can be claimed.

### 3. Some browser tests create projects by direct API

The targeted routing and Music Video regressions may create a project directly with a known `recipe_id` and navigate to `/projects/{id}`. This isolates the workflow under test, but it does not test recipe discoverability/readiness on the project creation screen.

### 4. Existing E2E is still informed by domain vocabulary

Stable regression anchors include concepts such as:

- exact timeline range;
- ReviewTarget;
- Accept;
- Music Map;
- Music Director;
- Assembly Plan;
- bounded TimelineContext.

Those concepts are valuable domain contracts. They should not automatically define the default end-user mental model.

### 5. Workspace isolation is now tested only for migrated journeys

Photo -> Video, Visualizer and targeted `free_project` now fail their browser evidence when unrelated generic specialist workspaces are mounted. Non-migrated recipes still require their own migration and isolation tests.

### 6. Recipe discovery/readiness remains outside these informed regressions

A workflow-specific test that begins from an already selected recipe does not prove that `/projects` presents unavailable, setup-required and ready tasks truthfully before project creation.

## Evidence classes from D-062 onward

### Class A — Domain/API tests

Prove:

- canonical state invariants;
- schemas;
- commands;
- authorization;
- adapter execution;
- persistence/recovery;
- projected action contracts and fail-closed input validation.

Keep extensive coverage.

The targeted-edit slice adds Class A proof that:

- verified project-owned video controls readiness;
- tampered media fails closed;
- readiness follows the current product stage instead of merely the presence of any source: a saved Brief without replacement material is `setup_required`, a missing required local render runtime is not reported as ready, and an exact matching master is reported as the current outcome;
- replacement source must be distinct and one of the currently projected allowed pairs;
- semantic domain actions preserve existing Brief/Plan/Candidate/Review/Accepted stores rather than adding orchestration persistence;
- already consumed approved Reviews are not advertised as repeatable Accept actions;
- stale render artifacts are not exposed as `current_outcome` after Accepted state changes;
- a failed combined Plan + Candidate operation restores the exact previous Plan and removes partial artifact registration when no concurrent canonical mutation superseded the action;
- if another Plan is approved while Candidate preparation is in flight, the action fails closed and rollback preserves that concurrent Plan instead of overwriting it;
- Candidate registration remains bound to the exact Plan installed by the semantic action, so a concurrent Plan change cannot silently rebind copied media to a different decision;
- final render remains capability-backed through `video.render_edits` and its existing local/free execution boundary.

### Class B — Informed browser regression

May use deterministic fixture/API setup when necessary. Proves that a known product/domain path still works through real browser controls.

Existing E2E belongs here.

The migrated reference journeys additionally verify workspace isolation and semantic Orchestrator calls. The targeted-edit journey is isolated from Dubbing/Continuity, while those older domains retain a separate compatibility regression until migrated.

### Class C — Cold-start product journey

Must start from user-equivalent clean state and use user-visible actions for all product decisions/setup.

Rules:

- empty Project Store unless importing is the scenario;
- default machine config except explicitly documented installed baseline;
- no direct HTTP seeding of transcript, plan, review, Music Map, accepted edit or other workflow decision state;
- no direct API project creation when project discoverability/readiness is under test;
- setup-required capabilities must be represented through visible setup/prerequisite UX;
- fail on unexplained disabled primary actions;
- fail on ready recipe cards that cannot reach a result;
- fail when irrelevant specialist workspaces dominate a selected recipe;
- fail on product CTAs that loop or have no meaningful destination;
- verify an actual result/artifact where the scenario claims one.

### Class D — Installed human acceptance

A real installed Windows candidate must be reviewed without test-author knowledge as a substitute for human discovery.

At minimum:

- first launch;
- create/open project;
- understand the first meaningful action;
- readable controls;
- no misleading dead CTAs;
- selected mode exposes relevant workflow;
- expected result can be produced or a clear setup requirement is shown;
- native window/process lifecycle;
- update/reinstall/uninstall/data preservation when release candidate testing resumes.

## Permanent-scenario cold-start targets

### A. General video

```text
choose General Video
-> see truthful readiness
-> enter brief
-> follow proposed plan/actions
-> produce/assemble assets
-> preview
-> export
```

No hidden narration requirement.

### B. Narrated video

```text
choose Narrated Video
-> see TTS/generation prerequisites before execution
-> topic/script
-> narration
-> visual plan/assets
-> preview
-> export
```

Until that path exists, mode must be explicitly unavailable/partial rather than pretending the historical VideoClaw pipeline is mounted.

### C. Music Video

```text
choose Music Video in UI
-> add song
-> request/propose analysis
-> review/edit structure
-> add/obtain visuals
-> assemble
-> rhythm review
-> export
```

Advanced manual Music Map editing may remain available, but should not be the only discoverable path.

### D. Dubbing

```text
choose Dubbing
-> import video
-> product explains local ASR setup or provides available path
-> transcribe
-> review text
-> translate optional
-> provide/generate speech
-> review
-> render/export
```

No backend transcript seeding in Class C.

### E. Targeted edit

```text
choose targeted edit
-> import source video
-> product guides range selection
-> describe change
-> import or obtain replacement material
-> prepare and preview a variant
-> review / accept / reject
-> export current Accepted state
```

The durable Brief/Plan/Candidate/Review implementation remains underneath. Class C must not require the user to understand the hidden Plan object or internal IDs.

## CI policy direction

Do not make cold-start tests replace domain/informed E2E. Run both:

```text
unit/domain/API
+ real-media
+ informed browser regression
+ cold-start product journey
+ packaged installed-app evidence when release work resumes
```

A release gate requires all relevant classes. Green lower-layer evidence cannot override a failed higher-layer user outcome.
