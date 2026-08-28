# Next Task

<!-- uv-next-slice: donor-ui-retirement -->

## Goal

After `architecture-compression-inventory` is accepted, merged and lifecycle-closed, perform the first bounded retirement slice by first removing the mechanisms that can restore donor frontend state, extracting the one supported model-listing dependency currently shared through donor-era client glue, and only then removing donor frontend workflow surfaces whose zero-supported-caller gate is actually proven.

The expected deletion group is the old VideoClaw-style Workflow/Pipeline/Sandbox/stage UI and the donor-only remainder of its client glue. Two prerequisites must be satisfied before that deletion:

1. `.github/workflows/promote-frontend.yml` currently allows manual `workflow_dispatch` of `python tools/promote_frontend.py --force`; that command replaces the entire UV-owned `frontend/` tree from the pinned VideoClaw frontend and can therefore restore retired donor surfaces. The retirement slice must disable, remove or safely replace this destructive reset path before claiming donor UI retirement.
2. `frontend/lib/workflowApi.ts` is **not** wholly donor-only today: supported `/settings` reaches `fetchApiModels` through `frontend/lib/modelRegistry.ts`. That model lookup must move to a modern model/capability client without changing Settings behavior.

## Required direction

- start only from lifecycle-idle `main` after the inventory PR is merged and closed;
- first disable, remove or replace the manual pinned-frontend reset path so repository automation cannot overwrite the UV-owned frontend with the donor VideoClaw tree after cleanup; do not leave an equivalent `--force` whole-frontend replacement path under another workflow name;
- move `fetchApiModels` used by `/settings -> modelRegistry.ts` out of `workflowApi.ts` into an appropriate modern model/capability API client, preserving the existing model-listing/filter contract;
- only after both prerequisites are proven, remove donor Workflow/Pipeline/Sandbox/stage roots and any `workflowApi.ts` remainder that an exact recursive scan proves has no supported caller;
- remove only items classified **DELETE LATER** whose deletion gate is fully satisfied by the accepted inventory; treat mixed **ADAPT → DELETE LATER** glue as extract-first;
- do not remove the live legacy `/projects/[projectId]` compatibility route merely because donor components are removed;
- do not conflate `frontend/components/stages/**` donor workflow UI with live Stage 8 editor panels such as `Stage8CompositionPanel` / `Stage8MediaPanel`;
- do not remove Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 API/workspace, schema-v1 `recipe_id`, or useful dubbing/music/continuity/targeted-edit domain state in this slice;
- preserve the modern `/projects/[projectId]/studio` route and Production Direction creation path;
- preserve `/settings` and its model selection behavior;
- preserve Stage-18 mutation/recovery guarantees.

## Required proof

At minimum:

- direct proof that no enabled repository workflow/tool path can restore the pinned donor frontend over the UV-owned `frontend/` tree after cleanup; explicitly cover `.github/workflows/promote-frontend.yml` and `tools/promote_frontend.py --force`;
- direct proof that `/settings -> modelRegistry.ts` no longer imports model listing from `workflowApi.ts` and still receives the expected filtered model groups;
- exact recursive zero-supported-caller proof for every removed frontend file/client remainder;
- Next.js route inventory showing supported routes remain unchanged, including `/settings`;
- frontend lint and production build pass;
- permanent Ubuntu/Windows repository checks pass;
- browser coverage confirms supported Settings/Projects/Studio/legacy compatibility routes remain usable;
- no supported legacy project route or persisted project becomes unreadable;
- no new compatibility fallback or reset mechanism is introduced to recreate the deleted donor UI.

## Entry gate

Begin only after the accepted `architecture-compression-inventory` confirms this reset-safe, extract-first `donor-ui-retirement` boundary and the repository is lifecycle-idle.
