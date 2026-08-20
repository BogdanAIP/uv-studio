# Legacy VideoClaw Surface Inventory

## Purpose

Stage 3.5 intentionally stopped mounting the complete VideoClaw FastAPI application. This inventory distinguishes current UV Studio product authority from donor/compatibility code before any deletion or reintroduction of legacy routes.

## Classification rules

- `current_product` — reachable from current UV-owned product flow and backed by mounted UV-owned routes;
- `compatibility_only` — retained for an explicit adapter/migration/test boundary but not a user-facing execution path;
- `donor_unreachable` — historical frontend/donor code not reachable from current product navigation;
- `stale_contract` — current metadata/client code still implies a route is executable even though it is not mounted;
- `unknown` — requires call-site evidence before classification.

## Confirmed legacy route families

| Route family | Current server mounted? | Known role | Classification | Action |
|---|---:|---|---|---|
| `/api/pipelines/standard/tasks` | No | historical narrated/standard VideoClaw production pipeline | `stale_contract` in recipe execution metadata; donor compatibility elsewhere | recipe metadata fails closed now; do not remount |
| `/api/pipelines/action_transfer/tasks` | No | historical action-transfer pipeline | `stale_contract` in recipe execution metadata; donor compatibility elsewhere | recipe metadata fails closed now; later bind current capability workflow or remain unavailable |
| `/api/pipelines/digital_human/tasks` | No | historical product-promo digital-human pipeline | compatibility/donor surface; current recipe already does not claim full compatibility | keep isolated pending call-site audit |
| `/api/tasks` | No | historical task polling/control | donor/compatibility client surface | audit callers; retire if unreachable |
| `/api/sessions` | No | historical VideoClaw session state | donor/compatibility client surface | audit callers; Project Store remains canonical |
| `/api/models` | No | historical provider/model catalog | donor/compatibility client surface | audit callers; Capability Registry/runtime config remain current authority |
| `/api/upload_media` | No | historical upload path | donor/compatibility client surface | audit callers; current project media registration is authority |
| `/api/sandbox/*` | No | historical sandbox task execution | donor/compatibility client surface | do not remount; audit and retire unreachable callers |

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

A stale caller is **not** justification to remount the legacy backend. Reintroduction requires an explicit UV-owned adapter that preserves D-017 authorization, secret safety, project path boundaries and provider-neutral canonical state.

## Retirement procedure

For each legacy frontend/client file:

1. prove whether it is reachable from current product navigation/import graph;
2. identify tests or compatibility adapters that still import it;
3. classify as current/compatibility/donor/dead;
4. replace current callers with UV-owned semantics where needed;
5. delete only after tests prove no supported path depends on it.

This slice records the route-family truth. File-by-file retirement can proceed in bounded follow-up commits after dependency evidence is available.
