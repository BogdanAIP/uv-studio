# UV Studio Frontend / Backend Interaction Map

## Purpose

This document maps the Stage 8 `main` product from visible frontend surfaces through HTTP contracts into UV-owned domain state and capability adapters. It exists to support Product Truth Recovery and the next Product Orchestrator slice.

The key finding is not that the backend is missing. Much of it is real and well separated. The problem is that the frontend currently composes many domain APIs directly, so product-level workflow truth is distributed across React state, route-specific API clients and backend extension state.

## Current high-level architecture

```text
Next.js pages/components
        |
        v
frontend/lib/*Api.ts
        |
        v
FastAPI uv_studio/api/*
        |
   +----+--------------------+
   |                         |
   v                         v
Project/domain modules   Capability execution
uv_studio/projects/*     registry/selection/auth
uv_studio/editor/*              |
                               v
                     local / MCP / native adapters
                               |
                     FFmpeg / MLT / ML / providers
```

## Canonical authorities

| Concern | Current authority | Assessment |
|---|---|---|
| project identity/state | `uv_studio/projects` / Project Store | strong, keep |
| recipe semantics | `uv_studio/recipes` | keep, repair readiness semantics |
| provider/runtime capability metadata | `uv_studio/capabilities/registry.py` + offers | strong, keep |
| capability selection | `uv_studio/capabilities/selection.py` | strong, keep |
| paid/remote authorization | `uv_studio/capabilities/authorization.py` | strong, keep |
| capability execution result/provenance | capability execution + provenance | strong, keep |
| edit/dubbing/music durable state | project extension/domain modules | valuable, keep |
| product next-step/readiness | **no single authority** | missing Product Orchestrator |
| visible workflow composition | React project page/components | currently too authoritative; refactor |
| editor engine projection | UV edit state -> MLT adapter | re-evaluate ownership under D-033 |

## Server composition

`uv_studio/server.py` is the UV-owned FastAPI boundary. It mounts explicit UV routers instead of the whole vendored VideoClaw app.

Major mounted families:

```text
configuration
capabilities
capability execution
MCP / optional Qwen integration
recipes
recipe execution projection
projects / archives / media
prepared audio
editor commands / editor state
replacement plan / candidate / review
continuity brief
sequence continuity / review assist
music map / direction / assembly / analysis assist / review
Stage 8 workspace
artifact/media files
```

Historical vendor `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/upload_media`, `/api/sandbox/*` are not product routes.

## Frontend API modules

The live UV-owned `frontend/lib` is already substantially independent from the vendored `workflowApi.ts`. Important modules include:

- `projectsApi.ts`
- `recipesApi.ts`
- `editorApi.ts`
- `renderApi.ts`
- `dubbingApi.ts`
- `dubbingPrecisionApi.ts`
- `subtitleApi.ts`
- `sequenceContinuityApi.ts`
- `musicVideoApi.ts`
- `musicVideoReviewApi.ts`
- `performanceLipSyncApi.ts`
- `stage8WorkspaceApi.ts`
- `stage8MediaApi.ts`

This is positive: the active frontend is not fundamentally bound to the old VideoClaw workflow API. Recovery should build on these UV-owned seams rather than restore vendor routing.

## Projects / recipes path

```text
ProjectsPage
   |
   +--> recipesApi.listUVRecipes
   |       -> recipe registry API
   |
   +--> projectsApi.listUVProjects
   |       -> GET /api/uv/projects
   |
   +--> projectsApi.createUVProject
   |       -> POST /api/uv/projects
   |       -> Project Store
   |
   +--> importUVProjectArchive
           -> POST /api/uv/projects/import
           -> validated archive import -> Project Store
```

Project page:

```text
getUVProject
  -> GET /api/uv/projects/{project_id}

getProjectExecutionPlan
  -> GET /api/uv/projects/{project_id}/execution-plan
  -> RecipeExecutionPlan
  -> capability readiness projection for selected Stage 8 modes
```

Problem: the entry screen selects recipes without product readiness, then the project page uses `execution-plan` only as an informational block rather than the owner of relevant next actions.

## Targeted edit path

Frontend owner:

- `ProjectEditor.tsx`
- `RangeTimeline.tsx`
- `ReplacementWorkflowPanel.tsx`
- `EditorRenderPanel.tsx`
- `editorApi.ts`
- `renderApi.ts`

Flow:

