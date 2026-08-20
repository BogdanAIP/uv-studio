# UV Studio Frontend / Backend Interaction Map

## Purpose

This document maps the Stage 8 `main` frontend through its HTTP contracts into backend/domain/capability layers. The corrected audit shows that there are **two live frontend architectures** in the same Next.js application.

The backend is not generally empty. The newer UV-owned backend contains strong canonical/domain/capability layers. The product problem is that the frontend combines those layers with a still-live VideoClaw workflow shell whose backend runtime was intentionally removed at Stage 3.5.

## Actual Stage 8 high-level architecture

```text
frontend/app/layout.tsx
        |
        v
     AppShell
      /    \
     /      \
legacy       UV-owned product
sidebar      /projects
pipeline     project editor / dubbing / music / Stage8
routes       |
 |           frontend/lib/*Api.ts
workflowApi  |
 |           /api/uv/* + capabilities
old APIs     |
 X           v
(not mounted) Project Store / domain state / Capability Registry
                            |
                            v
                  FFmpeg / MLT / local ML / MCP / providers
```

The coexistence is literal: `AppShell` is the root wrapper for every route and contains VideoClaw navigation/task polling while `/projects` exposes the newer UV-owned project system.

## Architecture A — UV-owned project/product path

Important frontend clients:

- `projectsApi.ts`;
- `recipesApi.ts`;
- `editorApi.ts`;
- `renderApi.ts`;
- `dubbingApi.ts`;
- `dubbingPrecisionApi.ts`;
- `subtitleApi.ts`;
- `sequenceContinuityApi.ts`;
- `musicVideoApi.ts`;
- `musicVideoReviewApi.ts`;
- `performanceLipSyncApi.ts`;
- `stage8WorkspaceApi.ts`;
- `stage8MediaApi.ts`.

These use the current UV-owned FastAPI routers and durable Project Store/domain state.

### Canonical authorities

| Concern | Authority | Recovery decision |
|---|---|---|
| project identity/state | `uv_studio/projects` / Project Store | keep |
| recipes | `uv_studio/recipes` | keep; repair product readiness semantics |
| capability metadata | Capability Registry/offers | keep |
| capability selection | selection policy | keep |
| remote/paid authorization | D-017 authorization | keep |
| result/provenance/cancellation | capability execution layer | keep |
| edit/dubbing/music state | project domain extensions | keep |
| product readiness/next step | no single owner | add Product Orchestrator |
| generic editor ownership | React + UV state + MLT projection | re-evaluate under D-033 |

### Server composition

`uv_studio/server.py` mounts explicit UV routers for:

- configuration;
- capabilities and capability execution;
- MCP/Qwen optional integrations;
- recipes/execution projection;
- projects/archives/media;
- prepared audio;
- editor commands/state;
- replacement plan/candidate/review;
- continuity/sequence state;
- dubbing state/review/precision;
- Music Map/Direction/Assembly/Analysis/Review;
- Stage 8 workspaces/media;
- artifacts/media access.

This remains the product backend boundary.

## Architecture B — live legacy VideoClaw path

Important live frontend files:

- `frontend/lib/workflowApi.ts`;
- `frontend/components/AppShell.tsx` legacy navigation/task logic;
- `frontend/components/HomePage.tsx`;
- `frontend/components/WorkflowPanel.tsx`;
- `frontend/components/pipelines/PipelinePage.tsx`;
- `frontend/components/BrandHeader.tsx`;
- `/pipelines/standard`;
- `/pipelines/action-transfer`;
- `/pipelines/digital-human`;
- `/sandbox` and related old helpers.

### AppShell coupling

The Stage 8 `AppShell` imports from `workflowApi`:

```text
clearTempCache
fetchPipelineTasks
fetchSandboxTasks
fetchSessions
```

and places these routes in primary navigation:

```text
/
/sandbox
/pipelines/standard
/pipelines/action-transfer
/pipelines/digital-human
```

It also constructs links for old session/pipeline/sandbox running/completed tasks.

Because `frontend/app/layout.tsx` wraps all pages with `AppShell`, this legacy model is part of the normal product shell, including when the user is inside `/projects`.

### workflowApi old contracts

The live `workflowApi.ts` calls route families such as:

```text
/api/sessions
/api/pipelines/standard/tasks
/api/pipelines/action_transfer/tasks
/api/pipelines/digital_human/tasks
/api/tasks
/api/sandbox/tasks
/api/models
/api/pipelines/standard/templates
/api/upload_media
/api/project/start
/api/project/{session}/status
/api/project/{session}/execute/{stage}
/api/project/{session}/intervene
/api/project/{session}/stop
/api/project/{session}/models
/api/project/{session}/artifact/*
```

Most of these are not mounted by the current UV server.

### PipelinePage path

Each of the three `/pipelines/*` pages renders `PipelinePage`, which directly imports legacy model/task/upload/start functions from `workflowApi`.

So these are not historical files that merely compile: they are main-sidebar routes whose normal execution path points at a backend removed for security/runtime-independence reasons.

`BrandHeader` labels that UI `Video-Claw`, and `PipelinePage` uses a separate light/white form design. This makes the architecture split visible to the user as well as technical.

## Why Stage 3.5 must not be reversed

