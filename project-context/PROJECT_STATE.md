# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: project-store-portable-json-hardening -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is **idle** on `main` after Project Store hardening PR #50 merged as `99979737cfddc542481158c147306bda0c7fea24`.

The hardening slice completed without changing Project Store ownership, Product Orchestrator ownership or Capability Registry/D-017 provider/runtime boundaries. Its exact Draft head and exact Review head each passed all five permanent Ubuntu/Windows CI checks, including API/HTTP, real-media, frontend and browser user-outcome coverage.

## Project Store hardening completed

Canonical project state is now constrained to strict portable JSON at persistence boundaries:

- nested `settings`, `extensions` and reference `metadata` are recursively validated and detached;
- non-string JSON-object keys, Python-only values, recursive containers and `NaN`/`Infinity`/`-Infinity` are rejected;
- mutable nested reference metadata is revalidated before canonical document save;
- `project.json` reads reject non-standard non-finite constants and canonical writes use strict serialization while retaining atomic replacement;
- archive import reaches the same strict staged-project validation before canonical commit;
- one malformed/invalid project no longer hides unrelated healthy projects during listing;
- corrupt project bytes are preserved, with bounded Store diagnostics available for recovery tooling;
- existing project ID/path/symlink protections and migrations remain intact.

The public `/api/uv/projects` list response remains compatible: it returns healthy project payloads rather than changing response shape to include diagnostics.

## Preserved product truth

The five authoritative Class A/B Product Orchestrator journeys remain:

- `photo_to_video -> photo_composition`;
- `visualizer -> audio_visualizer`;
- `free_project -> targeted_edit`;
- `dubbing -> dubbing`;
- `music_video -> music_video`.

`main` branch protection remains an external repository-setting P0 and is not represented as fixed in code.

## Remaining release boundary

This state does **not** claim Narrated recovery, Class C cold-start usability, installed Windows human acceptance or Stage 9 release readiness. Stage 9 packaging/release remains blocked until the remaining gates are complete.

## Next authorized slice

The next authorized slice is `product-recovery-narrated-orchestration`, defined by `project-context/NEXT_TASK.md`.
