# UV Studio Product Truth Matrix

## Purpose

This document is the auditable source of truth for what UV Studio currently promises and what the `main` application can actually execute. A product mode is not `working` because its domain objects or tests exist; it is working only when a normal user can reach a current mounted execution path and obtain the expected state/artifact.

Status values:

- `working` — current UI -> current mounted API -> current implementation -> result works without hidden setup;
- `working_with_setup` — end-to-end path exists, but an explicit optional runtime/configuration prerequisite must be satisfied first;
- `partial` — useful current pieces exist but the advertised product journey is incomplete;
- `misleading` — product metadata/UI implies executable readiness that is not true on the current UV-owned server;
- `dead` — historical/donor surface with no supported current product path.

## Server boundary audited

`uv_studio/server.py` mounts UV-owned routers for configuration, capabilities/execution, MCP/Qwen pack, recipes/execution metadata, projects/media, editor commands, dubbing state/review, replacement workflow, sequence continuity, music map/direction/assembly/review, Stage 8 workspaces and artifact/media access.

It deliberately does **not** mount the complete legacy VideoClaw route table. In particular, `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/upload_media` and `/api/sandbox/*` are not current product routes.

## Recipe matrix

| Recipe | Product promise | Current user surface | Current execution owner | Required setup | Result | Status | Recovery action |
|---|---|---|---|---|---|---|---|
| `general_video` | Create a normal video from a brief without mandatory narration/song | Create-project recipe + generic project workspace | Recipe metadata requires `video.generate` + `timeline.assemble`; execution plan already says no true path | Generation capabilities would be required | No coherent brief -> plan -> assets -> assembly path | `partial` | Keep visibly gated until Product Orchestrator defines a real UV-owned journey |
| `narrated_video` | Topic/script -> narration -> visuals -> assembled video | Create-project recipe; no dedicated complete current workspace | **Historical execution plan advertises `/api/pipelines/standard/tasks`, which is not mounted** | text/image/video/TTS provider/runtime choices | Advertised launch target is unreachable | `misleading` | Remove false `AVAILABLE`/legacy launch target; rebuild through current semantic capabilities |
| `music_video` | Song-driven 20–30 s professional clip | Music panels: map/direction/assembly/review | UV-owned music routers/state + render capabilities | source audio; generation optional | Large parts are real, but default flow exposes internal Music Map/state authoring and lacks a simple intent-first path | `partial` | Product Orchestrator should propose analysis/map/direction before advanced manual editing |
| `action_transfer` | Transfer motion from source video to target image/person | Recipe visible; no complete current task workspace | **Historical execution plan advertises `/api/pipelines/action_transfer/tasks`, which is not mounted**; semantic capability exists separately | executable `video.action_transfer` offer/provider | No current recipe-level path from creation to result | `misleading` | Remove false `AVAILABLE`; later bind a current authorized capability workflow or gate unavailable |
| `digital_human` | Portrait + speech -> talking character video | Recipe visible; generic project/editor surfaces | Execution plan is already `PARTIAL`; provider-neutral capability exists | suitable `video.digital_human` offer/runtime | No baseline one-click current path | `partial` | Keep setup/availability explicit; do not route through legacy promo pipeline |
| `story_video` | Story brief/script/materials -> coherent video | `Stage8CompositionPanel` + generic editor/other panels | Typed Stage 8 workspace + existing media primitives | generation optional | Current dedicated surface mainly stores brief/script/source bindings; full story production path not orchestrated | `partial` | Add story-level orchestration only after core scenarios are coherent |
| `commercial_product` | Product brief/materials -> ad/product video | `Stage8CompositionPanel` + generic editor/other panels | Typed Stage 8 workspace + existing media primitives | generation optional | Current dedicated surface is preparation/state, not complete ad workflow | `partial` | Add orchestrated product path; preserve source/product constraints |
| `photo_to_video` | Ordered photos + optional audio -> video | `Stage8MediaPanel` | `video.compose_photos` -> local FFmpeg adapter | none beyond bundled/system media toolchain in current dev app | Video artifact | `working` | Use as UX reference: short intent -> inputs -> one clear action -> result |
| `visualizer` | Audio + optional artwork -> visualizer video | `Stage8MediaPanel` | `audio.visualize` -> local FFmpeg adapter | none beyond media toolchain | Video artifact | `working` | Use as UX reference |
| `performance_lip_sync` | Portrait + speech -> lip-sync performance | `PerformanceLipSyncPanel` | verified MuseTalk adapter/profile behind capability boundary | exact optional MuseTalk/CUDA/model runtime | Result works only when strict runtime preflight is satisfied | `working_with_setup` | Surface setup prerequisite before user enters the workflow |
| `free_project` | Flexible project using only needed tools | Stage 8 preparation + generic editor + many global panels | Multiple independent UV-owned feature APIs | depends on chosen action | Useful primitives, but no product-level next-action owner | `partial` | Make orchestrator/tool palette explicit; stop loading unrelated workflows as implicit path |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | No complete brief -> visual plan -> assets/generation -> assembly -> export journey | `partial` | missing product orchestration and executable baseline |
| B. Narrated video | Historical VideoClaw standard pipeline metadata remains, but route is not mounted | `misleading` | stale execution target + no replacement UV-owned journey |
| C. Music-video excerpt | Domain state, assembly and review exist; default authoring is backend-schema-heavy | `partial` | intent-first analysis/direction orchestration |
| D. Existing-video dubbing | Strong ASR/translation/prepared-speech/review/render domain path; local ASR/runtime can require external setup and UI exposes many internal gates | `working_with_setup` / UX-partial | explicit first-run prerequisite projection + simplified next actions |
| E. Targeted existing-video edit | Mechanical range edit/replacement/review/render path is real | `working` / UX-partial | simplify hidden state machine into next actions; generation path only when capability available |

