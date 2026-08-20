# UV Studio Product Truth Matrix

## Purpose

This document records the D-062 Stage 8 audit baseline and the current recovery
status. A feature is not `working` merely because source code, domain state or
tests exist; it is working only when a user-visible action reaches a current
mounted UV-owned execution path and produces the expected result.

Status values:

- `working` — current UI -> current mounted API -> implementation -> result;
- `working_orchestrated` — `working` plus truthful Product Orchestrator readiness,
  prerequisites, relevant workspace and semantic next action;
- `working_with_setup` — complete path exists after an explicit optional runtime/config prerequisite;
- `partial` — valuable pieces exist but the product journey is incomplete;
- `misleading` — UI/metadata implies readiness that current backend execution does not support;
- `live_legacy_broken` — compiled/routable live legacy UI calls routes intentionally absent from the UV-owned server;
- `vendor_donor` — pinned upstream provenance under `vendor/` only.

## Fundamental Stage 8 architecture split

At the D-062 audit baseline, the live product contained **two frontend
architectures at once**.

### A. UV-owned project architecture

```text
/projects
 -> Project Store
 -> Recipe Registry
 -> ProjectEditor / Dubbing / Music / Stage8 workspaces
 -> UV-owned /api/uv/* and capability APIs
 -> Project/domain state + Capability Registry
 -> FFmpeg / MLT / ML / MCP / provider adapters
```

### B. Live legacy VideoClaw architecture

```text
AppShell sidebar
 -> /sandbox
 -> /pipelines/standard
 -> /pipelines/action-transfer
 -> /pipelines/digital-human
 -> workflowApi.ts
 -> /api/pipelines/* /api/tasks /api/sessions /api/models /api/upload_media /api/project/* /api/sandbox/*
```

Most of the latter backend routes were intentionally removed from `uv_studio/server.py` by Stage 3.5.

The legacy layer is not only under `vendor/`: `frontend/lib/workflowApi.ts`,
`HomePage.tsx`, `WorkflowPanel.tsx`, `PipelinePage.tsx` and the three pipeline
routes remain compiled migration debt. In the audit baseline, `AppShell`
imported `workflowApi` and placed legacy routes in primary navigation. The
Product Orchestrator foundation replaces that shell with a UV-owned project
shell that neither links nor polls those routes.

This is a central Product Truth defect: the new UV product was added without completing retirement/isolation of the old runtime-facing frontend.

## Current server boundary

`uv_studio/server.py` mounts UV-owned routers for configuration, capabilities/execution, MCP/Qwen pack, recipes, projects/media, editor commands, replacement workflow, dubbing, sequence continuity, music, Stage 8 workspaces and artifact/media access.

It does **not** mount the complete old VideoClaw runtime. Important absent families include:

- `/api/pipelines/*`;
- `/api/tasks*`;
- `/api/sessions*`;
- `/api/models*`;
- `/api/upload_media`;
- most `/api/project/*` old workflow routes;
- `/api/sandbox/*`.

`/api/stages` remains only a compatibility metadata endpoint and does not restore those workflows.

## Main-shell truth

The audited Stage 8 `AppShell` imported `clearTempCache`, `fetchPipelineTasks`,
`fetchSandboxTasks` and `fetchSessions` from `workflowApi` and defined primary
navigation for:

```text
/
/sandbox
/pipelines/standard
/pipelines/action-transfer
/pipelines/digital-human
/settings
```

The pipeline pages use a separate `Video-Claw` BrandHeader and light controls. They are therefore both a backend-contract problem and a second visible design system.

The Product Orchestrator recovery shell now advertises `/projects` and the
currently mounted `/settings` configuration surface only. It does not import or
poll the old workflow client. The settings page no longer mounts the historical
Video-Claw header; its mixed-language field copy remains presentation migration
debt, not a second workflow/runtime contract.

## UV project-page composition audit

Inside the newer `/projects/{projectId}` architecture, workflows are also not isolated by recipe. The page always mounts:

1. `ProjectEditor`;
2. `SequenceContinuityPanel`;
3. `DubbingWorkflowPanel`;
4. `DubbingPrecisionPanel`;
5. `DubbingSubtitleExportPanel`;
6. execution-plan diagnostics;
7. archive/recovery controls.

Recipe-specific panels are then appended:

- story/commercial/free -> `Stage8CompositionPanel`;
- music -> Music Map/Assembly/Review panels;
- photo/visualizer -> `Stage8MediaPanel`;
- performance lip-sync -> `PerformanceLipSyncPanel`.

