# Next Task

<!-- uv-next-slice: donor-ui-retirement -->

## Goal

After `architecture-compression-inventory` is accepted, merged and lifecycle-closed, perform the first bounded retirement slice by removing only donor-era frontend workflow surfaces that the accepted inventory proves have no supported route, import, runtime or persisted-project caller.

The expected candidate group is the old VideoClaw-style Workflow/Pipeline/Sandbox/stage UI and its donor-only client glue. This handoff is intentionally subordinate to the inventory: if the accepted caller map shows that another retirement/extraction must happen first, update this task and the lifecycle handoff before the inventory PR becomes ready for review.

## Required direction

- start only from lifecycle-idle `main` after the inventory PR is merged and closed;
- remove only items classified **DELETE LATER** whose deletion gate is fully satisfied by the accepted inventory;
- do not remove the live legacy `/projects/[projectId]` compatibility route merely because donor components are removed;
- do not conflate `frontend/components/stages/**` donor workflow UI with live Stage 8 editor panels such as `Stage8CompositionPanel` / `Stage8MediaPanel`;
- do not remove Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 API/workspace, schema-v1 `recipe_id`, or useful dubbing/music/continuity/targeted-edit domain state in this slice unless the accepted inventory explicitly selects a different first retirement;
- preserve the modern `/projects/[projectId]/studio` route and Production Direction creation path;
- preserve Stage-18 mutation/recovery guarantees.

## Required proof

At minimum:

- exact zero-supported-caller proof for every removed frontend file/client;
- Next.js route inventory showing supported routes remain unchanged;
- frontend lint and production build pass;
- permanent Ubuntu/Windows repository checks pass;
- no supported legacy project route or persisted project becomes unreadable;
- no new compatibility fallback is introduced to replace the deleted donor UI.

## Entry gate

Begin only after the accepted `architecture-compression-inventory` explicitly confirms this as the first safe retirement slice and the repository is lifecycle-idle.