## Confirmed false product contracts

### `narrated_video`

Current `main` unit tests explicitly require:

- `ExecutionCompatibility.AVAILABLE`;
- target `standard`;
- `launch_path == /api/pipelines/standard/tasks`.

The current UV-owned FastAPI server does not mount that route. This is a confirmed product-truth defect, not a speculative UX concern.

### `action_transfer`

Current `main` unit tests explicitly require `AVAILABLE` and a native `action_transfer` compatibility target. The target is `/api/pipelines/action_transfer/tasks`, also not mounted by the current UV-owned server.

These two contracts must be changed to fail closed until a current executable workflow is registered.

## Legacy frontend/API inventory

The repository still contains donor/compatibility code that references historical VideoClaw endpoints. Known classes include:

- `/api/pipelines/standard/tasks`;
- `/api/pipelines/action_transfer/tasks`;
- `/api/pipelines/digital_human/tasks`;
- `/api/tasks`;
- `/api/sessions`;
- `/api/models`;
- `/api/upload_media`;
- `/api/sandbox/tasks`.

Recovery rule: classify each caller as `reachable product`, `compatibility-only`, `test-only`, or `dead` before removal. No route is remounted merely to make stale callers green.

## Product Orchestrator contract — initial proposal

The next product-level projection should be read-only over canonical state plus runtime availability:

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
- action_id                  # stable semantic product action
- title
- explanation
- enabled
- blocked_by[]               # prerequisite IDs
- input_schema
- execution_class            # deterministic_local | local_optional | remote_optional | state_only
- authorization_class        # none | explicit_remote | explicit_paid
- expected_result_kind
```

The frontend should use this projection to answer “what can I do now?” instead of duplicating domain prerequisite logic in React.

## Contract tests required in this slice

1. Every `RecipeExecutionPlan` with a non-null executable target must reference a route mounted by the current UV-owned FastAPI application.
2. `AVAILABLE` must imply a reachable target or an explicitly registered current product workflow; a historical donor path is insufficient.
3. `narrated_video` and `action_transfer` must fail closed until replacement UV-owned workflows exist.
4. Existing `general_video`, `digital_human`, Stage 8 and music truth statuses must remain explicit and provider-neutral.

## Cold-start evidence status

No permanent scenario is considered release-complete from this matrix alone. A later cold-start suite must begin with clean project/runtime state and use only user-visible actions, without pre-seeding internal domain objects through test helpers or direct HTTP APIs.
