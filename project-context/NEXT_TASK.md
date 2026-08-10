# Next Task

**Primary target:** establish an UV Studio-owned frontend derived from the pinned VideoClaw frontend baseline, then add the first Projects screen against `/api/uv/projects`.

## Why this comes next

The current user-facing Next.js application still lives under `vendor/videoclaw-app/frontend`. UV Studio will need substantial product-specific navigation, terminology and workflow changes. Repeatedly patching the vendored snapshot would blur upstream provenance and make future upstream comparisons difficult.

Therefore the next slice should promote the pinned frontend baseline into an explicitly UV Studio-owned derived frontend while preserving MIT attribution.

## Do first

1. Create a reproducible one-time/front-end promotion script or documented copy manifest from the pinned `vendor/videoclaw-app/frontend` baseline into a top-level UV Studio frontend directory.
2. Preserve upstream MIT attribution/provenance for the derived frontend.
3. Update `tools/uv_dev.py`, Windows launch scripts and CI so the product frontend builds/runs from the UV Studio-owned directory.
4. Prove build parity before product changes.
5. Add a minimal Projects entry screen that:
   - lists projects from `GET /api/uv/projects`;
   - creates a project with `POST /api/uv/projects`;
   - opens/selects a project shell by stable project ID.
6. Keep existing upstream screens reachable during migration instead of rewriting all UI at once.
7. Add frontend tests where practical and at minimum keep production build green on Windows/Linux CI.

## Expected areas

Likely:

- `frontend/` — UV Studio-owned Next.js application derived from pinned baseline;
- `tools/promote_frontend.py` or equivalent provenance/manifest tooling;
- frontend provenance/license notice;
- updates to `tools/uv_dev.py`;
- updates to `scripts/setup-dev.ps1` / `scripts/run-frontend.ps1`;
- Projects page/components/client helpers;
- `docs/FRONTEND.md`.

## Acceptance criteria

- UV Studio frontend no longer runs directly from `vendor/videoclaw-app/frontend`;
- the promoted baseline can be reproduced from the current pinned upstream snapshot;
- upstream attribution is preserved;
- existing baseline UI still production-builds before/after promotion;
- Projects screen successfully lists and creates canonical UV Studio projects through `/api/uv/projects`;
- opening a project uses its stable project ID, not upstream chat/session identity;
- no Project Store filesystem logic is duplicated in frontend;
- CI remains green on Windows and Linux.

## Explicitly out of scope for this slice

- complete visual redesign/rebranding;
- Recipe Registry implementation;
- project delete/archive/import/export;
- media upload;
- music-video UI;
- OpenClaw integration;
- rewriting all existing VideoClaw pages.

The goal is to establish ownership of the user-facing product surface and make canonical UV Studio projects visible without throwing away the usable upstream interface.