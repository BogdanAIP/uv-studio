# Next Task

<!-- uv-next-slice: donor-ui-retirement -->

## Goal

After `architecture-compression-inventory` is accepted, merged and lifecycle-closed, perform the first bounded retirement slice by first removing every supported mechanism that can restore donor frontend state, extracting the one supported model-listing dependency currently shared through donor-era client glue, and only then removing donor frontend workflow surfaces whose zero-supported-caller gate is actually proven.

The expected deletion group is the old VideoClaw-style Workflow/Pipeline/Sandbox/stage UI and the donor-only remainder of its client glue. Two prerequisites must be satisfied before that deletion:

1. Donor frontend restoration is currently possible through more than the manually dispatched force-reset workflow. `.github/workflows/promote-frontend.yml` runs `python tools/promote_frontend.py --force`, which can replace the maintained UV-owned `frontend/`; plain `python tools/promote_frontend.py` also recreates the pinned donor frontend when `frontend/` is absent. `tools/uv_dev.py` and Windows `scripts/setup-dev.ps1` currently direct developers to the plain command when frontend files are missing, and `docs/FRONTEND.md` documents the promotion/provenance mechanism. The retirement slice must disable, remove or safely replace every supported write-capable donor restoration entry point and update its callers/guidance before claiming donor UI retirement.
2. `frontend/lib/workflowApi.ts` is **not** wholly donor-only today: supported `/settings` reaches `fetchApiModels` through `frontend/lib/modelRegistry.ts`. That model lookup must move to a modern model/capability client without changing Settings behavior.

## Required direction

- start only from lifecycle-idle `main` after the inventory PR is merged and closed;
- first disable, remove or replace all supported pinned-frontend restoration paths so repository automation, developer tooling, setup scripts, or documented recovery guidance cannot recreate the donor VideoClaw tree after cleanup; explicitly cover `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py` with and without `--force`, the `tools/uv_dev.py` missing-frontend guidance, Windows `scripts/setup-dev.ps1`, and the corresponding `docs/FRONTEND.md` instructions/provenance wording;
- retain a provenance verification/check-only path if still needed, but it must have no write authority over the maintained `frontend/` tree and must not offer an equivalent whole-frontend restore under another command/workflow name;
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

- direct proof that no enabled repository workflow, developer tool, setup script, or documented supported recovery path can restore the pinned donor frontend over the UV-owned `frontend/` tree after cleanup; explicitly cover `.github/workflows/promote-frontend.yml`, `tools/promote_frontend.py --force`, plain `tools/promote_frontend.py` when `frontend/` is absent, `tools/uv_dev.py`, `scripts/setup-dev.ps1`, and `docs/FRONTEND.md`;
- direct proof that any retained provenance command is check-only/read-only with respect to `frontend/`;
- direct proof that `/settings -> modelRegistry.ts` no longer imports model listing from `workflowApi.ts` and still receives the expected filtered model groups;
- exact recursive zero-supported-caller proof for every removed frontend file/client remainder;
- Next.js route inventory showing supported routes remain unchanged, including `/settings`;
- frontend lint and production build pass;
- permanent Ubuntu/Windows repository checks pass;
- browser coverage confirms supported Settings/Projects/Studio/legacy compatibility routes remain usable;
- no supported legacy project route or persisted project becomes unreadable;
- no new compatibility fallback, setup command, documented recovery instruction or reset mechanism is introduced that recreates the deleted donor UI.

## Entry gate

Begin only after the accepted `architecture-compression-inventory` confirms this restore-safe, extract-first `donor-ui-retirement` boundary and the repository is lifecycle-idle.
