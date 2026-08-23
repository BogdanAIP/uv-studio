# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-recovery-repository-hygiene -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** on `main` after repository-hygiene PR #49 merged as `a92a232ed8fdcc50eb88b114452784348c3c994c`.

Product Truth Recovery now has five authoritative Class A/B Product Orchestrator journeys, and the repository truth/contract cleanup required before further orchestration work is complete. Product Orchestrator remains a current-state projection plus allowed semantic-action boundary; Project Store and dedicated domain stores remain canonical.

## Completed Product Recovery journeys

The permanent Product Orchestrator has authoritative Class A/B journeys for:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`;
- `music_video -> music_video`.

## Repository hygiene completed

PR #49 reconciled the repository with that as-built product truth:

- Product Truth Matrix, Product Orchestrator architecture and engineering backlog now describe all five recovered journeys;
- obsolete `/pipelines/standard`, `/pipelines/action-transfer`, `/pipelines/digital-human` and `/sandbox` frontend route pages are retired;
- Dubbing `accept_dubbing_review` now validates through its action-specific request contract, including optional `accepted_id`, without ambiguous union typing breaking the normal UI path;
- dead Music projection scaffolding was removed while current-byte integrity verification remains authoritative;
- strict portable-JSON validation and per-project corruption isolation were assessed and split into the next bounded Project Store hardening slice;
- missing `main` branch protection remains an external repository-setting P0 and is not represented as fixed in code.

The exact Draft head and exact Review head of PR #49 each passed all five permanent Ubuntu/Windows CI jobs, including API/HTTP, real-media, frontend lint/audit/build and browser user-outcome coverage.

## Remaining release boundary

This state does **not** claim Class C cold-start usability, installed Windows human acceptance or Stage 9 release readiness. Stage 9 packaging/release work remains blocked until Product Truth Recovery, Class C cold-start validation and installed Windows human acceptance are complete.

## Next authorized slice

The next authorized slice is `project-store-portable-json-hardening`, defined by `project-context/NEXT_TASK.md`.

It must harden canonical Project Store/model/import/list semantics so nested non-portable values and non-finite numbers cannot persist, while one malformed project cannot hide unrelated healthy projects. Narrated orchestration follows only after that hardening slice is reviewed, merged and closed back to idle.
