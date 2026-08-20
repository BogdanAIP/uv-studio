# UV Studio Product Truth Matrix

## Purpose

This document is the auditable source of truth for what UV Studio promises and what the Stage 8 `main` application can actually execute. A product mode is not `working` because its domain objects or tests exist; it is working only when a normal user can reach a current mounted execution path and obtain the expected state/artifact.

The active recovery branch may already repair a baseline defect described here. Such rows distinguish **baseline truth** from **recovery behavior** so history is not rewritten.

Status values:

- `working` — current UI -> current mounted API -> current implementation -> result works without hidden setup;
- `working_with_setup` — end-to-end path exists, but an explicit optional runtime/configuration prerequisite must be satisfied first;
- `partial` — useful current pieces exist but the advertised product journey is incomplete;
- `misleading` — product metadata/UI implies executable readiness that is not true on the current UV-owned server;
- `donor_only` — historical/vendor surface outside current UV-owned product authority.

## Server boundary audited

`uv_studio/server.py` mounts UV-owned routers for configuration, capabilities/execution, MCP/Qwen pack, recipes/execution metadata, projects/media, editor commands, dubbing state/review, replacement workflow, sequence continuity, music map/direction/assembly/review, Stage 8 workspaces and artifact/media access.

It deliberately does **not** mount the complete legacy VideoClaw route table. In particular, `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/upload_media` and `/api/sandbox/*` are not current product routes.

## Project-page composition audit

The Stage 8 project page does not currently isolate workflows by recipe. It always mounts:

1. `ProjectEditor`;
2. `SequenceContinuityPanel`;
3. `DubbingWorkflowPanel`;
4. `DubbingPrecisionPanel`;
5. `DubbingSubtitleExportPanel`;
6. execution-plan/readiness diagnostics;
7. project archive/recovery controls.

Recipe-specific panels are then added on top:

- `story_video`, `commercial_product`, `free_project` -> `Stage8CompositionPanel`;
- `music_video` -> `MusicVideoPanel` + `MusicAssemblyPanel` + `MusicVideoReviewPanel`;
- `photo_to_video`, `visualizer` -> `Stage8MediaPanel`;
- `performance_lip_sync` -> `PerformanceLipSyncPanel`.

This means a photo visualizer, story project or free project still receives targeted range editing, sequence continuity and three dubbing panels. This is a confirmed **cross-workflow leakage** defect. It directly violates the Stage 2 user-exit requirement that selecting a task presents only the relevant workflow.

Recovery consequence: the Product Orchestrator must decide relevant next actions/workspaces. Recipe selection must not merely append more panels to a universal page.

## Core frontend -> backend ownership map

| User-facing area | Frontend owner | Current API/domain owner | Truth assessment |
|---|---|---|---|
| Project create/open/archive | project pages + `projectsApi` | Project Store / projects API | real canonical foundation |
| Generic source import | `ProjectEditor` / `editorApi` | project media + editor state | real |
| Range selection / change brief | `ProjectEditor` | `/editor/commands` + continuity brief | real, but user must understand hidden sequence |
| Replacement plan/candidate/review | `ReplacementWorkflowPanel` | replacement plan/preparation/review APIs + capabilities | real controlled workflow; too much orchestration exposed in UI |
| Final edit render | `EditorRenderPanel` | accepted edit state + bounded render capability | real |
| Sequence continuity | `SequenceContinuityPanel` | sequence continuity/review assist APIs | real optional policy, but currently displayed globally |
| Dubbing transcription/translation/prepared speech | dubbing panels | capability execution + dubbing/editor/prepared-audio APIs | substantial real workflow; setup and state prerequisites are fragmented |
| Dubbing precision/subtitles | precision/export panels | alignment/review/WebVTT APIs | real specialist features, currently displayed globally |
| Music map/direction | `MusicVideoPanel` | Music Map/Direction APIs | real domain state; UI exposes internal authoring burden |
| Music assembly/review | assembly/review panels | Music Assembly + render + Rhythm/Review APIs | real |
| Photo -> Video | `Stage8MediaPanel` | `video.compose_photos` local capability | real clean intent-to-result reference |
| Visualizer | `Stage8MediaPanel` | `audio.visualize` local capability | real clean intent-to-result reference |
| Story/Commercial preparation | `Stage8CompositionPanel` | typed Stage 8 workspace | real preparation state, not full production journey |
| Performance lip-sync | `PerformanceLipSyncPanel` | verified optional `video.digital_human`/MuseTalk path | real only with explicit runtime setup |
| Recipe readiness block | project page + `/execution-plan` | `RecipeExecutionPlan` plus Stage 8 capability projection | overloaded semantics; not yet a Product Orchestrator |

