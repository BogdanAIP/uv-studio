# UV Studio Product Truth Matrix

## Purpose

This document keeps two things separate:

1. the **D-062 Stage 8 audit baseline** that explains how the product became confusing;
2. the **current recovery state** after PR #42 and PR #43.

Historical baseline findings must not be written as if they still describe the current shell, and current partial recovery must not be overstated as application-wide completion.

A feature is `working` only when a user-visible action reaches a current mounted UV-owned path and produces the expected state/artifact.

Status values:

- `working` — current UI -> current mounted API -> implementation -> result;
- `working_orchestrated` — `working` plus truthful Product Orchestrator readiness/prerequisites/relevant workspace/semantic next action;
- `working_with_setup` — complete path exists after an explicit optional runtime/config prerequisite;
- `partial` — valuable implementation exists but the user journey is incomplete;
- `unavailable` — intentionally fail-closed at the current product boundary;
- `historically_misleading` — an older visible/metadata contract advertised execution that was not actually mounted;
- `legacy_isolated` — legacy source still exists but is no longer part of the supported normal shell;
- `live_legacy_broken` — compiled/routable legacy page still depends on backend contracts intentionally absent from the UV-owned server.

## Current top-level architecture

```text
/projects
 -> UV-owned AppShell
 -> Project Store
 -> Recipe Registry
 -> Product Orchestrator where migrated
 -> UV semantic/domain APIs
 -> Capability Registry / D-017
 -> FFmpeg / MLT / local ML / MCP / provider adapters
```

The supported normal shell now exposes Projects and Settings. It no longer polls old VideoClaw sessions/tasks/sandbox state or advertises `/pipelines/*` as primary product navigation.

## Historical D-062 frontend split

At the Stage 8 audit baseline the live build combined:

```text
UV Project Store UI
+
legacy VideoClaw AppShell/session/task/pipeline UI
```

The legacy UI called `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/upload_media`, old `/api/project/*` and `/api/sandbox/*` contracts that Stage 3.5 had intentionally stopped mounting.

PR #43 corrected the **normal shell** side of this split. Legacy source such as `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and `/pipelines/*` routes still remains migration debt, but the supported AppShell no longer links or polls it.

## Current server boundary

`uv_studio/server.py` mounts UV-owned routers for projects/media, recipes, Product Orchestrator, editor/replacement state, dubbing, sequence continuity, music, Stage 8 workspaces, capabilities/execution, MCP and configuration.

It intentionally does **not** restore the complete historical VideoClaw runtime. Important absent families still include:

- `/api/pipelines/*`;
- `/api/tasks*`;
- `/api/sessions*`;
- `/api/models*`;
- `/api/upload_media`;
- most historical `/api/project/*` workflow routes;
- `/api/sandbox/*`.

## Current project-page composition

The old statement “the project page always mounts Editor + Continuity + Dubbing for every recipe” is now only a **baseline historical finding**.

Current code behaves as follows:

- `photo_to_video` is the first isolated Product Orchestrator flow and mounts its projected `photo_composition` workspace instead of generic Editor/Continuity/Dubbing panels;
- every **non-photo** recipe still receives `ProjectEditor`, `SequenceContinuityPanel`, `DubbingWorkflowPanel`, `DubbingPrecisionPanel` and `DubbingSubtitleExportPanel` before/alongside recipe-specific panels;
- music, story/commercial/free, visualizer and performance then add their specialist panels by `recipe_id`.

Therefore cross-workflow leakage is **fixed for Photo-to-Video only**, not application-wide.

## Core frontend -> backend truth

| User area | Current UI/API | Backend authority | Current truth |
|---|---|---|---|
| project create/open/archive | project pages + `projectsApi` | Project Store | **strong foundation** |
| Photo → Video | Product Orchestrator -> `Stage8MediaPanel` | workflow action -> `video.compose_photos` -> local FFmpeg | **working_orchestrated** |
| Visualizer | recipe-specific `Stage8MediaPanel` | `audio.visualize` -> local FFmpeg | **working**, not orchestrated yet |
| generic video import/preview | `ProjectEditor` / `editorApi` | project source media/editor state | **working** |
| targeted range selection | `ProjectEditor` -> `/editor/commands` | `EditorCommandService` + Continuity Brief | **working** |
| replacement plan/candidate/review | replacement UI/APIs | UV replacement domains + capabilities | **working**, internal state too visible |
| accepted edit render | render panel | accepted edit state + bounded media render | **working** |
| sequence continuity | continuity panel/APIs | sequence domain | **working optional domain**, still overexposed |
| dubbing | dubbing panels/APIs | ASR/translation/speech/alignment/review/render domains | **substantial working path**, setup/UX partial |
| music map/direction | music UI/APIs | Music Map/Direction domain | **working domain**, authoring burden high |
| music assembly/review | music UI/APIs | Assembly/Review + render | **working domain** |
| Story/Commercial preparation | `Stage8CompositionPanel` | Stage 8 composition state | **partial production journey** |
| Performance lip-sync | dedicated panel | verified optional MuseTalk capability path | **working_with_setup** |
| product workflow readiness | Product Orchestrator | Project Store + verified source state + Recipe/Capability Registry | **Photo only**; other recipes currently fail closed as `partial`/unavailable projection |

## Legacy frontend truth

| Legacy surface | Current shell exposure | Backend truth | Status |
|---|---|---|---|
| old session/task/sandbox AppShell behavior | removed from supported AppShell | backend families absent | `legacy_isolated` |
| `/pipelines/standard` | not normal-shell navigation | historical endpoints absent | `live_legacy_broken` source/route debt |
| `/pipelines/action-transfer` | not normal-shell navigation | historical endpoints absent | `live_legacy_broken` source/route debt |
| `/pipelines/digital-human` | not normal-shell navigation | historical endpoints absent | `live_legacy_broken` source/route debt |
| old HomePage/WorkflowPanel | no supported product authority | historical workflow runtime absent | `legacy_isolated` / migration debt |