```text
upload video
 -> POST /api/uv/projects/{id}/sources
 -> project source registration / probe

load editor
 -> GET /api/uv/projects/{id}/editor/state
 -> project edit extensions + MLT projection summary

select range + describe change
 -> POST /api/uv/projects/{id}/editor/commands
    command=select_range
 -> UV editor command
 -> exact ProjectMediaRange
 -> RangeContinuityBrief persisted in project state

approve replacement plan
 -> PUT /replacement-plans/{edit_id}
 -> ReplacementPlan persisted

prepare candidate
 -> replacement candidate endpoint / capability execution
 -> project artifact + candidate state

review candidate
 -> POST /replacement-reviews
 -> review state

accept review
 -> POST /replacement-reviews/{review_id}/accept
 -> accepted non-destructive edit state

render
 -> bounded render capability
 -> FFmpeg/MLT-backed output artifact
```

Assessment:

- mechanical/backend chain is real;
- project paths are controlled rather than arbitrary host paths;
- durable Brief/Plan/Candidate/Review state is useful;
- React currently knows too much of the prerequisite sequence;
- Product Orchestrator should project the user-level actions while keeping this domain state underneath.

## MLT role

`uv_studio/editor/mlt_adapter.py` projects canonical UV edit state into MLT timeline form. Current UI timeline interaction remains UV-owned React code.

Present ownership is therefore approximately:

```text
React RangeTimeline = interactive selection/editor surface
UV Project Store    = canonical edit truth
MLT adapter         = timeline projection / engine seam
FFmpeg/MLT          = media execution/render work
```

This is not inherently wrong, but it is not the strong “reuse a mature editor” interpretation originally investigated by D-033. Before expanding generic editing features, ownership must be explicitly re-decided.

## Dubbing path

Frontend owners:

- dubbing panels
- `dubbingApi.ts`
- `dubbingPrecisionApi.ts`
- `subtitleApi.ts`

Core flow:

```text
project source
 -> speech.transcribe capability
 -> ASR draft

accept transcript
 -> editor command
 -> durable dubbing transcript

translation
 -> editor command / dubbing state

prepared speech
 -> upload/record/TTS capability
 -> prepared audio + speech take

review
 -> dubbing review state

accept
 -> accepted dubbing state

render
 -> video.render_dubbing capability
 -> local media adapter
 -> artifact

precision/alignment/subtitle export
 -> separate precision/alignment/WebVTT APIs
```

Assessment:

- backend domain is substantial and real;
- ASR/TTS/alignment can require optional runtime setup;
- multiple separate panels expose the internal lifecycle;
- panels are currently mounted for every recipe, not only dubbing-oriented work;
- orchestrator should project setup requirements and the next decision/action.

## Sequence continuity path

Frontend owner:

- `SequenceContinuityPanel.tsx`
- `sequenceContinuityApi.ts`

Current HTTP contract:

```text
GET  /api/uv/projects/{id}/sequence/state
POST /api/uv/projects/{id}/sequence/commands
GET  /api/uv/projects/{id}/sequence/{sequence_id}/takes/{take_id}/context
```

Commands include:

- create sequence;
- upsert shot plan;
- register take;
- review take;
- accept take;
- re-anchor sequence.

Assessment:

This is a meaningful optional production policy. The architectural defect is presentation: it is mounted globally instead of only when continuity is relevant or requested.

## Music Video path

Frontend owners:

- `MusicVideoPanel.tsx`
- `MusicAssemblyPanel.tsx`
- `MusicVideoReviewPanel.tsx`
- `musicVideoApi.ts`
- `musicVideoReviewApi.ts`

Core contracts:

```text
song upload
 -> project audio source

Music Map
 GET  /music-map
 POST /music-map/commands
 -> sections / timing markers / lyric phrases / excerpt

Music Direction
 GET  /music-direction
 POST /music-direction/commands
 -> shot plans / transitions / sync markers

Music Assembly
 GET  /music-assembly
 POST /music-assembly/commands
 -> source bindings to shot plan

Rhythm audit
 GET /music-direction/rhythm-audit

Render
 POST /capabilities/video.render_music_video/execute
 -> local_free_first
 -> artifact

Review
 -> dedicated music-video review API/state
```

Assessment:

The backend already contains a strong provider-neutral production model. The UI problem is inversion of responsibility: users manually author many low-level timestamps/sections/markers/shot bindings that an analysis/orchestration layer should propose first.