Thus even after entering the new Project Store architecture, a selected task does not isolate its relevant workflow. This contradicts the Stage 2 product promise that selecting a task loads only the needed stages.

## Core UV frontend -> backend ownership map

| User area | Live UV frontend | Current backend authority | Truth |
|---|---|---|---|
| project create/open/archive | project pages + `projectsApi` | Project Store | strong foundation |
| generic source import | `ProjectEditor` / `editorApi` | project media/editor state | real |
| targeted range selection | `ProjectEditor` | editor commands + continuity brief | real, prerequisites implicit |
| replacement plan/candidate/review | replacement panels | dedicated replacement APIs + capabilities | real, state machine exposed |
| final edit render | render panel | accepted edit + media render | real |
| sequence continuity | continuity panel | sequence state/review APIs | real optional policy, globally displayed |
| dubbing | dubbing panels/APIs | ASR/capabilities + dubbing domain state | substantial real workflow, setup/state heavy |
| music map/direction | music panels/APIs | Music Map/Direction | real, low-level authoring burden |
| music assembly/review | music panels/APIs | Assembly/Review + media render | real |
| Photo -> Video | Product Orchestrator -> `Stage8MediaPanel` | workflow action -> `video.compose_photos` | first orchestrated real local path |
| Visualizer | `Stage8MediaPanel` | `audio.visualize` | clean real local path |
| Story/Commercial preparation | `Stage8CompositionPanel` | Stage 8 workspace state | real preparation, not full production |
| Performance lip-sync | dedicated panel | verified MuseTalk capability path | real with explicit setup |
| project readiness | Product Orchestrator block | Project Store + verified Source Media + Recipe/Capability Registry projection | implemented for Photo -> Video; other recipes fail closed as partial |

## Live legacy frontend -> disabled backend map

| Live surface | Client calls | Current backend truth | Status |
|---|---|---|---|
| legacy `AppShell` sidebar/task implementation | sessions/tasks/sandbox cache APIs | most routes absent | isolated from the normal shell; retained only in Git history |
| `/pipelines/standard` | models/templates/upload/standard task/task events | routes absent | `live_legacy_broken` |
| `/pipelines/action-transfer` | models/upload/action-transfer task/task events | routes absent | `live_legacy_broken` |
| `/pipelines/digital-human` | models/upload/digital-human task/task events | routes absent | `live_legacy_broken` |
| `WorkflowPanel` / `HomePage` old main workflow | `/api/project/start`, status, execute, intervene, artifacts, sessions | old workflow runtime absent | `live_legacy_broken` unless fully unreachable from current route entry |

Compiled legacy route source remains migration debt, but the normal shell no longer
links or polls those surfaces. Direct retirement is a later bounded cleanup.

## Recipe matrix

| Recipe | Intended outcome | UV-owned path truth | Baseline status | Recovery action |
|---|---|---|---|---|
| `general_video` | brief -> general video | no complete current brief -> plan -> assets -> assembly -> export path | `partial` | gate truthfully; build orchestrated UV path |
| `narrated_video` | topic/script -> narration -> visuals -> video | baseline RecipeExecutionPlan advertised unmounted `/api/pipelines/standard/tasks`; a separate live legacy standard page also calls the same disabled API | `misleading` + legacy broken surface | recovery plan now fail-closed; later implement current semantic path |
| `music_video` | song-driven clip | substantial UV Music Map/Direction/Assembly/Review domain path | `partial` UX | orchestrator proposes analysis/direction instead of forcing low-level manual map authoring |
| `action_transfer` | motion source + target image -> result | baseline plan and live legacy pipeline both target disabled `/api/pipelines/action_transfer/tasks`; semantic capability exists separately | `misleading` | fail closed; later bind authorized capability workflow or remain unavailable |
| `digital_human` | portrait + speech -> talking video | current UV recipe is partial/setup-dependent; separate legacy page calls disabled promo pipeline | `partial` + legacy broken surface | keep capability-gated; retire legacy promo path |
| `story_video` | story -> video | typed brief/script/material workspace plus generic leaked panels | `partial` | orchestrate production after core flow isolation |
| `commercial_product` | product brief/materials -> ad video | preparation state plus generic leaked panels | `partial` | orchestrated product flow |
| `photo_to_video` | photos + optional audio -> video | Product Orchestrator action delegates to the real local FFmpeg capability path | `working_orchestrated` | first reference journey; keep permanent evidence |
| `visualizer` | audio + optional artwork -> video | real local FFmpeg capability path | `working` but shell/page polluted | use as UX reference |
| `performance_lip_sync` | portrait + speech -> lip sync | verified optional MuseTalk path | `working_with_setup` | show setup before entry |
| `free_project` | flexible tools | real primitives but no next-action owner; unrelated workflows globally visible | `partial` | orchestrator/tool palette |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | no complete UV-owned path | `partial` | Product Orchestrator + execution baseline |
| B. Narrated video | old plan and live legacy pipeline pointed to disabled backend | `misleading` baseline; recovery fail-closed | new narrated workflow |
| C. Music-video excerpt | real domain/assembly/review, backend-schema-heavy UX | `partial` | intent-first orchestration |
| D. Dubbing | substantial real path; runtime/setup and many internal gates | `working_with_setup` / UX-partial | prerequisite projection + isolation |
| E. Targeted edit | real range/replacement/review/render | `working` / UX-partial | simplify next actions |