The correct recovery action is dependency-proven retirement/migration, **not** remounting the old backend.

## Recipe matrix — current recovery truth

| Recipe | Intended outcome | Current UV-owned path | Status | Required recovery |
|---|---|---|---|---|
| `general_video` | brief -> general video | no complete brief -> plan -> assets -> assembly -> export journey | `partial` | build orchestrated current path |
| `narrated_video` | topic/script -> narration -> visuals -> video | historical stale pipeline target removed; no replacement full journey yet | `unavailable` product execution | implement current semantic path |
| `music_video` | song-driven clip | real Music Map/Direction/Assembly/Review domains | `partial` UX | intent-first orchestration over existing domains |
| `action_transfer` | motion source + target -> result | semantic capability exists, historical pipeline target removed | `unavailable` product journey | build authorized current workflow or keep unavailable |
| `digital_human` | portrait + speech -> talking video | capability/domain pieces exist; no complete baseline journey | `partial` | truthful capability-gated workflow |
| `story_video` | story -> video | brief/script/material workspace | `partial` | extend from preparation to orchestrated production |
| `commercial_product` | brief/materials -> ad video | preparation workspace | `partial` | orchestrated production path |
| `photo_to_video` | photos + optional audio -> video | Product Orchestrator `compose_photos` -> local FFmpeg | `working_orchestrated` | preserve as first reference journey |
| `visualizer` | audio + optional artwork -> video | real `audio.visualize` local path, but Product Orchestrator reports generic not-migrated state | `working`, orchestration missing | next deterministic orchestration reference |
| `performance_lip_sync` | portrait + speech -> lip-sync | verified optional MuseTalk path | `working_with_setup` | show setup/readiness before use |
| `free_project` | flexible tools | reusable primitives, no coherent next-action owner | `partial` | orchestrated tool palette, not every specialist workflow at once |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | no complete UV-owned journey | `partial` | orchestration + execution baseline |
| B. Narrated video | historical path fail-closed; replacement incomplete | `unavailable/partial` | new narrated workflow |
| C. Music-video excerpt | strong domains, schema-heavy journey | `partial` | intent-first orchestration |
| D. Dubbing | substantial real path with runtime/setup gates | `working_with_setup` / UX-partial | prerequisite projection + task isolation |
| E. Targeted edit | real range/replacement/review/render | `working` / UX-partial | simplify next actions + D-033 conformance |

## Confirmed current defects

### Cross-workflow leakage remains for non-photo recipes

Photo-to-Video is no longer evidence for this defect. Visualizer, Story, Music and other non-photo projects still receive unrelated generic editor/continuity/dubbing workspaces because current project-page routing is only partly orchestrator-driven.

### Recipe creation is readiness-blind

`/projects` shows recipe cards before Product Orchestrator has a pre-project/readiness projection. Working, setup-gated, partial and unavailable tasks therefore look more equivalent than they are.

### Product Orchestrator coverage is one journey, not two

Only `photo_to_video` is currently implemented in `project_workflow_state()`. Visualizer has a real local capability path but remains unmigrated at the product orchestration layer.

### Targeted edit exposes implementation vocabulary

The durable Brief -> Plan -> Candidate -> Review -> Accepted model is valuable, but ordinary users currently see too much of that state machine. Recovery should preserve domain rigor while making the next product action obvious.

### D-033 command-boundary defect

Accepted range edits are canonical non-destructive timeline state. The historical direct `DELETE /api/uv/projects/{project_id}/edits/{edit_id}` route mutates `RangeEditStateStore` without going through the product-owned editor Command API. PR #44 tracks this bounded conformance repair; see `EDITOR_FOUNDATION_CONFORMANCE.md`.

### Legacy routes remain source debt

The supported shell is repaired, but direct legacy `/pipelines/*` pages still compile while requiring intentionally absent backend contracts. They remain retirement/migration debt rather than supported functionality.

## Recipe execution-plan truth

PR #42 repaired the historically misleading `narrated_video` and `action_transfer` base execution targets. A base `RecipeExecutionPlan.target` may no longer advertise an unmounted FastAPI route.

`RecipeExecutionPlan` is still a lower compatibility/capability layer; it is **not** Product Orchestrator readiness. Product Orchestrator separately owns user-facing:

- readiness;
- prerequisites;
- relevant workspaces;
- next actions;
- current/recent outcomes;
- diagnostics.

## Product Orchestrator contract status

```text
ProjectWorkflowState
- schema_version
- project_id / recipe_id
- readiness
- summary / current_outcome
- prerequisites[]
- relevant_workspaces[]
- next_actions[]
- active_jobs[]
- user_decisions[]
- recent_artifacts[]
- diagnostics[]
```

The contract is a projection over canonical state and runtime availability, not a second workflow database.

The current first action, `compose_photos`, is capability-backed. Future orchestration must not assume every semantic next action necessarily maps one-to-one to a capability; domain decisions such as approve/reject/accept may remain UV-owned domain commands.

## Test evidence

Existing browser suites are Class B informed regression evidence. They prove real frontend/backend/media paths but may know hidden state or setup order.

Class C cold-start product tests must start from user-equivalent state, avoid API seeding of workflow decisions, fail on unexplained disabled actions or irrelevant workspaces, and prove an actual artifact for any task advertised as ready.

Installed Windows human acceptance remains Class D and release-blocking.
