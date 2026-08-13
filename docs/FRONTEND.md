# UV Studio Frontend

Top-level `frontend/` is UV Studio-owned product source. It began as a reproducible derived copy of the pinned VideoClaw frontend, whose untouched comparison snapshot remains under `vendor/videoclaw-app/frontend/` with provenance/attribution metadata.

## Supported product surfaces

Current canonical UV-owned user paths are:

- `/projects` — project list/create/import;
- `/projects/[projectId]` — canonical project/editor workspace;
- targeted existing-video range editing through the Stage 4C UI;
- Stage 5 dubbing/translation/precision/subtitle panels mounted inside the canonical project page.

These surfaces use `/api/uv/*` product APIs and canonical UV project IDs.

## Legacy root workspace

The historical VideoClaw `WorkflowPanel` and related source still exist in the derived frontend, but D-025 deliberately stopped mounting the complete legacy VideoClaw backend route table. Therefore `/` must not be described as a fully supported working production workflow merely because the UI source is still present.

The post-Stage-5 hardening slice must either:

1. make the root route a UV-owned landing/redirect into supported project surfaces; or
2. explicitly isolate a separate compatibility runtime with its own security/authorization contract.

It must not silently remount the old provider/pipeline/sandbox backend and weaken D-025.

## Identity rule

UV `project_id` and legacy VideoClaw session IDs are different identifiers. Do not substitute one for the other.

## Source provenance

Initial donor:

- `HITsz-TMG/VideoClaw`
- commit `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`
- MIT

`frontend/.uv-derived.json` records the source baseline and `frontend/UPSTREAM_LICENSE` preserves the license. `tools/promote_frontend.py --force` is destructive and must not be used during ordinary development.

Stage 4C also selectively adapts MIT OpenCut Classic timeline interaction ideas while keeping UV Project Store/Command boundaries authoritative.

## Testing state

Permanent CI currently runs frontend lint, high-severity dependency audit and production build on Windows/Ubuntu. Browser E2E and frontend unit/accessibility coverage remain incomplete; browser E2E for the existing-video and dubbing user outcomes is the next Stage 5 quality gate.
