# UV Studio Test Evidence Policy and Gaps

**Status:** CURRENT SUPPORTING EVIDENCE POLICY  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064

## Purpose

Green lower-layer tests do not by themselves prove that a clean user can understand and complete a product journey. UV Studio keeps four evidence classes and applies them to the current Production-Direction product model.

## Evidence classes

### Class A — Domain/API tests

Prove schemas, canonical-state invariants, commands, authorization, adapters, persistence/recovery, integrity and fail-closed behavior.

### Class B — Informed browser regression

A known workflow may use deterministic fixture/API setup when needed. It proves that a real browser surface still drives real backend/domain behavior. Existing recipe/Product-Orchestrator browser tests belong here while compatibility is retained.

### Class C — Cold-start product journey

Starts from user-equivalent clean state and uses visible UI for product decisions/setup.

Rules:

- empty Project Store unless import is the scenario;
- no direct API seeding of production decisions/state;
- no direct API creation when direction discovery/selection is under test;
- setup-required capabilities are explained visibly;
- fail on unexplained disabled primary actions or dead CTAs;
- verify an actual persisted result when the scenario claims one;
- verify selected Production Direction survives reopen/archive round-trip;
- verify all directions enter the same Studio Core rather than separate engines.

PR #63 added the first Direction-selection Class-C spine; later direction-domain slices must extend it rather than returning to recipe cards.

### Class D — Installed human acceptance

A real installed Windows candidate is reviewed without test-author knowledge. At minimum: first launch, direction selection/open, understandable first action, readable controls, truthful setup state, expected result or clear limitation, native process/window lifecycle and data preservation/update behavior when release work resumes.

## Current targets under D-064

### Shared Studio Core

```text
clean launch
 -> /projects
 -> choose Production Direction
 -> create project
 -> enter shared Studio
 -> import media
 -> edit canonical Timeline
 -> reopen
 -> export
```

### Micro-drama

```text
choose micro_drama
 -> establish story/characters/locations
 -> scenes/shots
 -> candidate takes
 -> accept a take
 -> shared Timeline/export
```

This is the preferred first rich direction vertical after the transaction foundation.

### Commercial

```text
choose commercial
 -> brief/product/brand/audience
 -> concepts/shots/variants
 -> accept material
 -> shared Timeline/export
```

### Music video

```text
choose music_video
 -> song/Music Map
 -> visual direction/shots
 -> rhythm-aware assembly
 -> shared Timeline/export
```

Existing Music Map/Assembly browser tests remain valuable Class-B compatibility/domain evidence until surfaced through the modern direction UI.

### Narrated video

```text
choose narrated_video
 -> brief/script/voice
 -> semantic segments/visual plan/subtitles
 -> shared Timeline/export
```

### Dub battle

```text
choose dub_battle
 -> source scene/characters/dialogue
 -> cast/recording takes
 -> mix
 -> shared Timeline/export
```

Ordinary dubbing/translation remains a contextual tool and must not be confused with this direction.

### Free project / contextual tools

`free_project` proves unconstrained Media/Assets/Timeline work. Targeted edit, ordinary dubbing, slideshow, visualizer and similar operations are tested as contextual Studio tools, not as top-level directions.

## Compatibility evidence

Legacy recipe/Product-Orchestrator/Stage browser tests may remain while supported old projects depend on those paths. They must be labelled/understood as Class-B compatibility evidence and must not define the modern product taxonomy.

## CI policy

Keep layered evidence:

```text
unit/domain/API
+ real-media
+ informed browser regression
+ cold-start Production-Direction journeys
+ packaged installed-app evidence when release work resumes
```

A higher-level failed user outcome can block release even when lower-layer checks are green. Git history preserves the detailed Product Truth Recovery-era gap analysis that preceded D-064.