## Confirmed product-surface defects

### Cross-workflow leakage

A Photo -> Video, Story or Music project receives unrelated edit/continuity/dubbing panels because project-page composition is universal-first rather than recipe/orchestrator-driven.

### Readiness-blind project creation

Recipe cards look similarly selectable before the user knows whether a mode is working, partial, setup-required or unavailable.

### Hidden edit prerequisites

`ProjectEditor` disables the primary change action until source + valid range + change text all exist. The later UI exposes durable `Brief -> Plan -> Candidate -> Review -> Accepted -> Render` vocabulary. The domain model is valuable; the product explanation is not sufficient.

### Dual navigation/state models

At the audit baseline, the global shell showed legacy session/task/pipeline
concepts while `/projects` used Project Store/project IDs. The Product
Orchestrator foundation removes that competing model from the normal shell.

### Broken legacy pipeline execution

The three main-sidebar pipeline routes render real pages but their `workflowApi` task/model/upload endpoints are not mounted by the UV server.

### Two visual systems

Legacy `PipelinePage`/BrandHeader use Video-Claw branding and white controls while UV project surfaces use a different product theme. This can directly produce the “white field inside dark app” class of experience in addition to any separate missing CSS bugs.

## False recipe contracts repaired in this branch

### `narrated_video`

Stage 8 baseline required `AVAILABLE` + `/api/pipelines/standard/tasks`. Recovery changes the base plan to `UNAVAILABLE`, `target=None`, retaining typed inputs and runtime capability requirements.

### `action_transfer`

Stage 8 baseline required `AVAILABLE` + `/api/pipelines/action_transfer/tasks`. Recovery fails closed while preserving `video.action_transfer` readiness metadata and production policy.

### New invariant

Any future non-null base `RecipeExecutionPlan.target` must exist in the actual FastAPI route table. Base compatibility cannot silently advertise an absent route.

This invariant intentionally does not define the eventual Product Orchestrator readiness semantics.

## Why execution-plan is not enough

`/execution-plan` mixes compatibility-target planning with Stage 8 capability readiness. Capability-driven Photo/Visualizer/Performance modes can become `available` with `target=None`, which is valid at that lower layer.

Therefore Product Orchestrator must provide separate:

- `readiness`;
- `prerequisites`;
- relevant workspaces;
- `next_actions`;
- jobs/results;
- diagnostics.

## Product Orchestrator contract — next slice

```text
ProjectWorkflowState
- schema_version
- project_id
- recipe_id
- readiness: ready | setup_required | partial | unavailable
- summary
- relevant_workspaces[]
- prerequisites[]
- next_actions[]
- active_jobs[]
- recent_artifacts[]
- diagnostics[]
```

Each prerequisite is structured and each next action has a stable semantic ID, visible explanation, enabled/blocked state, bounded input schema, execution/authorization class and expected result.

The orchestrator is a projection over Project Store/domain state plus runtime availability. It is **not** a second canonical workflow store and does not replace coherent domain APIs.

## Recovery sequencing implication

The next implementation phase has two jobs:

1. introduce Product Orchestrator over the good UV-owned domain/capability architecture;
2. remove/isolate legacy VideoClaw navigation and runtime-facing surfaces from the normal shell instead of remounting the unsafe old backend.

Only after these are separated should broader visual redesign proceed.

## Test evidence

Existing browser suites remain informed regression evidence. A later cold-start class must begin from user-equivalent state, must not seed transcripts/plans/reviews/Music Maps through hidden APIs, and must fail on broken legacy navigation, irrelevant workspaces and unexplained disabled primary actions.