The Product Orchestrator should not delete Music Map/Direction. It should turn them into proposed/editable durable plans.

## Photo -> Video path

Frontend owner:

- `Stage8MediaPanel.tsx`
- `stage8MediaApi.ts`

Flow:

```text
image upload -> /sources/image
audio upload -> /sources/audio
order + duration
 -> POST /capabilities/video.compose_photos/execute
    selection_policy=local_free_first
 -> local FFmpeg adapter
 -> video artifact
```

Assessment: clean reference flow.

## Visualizer path

```text
audio upload -> /sources/audio
optional artwork -> /sources/image
 -> POST /capabilities/audio.visualize/execute
    selection_policy=local_free_first
 -> local FFmpeg adapter
 -> video artifact
```

Assessment: clean reference flow.

## Story / Commercial / Free path

Frontend owner:

- `Stage8CompositionPanel.tsx`
- `stage8WorkspaceApi.ts`

Current dedicated behavior:

- persist brief;
- persist optional script/text;
- register/select image/video/audio project sources;
- preserve typed workspace state.

Assessment:

This is good pre-production state, but it is not itself a complete story/commercial generation/assembly workflow. Product cards must not imply more than the available next actions.

## Performance lip-sync path

Frontend owner:

- `PerformanceLipSyncPanel.tsx`
- `performanceLipSyncApi.ts`

Backend owner:

- semantic `video.digital_human` capability;
- verified MuseTalk adapter/profile when the exact optional runtime/model/CUDA boundary passes.

Assessment:

This is a real setup-gated capability. Readiness must be surfaced before the user enters the task, rather than discovered after attempting execution.

## Capability execution architecture

The capability layer is one of the strongest parts of the repository:

```text
CapabilityDefinition
       |
CapabilityOffer(s)
       |
SelectionPolicy
       |
Authorization (D-017)
       |
Execution
       |
Adapter
       |
Result + provenance + artifact
```

Important properties to preserve:

- semantic capability IDs rather than provider IDs in project semantics;
- local/free-first selection is fail-closed;
- remote/paid execution has explicit authorization boundaries;
- adapters are peers rather than requiring one universal runtime;
- project-scoped inputs prevent raw arbitrary host-path execution;
- provenance and artifact publication are explicit.

The Product Orchestrator should consume capability availability, not replace the registry/selection/authorization layer.

## Project Store / domain state architecture

`uv_studio/projects` contains more than a basic file store. It owns typed/versioned domain extensions for:

- continuity briefs;
- edit state;
- dubbing transcripts/translation/review/alignment;
- music analysis/map/direction/assembly/review;
- replacement plans/candidates/reviews;
- sequence continuity;
- Stage 8 workspaces;
- archives/migrations/integrity.

This is why a rewrite is unnecessary. The recovery target is to add a projection/orchestration layer **over** this durable state.

## Main architectural gap

Today the product effectively does:

```text
React component
 -> inspect several domain states
 -> infer prerequisites
 -> decide which control is disabled
 -> invoke one of many specialized APIs
 -> refresh selected state
 -> repeat
```

Target:

```text
Product Orchestrator
 -> inspect canonical project/domain state
 -> inspect capability/runtime availability
 -> project readiness/prerequisites/next actions

React
 -> render projection
 -> collect bounded action input
 -> execute semantic action
 -> refresh projection
```

The specialized domain APIs can remain underneath during migration. The orchestrator is initially a facade/projection, not a big-bang replacement.

## Migration rule

Do not consolidate APIs merely for aesthetic uniformity. A domain-specific API remains acceptable when it owns a coherent invariant. Consolidate **product action semantics**, not necessarily every HTTP route.

Examples:

- Music Map commands can remain a dedicated domain API.
- Dubbing review can remain a dedicated domain API.
- Replacement Review can remain dedicated.
- Product Orchestrator maps those into stable user-facing actions such as `analyze_song`, `review_dub`, `prepare_replacement`, `export_result`.

This avoids replacing several tested bounded modules with one giant controller.

## Immediate Product Orchestrator seam

Recommended first endpoint family in the next slice:

```text
GET /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

The first slice may implement only the read projection plus one representative action. Action execution can delegate to existing domain command/capability functions.

The read model must contain:

- truthful readiness;
- structured prerequisites;
- relevant workspaces/features;
- next actions;
- active jobs;
- recent result artifacts;
- diagnostics separated from ordinary user copy.

No new canonical workflow state is introduced.