## Recipe matrix

| Recipe | Product promise | Current user surface | Current execution owner | Required setup | Result | Baseline status | Recovery action |
|---|---|---|---|---|---|---|---|
| `general_video` | Create a normal video from a brief without mandatory narration/song | Create-project recipe + generic project workspace | metadata requires `video.generate` + `timeline.assemble`; execution plan says no true path | generation capabilities | no coherent brief -> plan -> assets -> assembly path | `partial` | visibly gate until Product Orchestrator defines a real UV-owned journey |
| `narrated_video` | Topic/script -> narration -> visuals -> assembled video | create-project recipe; no dedicated complete current workspace | baseline execution plan pointed to unmounted `/api/pipelines/standard/tasks` | text/image/video/TTS choices | baseline advertised target unreachable | `misleading` | **recovery branch now fails closed**; rebuild through current semantic capabilities |
| `music_video` | Song-driven 20–30 s professional clip | music map/direction/assembly/review panels plus globally leaked generic workflows | UV-owned music routers/state + render capabilities | source audio; generation optional | large parts real; default path exposes internal Music Map/state authoring | `partial` | orchestrator should propose analysis/map/direction before advanced manual editing |
| `action_transfer` | Transfer motion from source video to target image/person | recipe visible; no complete current task workspace | baseline execution plan pointed to unmounted `/api/pipelines/action_transfer/tasks`; semantic capability exists separately | executable `video.action_transfer` offer/provider | no current recipe-level path to result | `misleading` | **recovery branch now fails closed**; later bind current authorized capability workflow or stay unavailable |
| `digital_human` | Portrait + speech -> talking character video | recipe visible + generic leaked workflows | execution plan already `PARTIAL`; provider-neutral capability exists | suitable `video.digital_human` offer/runtime | no baseline one-click current path | `partial` | explicit setup/readiness; no legacy promo fallback |
| `story_video` | Story brief/script/materials -> coherent video | Stage 8 preparation plus generic edit/continuity/dubbing panels | typed Stage 8 workspace + media primitives | generation optional | dedicated surface mainly stores brief/script/source bindings | `partial` | orchestrated story path after core flows; hide unrelated panels |
| `commercial_product` | Product brief/materials -> ad/product video | Stage 8 preparation plus generic edit/continuity/dubbing panels | typed Stage 8 workspace + media primitives | generation optional | preparation state, not complete ad workflow | `partial` | orchestrated product path; preserve product constraints |
| `photo_to_video` | Ordered photos + optional audio -> video | Stage8MediaPanel plus unrelated globally mounted panels | `video.compose_photos` -> local FFmpeg | media toolchain | video artifact | `working` with page-level UX leakage | use as intent-to-result reference and isolate workspace |
| `visualizer` | Audio + optional artwork -> visualizer video | Stage8MediaPanel plus unrelated globally mounted panels | `audio.visualize` -> local FFmpeg | media toolchain | video artifact | `working` with page-level UX leakage | use as intent-to-result reference and isolate workspace |
| `performance_lip_sync` | Portrait + speech -> lip-sync performance | PerformanceLipSyncPanel plus generic leaked workflows | verified MuseTalk adapter/profile | exact optional MuseTalk/CUDA/model runtime | video artifact when preflight passes | `working_with_setup` | show setup prerequisite before entering workflow |
| `free_project` | Flexible project using only needed tools | Stage 8 preparation + all generic panels | multiple independent APIs | depends on action | useful primitives but no product-level next-action owner | `partial` | orchestrator/tool palette; user chooses tools rather than seeing all specialist workflows |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | No complete brief -> visual plan -> assets/generation -> assembly -> export journey | `partial` | product orchestration + executable baseline |
| B. Narrated video | Stage 8 baseline advertised an unmounted standard pipeline; recovery now fails closed | baseline `misleading`, recovery `unavailable` | current UV-owned narrated journey |
| C. Music-video excerpt | Domain state, assembly and review exist; default authoring is backend-schema-heavy | `partial` | intent-first analysis/direction orchestration |
| D. Existing-video dubbing | Strong ASR/translation/prepared-speech/review/render path; runtime can require setup; panels expose many internal gates | `working_with_setup` / UX-partial | prerequisite projection + simplified next actions + recipe isolation |
| E. Targeted existing-video edit | Mechanical range edit/replacement/review/render path is real | `working` / UX-partial | simplify plan/candidate/review state machine into next actions |

## Confirmed frontend orchestration burden

