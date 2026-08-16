# D-048 — Ship the current Next frontend as official standalone output

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The UV Studio frontend has an arbitrary dynamic `/projects/[projectId]` route and currently uses a Next rewrite to keep `/api/uv/*` same-origin while the FastAPI backend listens on loopback port 8000. A static export would simplify packaging but would change this runtime/routing contract and is therefore not safe to assume during release productization.

At the same time, the installed user must not need Node/npm or a source-tree `node_modules` directory.

## Decision

Stage 9 uses Next.js' supported `output: "standalone"` mode for the first Windows release frontend.

The build still runs from the locked frontend graph through `npm ci`, but the immutable installed frontend component is the traced standalone server payload rather than the source tree or development dependency directory.

`tools/stage_frontend_release.py` stages the release component by:

1. requiring `.next/standalone/server.js`;
2. copying the complete traced standalone output;
3. copying `.next/static` into the standalone `.next/static` location;
4. copying `public/` when present;
5. rejecting an already-populated destination instead of merging a new release over stale files.

The release frontend component entrypoint remains `frontend/server.js`; the Node executable is a separate D-044 component pinned by D-046.

## Verification

The dedicated Windows Node 24.19.0 release frontend job must not stop at `next build`. It stages the standalone payload, starts the staged `server.js` with Node 24 and verifies HTTP 200 for both the root route and an arbitrary synthetic `/projects/<id>` route. This proves that packaging did not collapse the dynamic project router into a static-only site.

Combined backend API rewrites and permanent browser outcomes are a later full-release gate after backend/media/launcher assembly. This decision covers the frontend component boundary only.

## Consequences

- Installed UV Studio does not require npm or the source frontend tree.
- Dynamic project URLs remain supported without inventing a second router.
- The first release still contains a Node runtime; this is intentional and explicit, not a user prerequisite.
- A future Node-free frontend is allowed only after equivalent routing, API proxy and permanent browser outcomes are proven through the packaged application.
- Next build output is intermediate build material; only the staged standalone directory belongs in the D-044 immutable release payload.
