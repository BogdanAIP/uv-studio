# Legacy VideoClaw Surface Inventory

## Purpose

Stage 3.5 intentionally stopped mounting the complete VideoClaw FastAPI application. This inventory distinguishes current UV Studio product authority from donor/compatibility code before any deletion or reintroduction of legacy routes.

## Classification rules

- `current_product` — reachable from current UV-owned product flow and backed by mounted UV-owned routes;
- `compatibility_only` — retained for an explicit adapter/migration/test boundary but not a user-facing execution path;
- `donor_unreachable` — historical frontend/donor code not reachable from current product navigation;
- `stale_contract` — current metadata/client code still implies a route is executable even though it is not mounted;
- `unknown` — requires call-site evidence before classification.

## Current frontend finding

The live UV-owned `frontend/lib` on the Stage 8 `main` baseline contains current modules such as `projectsApi.ts`, `editorApi.ts`, `dubbingApi.ts`, `musicVideoApi.ts`, `stage8MediaApi.ts` and capability/job/render clients. It does **not** contain `workflowApi.ts`; repository-tree checks also found no live `frontend` files named `HomePage` or `WorkflowPanel`.

The historical `workflowApi.ts` does exist at `vendor/videoclaw-app/frontend/lib/workflowApi.ts` inside the pinned donor tree. That vendored frontend is provenance/compatibility material, not current UV-owned product authority.

Therefore the confirmed active stale contract in this slice is **recipe execution/readiness metadata plus tests**, not an imported live React `workflowApi` client. The vendor route families below remain useful historical inventory and must stay isolated unless a reviewed UV-owned adapter explicitly reuses them.

## Confirmed legacy route families

| Route family | Current server mounted? | Current product evidence | Classification | Action |
|---|---:|---|---|---|
| `/api/pipelines/standard/tasks` | No | Stage 8 `RecipeExecutionPlan` and tests falsely advertised it for `narrated_video` | `stale_contract` | recovery branch fails closed; do not remount |
| `/api/pipelines/action_transfer/tasks` | No | Stage 8 `RecipeExecutionPlan` and tests falsely advertised it for `action_transfer` | `stale_contract` | recovery branch fails closed; later bind a current capability workflow or remain unavailable |
| `/api/pipelines/digital_human/tasks` | No | historical vendor product-promo route; current recipe already has no executable target | `donor_unreachable` / compatibility research | keep isolated pending explicit reuse decision |
| `/api/tasks` | No | present in donor-era workflow model, not current UV frontend authority | `donor_unreachable` | no current replacement needed merely for donor parity |
| `/api/sessions` | No | donor-era session state; Project Store is current canonical identity/state | `donor_unreachable` | do not restore as canonical state |
| `/api/models` | No | donor-era provider/model catalog; current capability/runtime layer owns readiness | `donor_unreachable` | do not restore as product authority |
| `/api/upload_media` | No | donor-era upload path; current project media APIs own registered inputs | `donor_unreachable` | do not restore |
| `/api/sandbox/*` | No | donor-era sandbox execution intentionally excluded by Stage 3.5 | `donor_unreachable` / security boundary | do not remount |

## Current authority replacements

| Concern | Current UV Studio authority |
|---|---|
| project identity/persistence | Project Store + `/api/uv/projects*` |
| recipe definitions | Recipe Registry + UV recipe API |
| execution availability | capability offers/selection/authorization plus current UV-owned workflow routes |
| media inputs | project-owned source registration/media APIs |
| deterministic edit/render | UV editor commands + bounded FFmpeg/MLT adapters |
| dubbing | UV dubbing/editor/prepared-audio/review/render state and capability execution |
| music video | UV Music Map/Direction/Assembly/Review APIs |
| provider/runtime choices | Capability Registry + runtime configuration; never legacy `/api/models` as canonical truth |

## Safety rule

A stale contract or donor caller is **not** justification to remount the legacy backend. Reintroduction requires an explicit UV-owned adapter that preserves D-017 authorization, secret safety, project path boundaries and provider-neutral canonical state.

## Retirement procedure

For any legacy file considered for deletion or reuse:

1. prove whether it belongs to live `frontend/`, `uv_studio/`, tests, or only `vendor/`;
2. prove whether a current product import/call site reaches it;
3. classify as current/compatibility/donor/dead;
4. replace current callers with UV-owned semantics where needed;
5. delete only after tests prove no supported path depends on it.

The vendor tree itself remains pinned upstream provenance and is not being opportunistically edited or deleted in this recovery slice.
