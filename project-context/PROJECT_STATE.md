# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: studio-v2-editor-spine -->
<!-- uv-last-completed: product-usability-class-c-cold-start -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

A new clean Studio-v2 slice is active in Draft PR #60 on branch `studio-v2/editor-spine`, based exactly on maintained `main` `6f656a9a3b3ea885b3280e7dd6a9594daf1dcaf7`.

The last merged lifecycle slice remains Class C cold-start usability PR #58, merge `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

PR #59 was intentionally **closed without merge** after product review rejected the recipe/workspace/wizard-centered direction. Its 79-commit branch remains an engineering reference, especially for the proven Windows host/installer/integrity/update/rollback work, but it is not a maintained product baseline.

## Architecture conclusion

D-063 is the current long-term product-composition authority.

UV Studio is now being developed as a **Studio-first professional video/AI editing workspace**:

- the project is the primary product object, not a recipe;
- normal Studio composition is Media/Scenes + Preview + Inspector/AI Tools + multitrack Timeline;
- AI model choice is visible to the user inside the relevant tool;
- Settings configure provider/runtime connections, while Studio tools choose named models and creative parameters;
- GUI, Agent, scripts and MCP use the same UV-owned semantic/application commands;
- Project Store remains canonical;
- MLT + selective OpenCut Classic reuse from D-033 remain the editor foundation;
- Capability Registry, D-017 and MCP remain the replaceable execution/security layer underneath a future user-visible Model Registry;
- targeted edit, dubbing, music, continuity, slideshow/visualizer and similar proven logic migrate into contextual Studio tools instead of top-level project modes.

See:

- `project-context/decisions/D-063-studio-first-product-architecture.md`;
- `docs/architecture/UV_STUDIO_V2_ARCHITECTURE_MAP.md`.

## What is good and retained

The architecture audit found a strong lower foundation that must not be rewritten:

- Project Store, project-owned paths/references, archive/migrations and integrity checks;
- D-033 editor foundation and the existing `ProjectEditor`/`RangeTimeline` seed;
- MLT behind a UV adapter and FFmpeg deterministic media paths;
- UV-owned Editor/Domain Command authority;
- Capability Registry, offer selection and exact D-017 authorization;
- MCP discovery/binding/execution boundaries;
- targeted-edit, dubbing/translation, continuity and music domain/review logic where it protects real invariants;
- previously proven Windows packaging/native-host engineering, to be selectively ported from archived #59 after the Studio product spine is accepted.

## What is now compatibility/legacy

Do not grow these as the long-term product center:

- new-project identity based on `recipe_id`;
- recipe-by-recipe Product Orchestrator growth;
- Stage 6/Stage 8 as user-facing product structure;
- specialized project workspaces when a contextual Studio tool can own the action;
- legacy `/execution-plan` as a second modern truth;
- old VideoClaw `/api/pipelines`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/project/*` frontend clients;
- donor-era frontend `modelRegistry.ts` as the future model architecture.

Compatibility code remains until callers are proven migrated; this is a strangler migration, not a delete-first rewrite.

## Current active proof — Studio v2 editor spine

PR #60 must prove a local/editor-first path before provider work:

```text
Project
 -> Media Bin
 -> import existing image/video
 -> shared UV timeline command
 -> canonical multitrack timeline
 -> close/reopen
 -> Preview/Timeline
 -> derived MLT projection
 -> deterministic export
```

Required properties:

- no recipe selection in the v2 path;
- no Stage 8 workspace in the v2 path;
- Studio shell exposes Media Bin, Preview, Inspector and Timeline;
- bounded clip add/move/trim/remove mutations use UV commands also callable programmatically;
- canonical timeline survives reload;
- MLT remains derived rather than canonical;
- export/result is project-owned and registered;
- schema-v1/recipe projects remain readable through compatibility boundaries.

## Open-source reuse rule

Reuse-first remains a core strategy and is reaffirmed by D-063.

Correct pattern:

`candidate -> license/evidence spike -> pin -> UV adapter/command -> needed primitive -> tests -> Studio tool`

Rejected pattern:

`donor -> copy donor application/workflow/project model -> expose it as another UV mode`

This preserves the benefits of MLT, OpenCut, FFmpeg, Whisper-family tools, MCP servers and future open-source systems without allowing donor architecture to define UV Studio.

## Verification status

The maintained `main` baseline is still the post-Class-C state from PR #58. PR #60 has only established the new durable architecture/context so far; the Studio editor-spine implementation and exact-head CI evidence are still pending.

Historical Release #395 on archived #59 remains evidence for Windows packaging/runtime engineering only. It is **not** human product acceptance and must not be reused as proof of Studio v2 behavior.

`main` branch protection remains intentionally deferred per current development direction.

## Next authorized slice after PR #60

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`.

After transaction/undo foundations, proceed to a backend-owned user-visible Model Registry, then Job Manager, then one real named Image AI vertical.
