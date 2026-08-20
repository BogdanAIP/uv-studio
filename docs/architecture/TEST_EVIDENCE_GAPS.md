# UV Studio Test Evidence Gaps

## Purpose

Existing browser E2E is valuable regression evidence. It is **not** sufficient cold-start product evidence. This distinction became release-critical after Stage 9 automation was green while the installed application failed human usability review.

The recovery does not delete or devalue existing tests. It assigns them the correct evidence class and adds a future cold-start class.

## Existing browser E2E strengths

The Stage 4C/5/6 suite:

- runs a real built Next.js frontend;
- runs the real UV-owned FastAPI server;
- uses real FFmpeg/FFprobe fixtures;
- uses Playwright against real browser controls;
- executes targeted edit Review/Accept/render through production UI;
- exercises dubbing state/review/render through production UI after prerequisite fixture setup;
- exercises optional sequence continuity commands/review through production UI;
- validates real project/domain state and artifacts.

The Music Video suite similarly drives Music Map, Direction, Assembly and render controls against the real application.

These tests are useful and should remain permanent regressions.

## Why they do not prove first-time usability

### 1. Tests know the exact hidden workflow sequence

Targeted-edit E2E explicitly knows to perform:

```text
select source
-> drag exact timeline range
-> fill change request
-> Prepare change
-> approve prepared-asset plan
-> prepare full candidate
-> mark every ReviewTarget pass
-> approve Review
-> accept into timeline
-> render master
```

This proves that the state machine is executable. It does not prove that a user can discover that state machine.

### 2. Dubbing test seeds prerequisite state through backend API

The Stage 5 path directly calls the real UV API to insert a reviewed transcript before continuing through browser controls:

```text
POST /api/uv/projects/{id}/editor/commands
command=import_dubbing_transcript
```

The test source itself explains that optional ASR/provider execution is not a browser-test precondition and provider-independent fixture setup uses UV-owned semantic APIs.

That is legitimate deterministic regression setup, but it bypasses the exact cold-start question:

> What does a normal user see and do when ASR/runtime is not configured yet?

### 3. Music Video test creates the project by direct API

The Stage 7 E2E begins with:

```text
POST /api/uv/projects
recipe_id=music_video
```

and navigates directly to `/projects/{id}`. It therefore does not test recipe discoverability/readiness on the project creation screen.

The test then manually authors exact excerpt times, section boundaries, cut markers and shot/source mappings. This proves the Music domain/editor path, not an intent-first product journey.

### 4. Existing E2E is informed by implementation vocabulary

Tests use exact labels and concepts such as:

- Brief;
- full candidate;
- ReviewTarget;
- Accept;
- Music Map;
- Music Director;
- Assembly Plan;
- bounded TimelineContext.

Those concepts are excellent stable regression anchors for domain behavior. They should not automatically define the default end-user mental model.

### 5. Existing tests do not fail on unrelated globally visible workspaces

A Photo -> Video mode can still render its expected artifact even if unrelated targeted-edit/dubbing/continuity panels are present on the page. Outcome assertion succeeds while the page remains confusing.

### 6. Existing tests do not treat misleading navigation as a product failure

A test focused on targeted edit or Stage 8 media does not need to click every top-level CTA. Therefore navigation loops such as `Производственный интерфейс -> / -> /projects` can survive a green suite.

## Evidence classes from D-062 onward

### Class A — Domain/API tests

Prove:

- canonical state invariants;
- schemas;
- commands;
- authorization;
- adapter execution;
- persistence/recovery.

Keep extensive coverage.

### Class B — Informed browser regression

May use deterministic fixture/API setup when necessary. Proves that a known product/domain path still works through real browser controls.

Existing E2E belongs here.

### Class C — Cold-start product journey

Must start from user-equivalent clean state and use user-visible actions for all product decisions/setup.

Rules:

- empty Project Store unless importing is the scenario;
- default machine config except explicitly documented installed baseline;
- no direct HTTP seeding of transcript, plan, review, Music Map, accepted edit or other workflow state;
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
-> import source
-> product guides range selection
-> describe change
-> prepare/obtain replacement
-> preview
-> accept/reject
-> export
```

The durable Brief/Plan/Candidate/Review implementation can remain underneath.

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