`ProjectEditor` is a real implementation, not a mock. It imports project media, previews video, owns playhead/zoom/range selection, captures a change request, calls the semantic `selectProjectRange` command, then mounts separate replacement and render panels.

However the primary action is disabled until three pieces of implicit state exist simultaneously:

1. an active source;
2. a valid timeline selection;
3. non-empty change text.

After that, the interface exposes durable implementation vocabulary such as `Brief`, `Plan`, `Candidate`, `Review`, `Accepted` and `edit_id`. Those are valuable canonical/domain concepts, but ordinary product flow should project them as understandable next actions rather than require the user to infer the state machine.

This is the architectural reason “disabled buttons” cannot be solved by styling alone.

## Confirmed false product contracts repaired in this branch

### `narrated_video`

The Stage 8 baseline unit/API tests required:

- `ExecutionCompatibility.AVAILABLE`;
- target `standard`;
- `/api/pipelines/standard/tasks`.

The UV-owned server does not mount that route. The recovery branch changes the plan to `UNAVAILABLE`, target `None`, while preserving typed inputs and runtime capability requirements.

### `action_transfer`

The Stage 8 baseline similarly required `AVAILABLE` plus `/api/pipelines/action_transfer/tasks`. The recovery branch fails closed while preserving `video.action_transfer` readiness metadata and production policy.

### New regression invariant

Any future non-null `RecipeExecutionPlan.target` must point to a path actually present in the current FastAPI route table. A base recipe plan cannot be `AVAILABLE` without a current executable target.

## Execution-plan semantic overload

`/api/uv/projects/{project_id}/execution-plan` currently combines two concepts:

1. legacy/current recipe compatibility planning from `RecipeExecutionPlan`;
2. Stage 8 machine capability readiness projection for `photo_to_video`, `visualizer`, `performance_lip_sync`.

For those Stage 8 modes the API may set `compatibility=available` while `target=None`, because execution is through semantic capabilities rather than a native pipeline target. This behavior is intentional but demonstrates why `compatibility` is not a sufficient product-level readiness model.

The Product Orchestrator should replace this ambiguity with explicit `readiness`, `prerequisites` and `next_actions`, while preserving the lower-level execution/capability data for diagnostics.

## Legacy frontend/API inventory

Current live `frontend/lib` has already moved to UV-owned APIs. The historical `workflowApi.ts` is under `vendor/videoclaw-app/frontend/lib/`, not the active frontend. See `LEGACY_SURFACE_INVENTORY.md`.

Known donor route families remain:

- `/api/pipelines/standard/tasks`;
- `/api/pipelines/action_transfer/tasks`;
- `/api/pipelines/digital_human/tasks`;
- `/api/tasks`;
- `/api/sessions`;
- `/api/models`;
- `/api/upload_media`;
- `/api/sandbox/tasks`.

No donor route is remounted merely to satisfy historical parity.

## Product Orchestrator contract — initial proposal

The next product-level projection is read-only over canonical state plus runtime availability:

```text
ProjectWorkflowState
- schema_version
- project_id
- recipe_id
- readiness: ready | setup_required | partial | unavailable
- summary
- prerequisites[]
- next_actions[]
- active_jobs[]
- recent_artifacts[]
- diagnostics[]
```

`prerequisites[]`:

```text
- prerequisite_id
- kind: source | runtime | capability | configuration | review | decision
- title
- explanation
- satisfied
- satisfying_action_id?
```

`next_actions[]`:

```text
- action_id
- title
- explanation
- enabled
- blocked_by[]
- input_schema
- execution_class: deterministic_local | local_optional | remote_optional | state_only
- authorization_class: none | explicit_remote | explicit_paid
- expected_result_kind
```

The frontend should use this projection to answer “what can I do now?” and “why can’t I do this yet?” instead of duplicating domain prerequisite logic in React.

## Contract tests in this slice

1. Any `RecipeExecutionPlan` with a non-null executable target must reference a route mounted by the current UV-owned FastAPI application.
2. Base `AVAILABLE` compatibility may not point to a historical donor path.
3. `narrated_video` and `action_transfer` fail closed until replacement UV-owned workflows exist.
4. Their typed input/capability/policy information remains available for future orchestration.
5. Stage 8 deterministic/capability workflows preserve their current provider-neutral readiness projection.

## Cold-start evidence status

No permanent scenario is release-complete from this matrix alone. A later cold-start suite must begin with clean Project Store/runtime state and use only user-visible actions, without pre-seeding transcripts, plans, reviews, Music Maps or accepted edits through test helpers/direct HTTP APIs.
