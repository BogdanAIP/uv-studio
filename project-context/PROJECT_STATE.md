# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: studio-v2-editor-spine -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Studio v2 editor-spine is frozen for Review in PR #61 on branch `stage-10/studio-v2-editor-spine`, based exactly on maintained `main` `6f656a9a3b3ea885b3280e7dd6a9594daf1dcaf7`.

Draft candidate `1837ae279723902ca0b80674c4ca5a0bb4b76a3a` passed the complete permanent CI set in run #2912 on Ubuntu and Windows, including browser user-outcome evidence. The lifecycle-only review transition creates a new exact review head; that head must independently pass the same five required checks before merge.

The last merged lifecycle slice remains Class C cold-start usability PR #58, merge `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

PR #59 was intentionally closed without merge after product review rejected the recipe/workspace/wizard-centered direction. PR #60 was a short-lived branch-name/lifecycle mismatch and was superseded without merge by #61. Neither is a maintained product baseline.

## Architecture conclusion

D-063 is the current long-term product-composition authority.

UV Studio is being developed as a **Studio-first professional video/AI editing workspace**:

- the project is the primary product object, not a recipe;
- normal Studio composition is Media Bin + Preview + Inspector/AI Tools + multitrack Timeline;
- GUI, Agent, scripts and MCP converge on the same UV-owned semantic/application commands;
- Project Store remains canonical;
- MLT is a derived editor-engine projection, never project truth;
- FFmpeg remains the first deterministic local export path;
- Capability Registry, D-017 and MCP remain the replaceable execution/security layer underneath a future user-visible Model Registry;
- targeted edit, dubbing, music, continuity, slideshow/visualizer and similar proven logic migrate into contextual Studio tools instead of top-level project modes.

See:

- `project-context/decisions/D-063-studio-first-product-architecture.md`;
- `docs/architecture/UV_STUDIO_V2_ARCHITECTURE_MAP.md`.

## What is good and retained

The architecture audit found a strong lower foundation that must not be rewritten:

- Project Store, project-owned paths/references, archive/migrations and integrity checks;
- D-033 editor foundation;
- MLT behind a UV adapter and FFmpeg deterministic media paths;
- UV-owned editor/domain command authority;
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

## Review candidate — Studio v2 editor spine

PR #61 contains the first real vertical implementation:

```text
Project
 -> Media Bin
 -> import existing image/video/audio
 -> shared UV timeline command
 -> canonical timeline/main.json
 -> close/reopen
 -> Preview/Timeline
 -> derived MLT projection
 -> bounded deterministic FFmpeg export
 -> registered project-owned export
```

Implemented properties:

- Studio project creation no longer asks for recipe selection;
- Studio runtime does not read a recipe to decide editing or export behavior;
- canonical multitrack Video/Audio timeline is project-owned;
- create-track/add/move/trim/remove mutations use `TimelineCommandService`;
- MLT projection is derived only from canonical timeline state and keeps resolved host paths out of its public summary;
- first renderer fails closed outside one contiguous active visual track plus at most one covering audio clip;
- registered Studio exports are streamed through a Studio-scoped project-owned endpoint;
- `/projects/{projectId}/studio` exposes Media Bin, Preview, Inspector/AI Tools and Timeline;
- old recipe projects remain readable through explicit compatibility links.

Schema v1 still requires a `recipe_id`; new Studio projects therefore carry neutral `studio_v2` compatibility metadata. Timeline, MLT and Studio render execution do not branch on that value.

## Open-source reuse rule

Reuse-first remains a core strategy and is reaffirmed by D-063.

Correct pattern:

`candidate -> license/evidence spike -> pin -> UV adapter/command -> needed primitive -> tests -> Studio tool`

Rejected pattern:

`donor -> copy donor application/workflow/project model -> expose it as another UV mode`

This preserves the benefits of MLT, OpenCut, FFmpeg, Whisper-family tools, MCP servers and future open-source systems without allowing donor architecture to define UV Studio.

## Verification status

Draft candidate `1837ae279723902ca0b80674c4ca5a0bb4b76a3a` passed CI run #2912:

- development-context — success;
- bootstrap Ubuntu — success;
- bootstrap Windows — success;
- app-baseline Ubuntu — success;
- app-baseline Windows — success.

Both app-baseline jobs passed API integration, real-media tests, frontend lint/audit/build and the browser user-outcome suite. The Class-C browser path now proves visible Studio-first creation, media import, timeline create/add/trim, navigation away and reopen persistence, and real local export without recipe selection or direct Project Store seeding.

This automated evidence is not human installed-Windows acceptance. No such human acceptance is claimed for this slice.

The Review head is frozen except for review fixes. Merge remains blocked until the exact Review head passes all five permanent checks and there are no unresolved review threads.

Historical Release #395 on archived #59 remains evidence for Windows packaging/runtime engineering only. It is **not** human product acceptance and must not be reused as proof of Studio v2 behavior.

`main` branch protection remains intentionally deferred per current development direction.

## Next authorized slice after PR #61

`studio-v2-application-transactions`, defined by `project-context/NEXT_TASK.md`.

After transaction/undo foundations, proceed to a backend-owned user-visible Model Registry, then Job Manager, then one real named Image AI vertical.