The old backend was removed because complete VideoClaw routing could bypass the UV-owned authorization/secret/runtime boundaries. A live broken legacy page is migration debt, not justification to mount that backend again.

The migration direction is:

```text
old user outcome still wanted?
  yes -> map to Product Orchestrator + current UV domain/capability action
  no  -> remove route/navigation from live product
```

not:

```text
broken old page -> restore whole old backend
```

## Projects / recipes path

```text
ProjectsPage
 -> listUVRecipes
 -> listUVProjects
 -> createUVProject / import archive
 -> Project Store

ProjectPage
 -> getUVProject
 -> getProjectExecutionPlan
 -> render generic + recipe panels
```

Problem: recipe selection is readiness-blind and project composition globally mounts unrelated specialist workflows.

## Targeted edit path

```text
source upload
 -> project source registration/probe

editor state
 -> project edit extensions + MLT projection

select range + change request
 -> editor command select_range
 -> ProjectMediaRange + RangeContinuityBrief

replacement plan
 -> candidate preparation/capability
 -> review
 -> accept
 -> render
```

This backend chain is real and should be preserved. The Product Orchestrator should translate its prerequisites/domain state into understandable next actions.

## Dubbing path

```text
project source
 -> speech.transcribe capability
 -> accepted transcript
 -> optional translation
 -> prepared speech/TTS/import
 -> review
 -> accept
 -> video.render_dubbing
 -> artifact
 -> optional alignment/subtitles
```

Real domain path. Main defects: setup visibility, internal-state burden and global mounting for unrelated recipes.

## Sequence continuity path

Dedicated sequence state/commands/take context/review exist and are useful as optional policy. The defect is product placement: it is globally visible rather than activated only when relevant.

## Music Video path

```text
song source
 -> Music Map
 -> Direction
 -> Assembly
 -> render_music_video
 -> rhythm/review
 -> artifact
```

Strong domain model; UI currently asks the user to manually author too much internal timing/shot structure. Orchestrator should propose/populate durable plans, not delete them.

## Photo -> Video path

```text
images + optional audio
 -> video.compose_photos
 -> local FFmpeg adapter
 -> artifact
```

Reference example of simple intent -> inputs -> action -> result.

## Visualizer path

```text
audio + optional artwork
 -> audio.visualize
 -> local FFmpeg adapter
 -> artifact
```

Second reference flow.

## Story / Commercial / Free path

Stage 8 workspace APIs persist useful brief/script/material selections. They are preparation state, not complete production engines. Orchestrator must expose the truthful next action rather than imply completion from workspace existence.

## Performance lip-sync path

Semantic `video.digital_human` execution through the verified MuseTalk profile is real when exact optional runtime/model/CUDA preflight succeeds. Product readiness should expose this setup requirement before entry.

## Capability architecture to preserve

```text
CapabilityDefinition
 -> CapabilityOffer(s)
 -> SelectionPolicy
 -> D-017 Authorization
 -> Execution
 -> Adapter
 -> Result + provenance + artifact
```

Important invariants:

- semantic capability IDs remain provider-neutral;
- `local_free_first` fails closed;
- paid/remote execution is explicit;
- adapters are peers, not one mandatory runtime;
- project-scoped inputs prevent arbitrary host-path execution;
- results/provenance are explicit.

Product Orchestrator consumes this layer; it does not replace it.

## Project/domain state to preserve

Project Store owns typed/versioned state for edits, replacement plans/candidates/reviews, dubbing, music, continuity, Stage 8 workspaces, archives and migrations. This is why recovery is not a rewrite.

## Main architectural gap

There are actually **two gaps**.

### Gap 1 — no product-level next-action owner for UV workflows

Today:

```text
React component
 -> inspect several domain states
 -> infer prerequisites
 -> disable/enable control
 -> invoke specialized API
 -> refresh
```

Target:

```text
Product Orchestrator
 -> canonical state + runtime availability
 -> readiness + prerequisites + relevant workspaces + next actions

React
 -> render product projection
 -> collect bounded input
 -> invoke semantic action
```

### Gap 2 — old live frontend still targets removed runtime

Today:

```text
AppShell / PipelinePage / WorkflowPanel
 -> workflowApi
 -> removed VideoClaw backend routes
```

Target:

- remove old pipeline/session/sandbox navigation from normal shell unless rebuilt on current semantics;
- retire duplicate project/task authority;
- preserve wanted outcomes only through UV-owned commands/capabilities.

## Migration rule

Do not flatten all domain APIs into one giant controller. Consolidate **product action semantics**, not every HTTP route.

Music Map, Dubbing Review and Replacement Review may remain coherent dedicated domains. Product Orchestrator maps them into stable user actions.

## Immediate Product Orchestrator seam

Recommended next-slice family:

```text
GET /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

Start with a read projection plus one representative action. It should contain:

- truthful readiness;
- prerequisites;
- relevant workspaces;
- next actions;
- active jobs;
- recent result artifacts;
- separate diagnostics.

No new canonical workflow store is introduced.

## UI-isolation companion work

The same next recovery phase should make the shell Product-Orchestrator-aware and stop exposing the legacy VideoClaw runtime surfaces as normal navigation. This is not merely cosmetic: it removes user entry points into APIs the backend intentionally does not provide.
