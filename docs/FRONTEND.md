# UV Studio Frontend

**Status:** CURRENT SUPPORTING PRODUCT SURFACE  
**Product authority:** D-064 / `docs/architecture/CURRENT_ARCHITECTURE.md`

Top-level `frontend/` is tracked UV Studio-owned product source. The pinned VideoClaw frontend under `vendor/videoclaw-app/frontend/` is read-only provenance/comparison material only; it is not a supported source for reconstructing or overwriting the product frontend.

## Current product surfaces

- `/projects` — canonical project list/import and **Production Direction** selection for new Studio projects;
- `/projects/[projectId]/studio` — shared Studio Core (Media/Assets, Preview, Inspector/AI area, canonical Timeline, export);
- `/settings` — machine/provider/runtime configuration.

New projects use Production Directions and open the shared Studio surface. Direction-specific production navigation/domain panels will grow inside that shell as their domain verticals are implemented.

## Compatibility project surface

`/projects/[projectId]` remains a legacy compatibility workspace for older recipe/Product-Orchestrator projects. It mounts specialized targeted-edit/dubbing/music/Stage-era panels and must not be used as the template for new Production Direction UI.

The `/projects` list labels this path as an old compatible workflow. Compatibility may remain until caller/project migration evidence permits retirement.

Historical donor `WorkflowPanel`, pipeline, Sandbox and donor stage components are retired from top-level product source. Their absence does not retire the live compatibility project route or its still-used UV-owned domain panels.

## Identity and command rules

- `project_id` is the stable UV project identity.
- Modern product composition uses validated Studio Production Direction metadata, not recipe identity.
- durable project/timeline/domain mutations must converge on UV-owned application/domain commands;
- the frontend may keep transient interaction state but must not become a second canonical project store;
- user-significant model choice belongs in the relevant Studio AI tool, not hidden in provider settings.

## Source provenance

Initial donor: `HITsz-TMG/VideoClaw` commit `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276` (MIT). `frontend/.uv-derived.json` and `frontend/UPSTREAM_LICENSE` preserve that historical source provenance.

`python tools/verify_frontend_provenance.py` verifies the pinned donor snapshot, license and provenance record **read-only**. No supported tool or workflow copies that snapshot over top-level `frontend/`. If tracked frontend source is missing or damaged, restore it from the current Git checkout or use a fresh checkout.

D-033 also authorizes selective MIT OpenCut Classic interaction/UI reuse while keeping UV Project Store/commands authoritative.

## Model listing

`/settings` obtains model choices through `frontend/lib/modelRegistry.ts` and the focused `frontend/lib/modelsApi.ts` client. The existing `/api/models` query contract remains unchanged; the settings surface no longer depends on the historical broad donor workflow client.

## Testing

Permanent CI verifies read-only frontend provenance, runs donor-retirement caller guards, lint, high-severity dependency audit, production build and real browser outcome suites on Windows/Ubuntu. Class-C evidence additionally verifies clean Production Direction discovery/creation plus shared Studio reopen/export; richer direction journeys must extend that evidence as they are implemented.
