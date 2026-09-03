# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` remains in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `4f8f1e55c9bfd3ef8289a3964fa94707ee4b1f1c` passed post-Ready CI #4583 **5/5 SUCCESS**, then a mandatory genuinely fresh ordinary-ChatGPT `code-review` v1.0 returned `review_validity=CURRENT`, `status=FINDINGS`, `reported_findings=1`, `rejected_candidates=17`. The single P2 was classified **CONFIRMED**. That review is stale after the material repair below.

The repaired documentation-synchronized Draft head `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8` passed authoritative CI #4598 (`33740778124`) **5/5 SUCCESS** across development-context, both full Ubuntu/Windows unit suites and both app-baseline API/real-media/frontend/browser Product Truth jobs.

## Confirmed fresh-review P2: redo-only legacy Generation terminal split

The supported legacy terminal-split recovery path can contain a durable Generation artifact while its owning Job/Attempt is still `FAILED` after a local post-artifact failure. If the user then Undo-es `generation.register_output`, the ProjectReference becomes reachable only through the durable Redo suffix while the exact output bytes remain in place.

On `4f8f1e55...`, redo-owned validation used the same authority as completed Generation. It therefore required the owning attempt already to be `SUCCEEDED` with `output_reference_id` and `take_id` before startup could reach the later materialization reconciler that exists to establish those fields. The retry guard simultaneously inspected only current `Project.artifacts`, so the undone durable output could be missed and a duplicate provider retry could be queued.

The repair preserves explicit user Undo rather than silently restoring canonical state:

- `uv_studio/projects/generation_authority.py` distinguishes immutable **Generation materialization authority** (Job/Attempt/request/provenance/path/size/SHA, including bounded RUNNING/FAILED/CANCELLED split states) from the stricter **completed Generation authority** used by archive/success paths;
- redo reconstruction and direct Redo can validate exact incomplete historical materialization bytes without claiming that the attempt is already successful;
- startup preserves a valid redo-only incomplete materialization without recreating its current ProjectReference or Take and without provider replay;
- `requeue_failed_generation_job()` validates current Redo authority and blocks retry when that Job owns an unreconciled redo-only materialization;
- after explicit user Redo restores the ProjectReference, ordinary startup recovery completes the legacy materialization locally and marks the owning attempt successful;
- archive remains strict: portable Generation authority still requires a durable successful attempt, exact output-reference/Take authority and exact bytes.

Regression `tests/test_stage19_redo_terminal_split_recovery.py` exercises the exact combined state: post-artifact local failure -> legacy `FAILED` attempt -> Undo `generation.register_output` -> restart -> retry rejection -> explicit Redo -> local reconciliation, with executor invocation count remaining exactly one. The regression passed in both full Ubuntu and Windows suites in CI #4598.

Repair commits:

- `6a2c1f67a9a805248fb132ee4ad1be4249fc91bb` — distinguish incomplete materialization authority from completed Generation authority;
- `19cec67a23f107efdcb0429e40bd86428a14d98e` — include validated redo-owned materialization in the retry guard;
- `8c8a1b2c27f4bc8198eeb832e92e20a9ad4c6210` — add the combined terminal-split/Undo/restart/retry/Redo regression;
- `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8` — synchronize the portable archive contract with incomplete-vs-completed Generation authority.

## Prior Stage-19 authority retained

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, source FFprobe publication-fence exception, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest/provenance authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability, direct Redo binary validation, leased root staging and cross-runtime allocation/recovery serialization, plus immediate-next-action Product Truth behavior.

Root staging/leases and the root coordination lock remain transient runtime coordination only. They add no Project, Production, Generation, media-history or Undo/Redo authority and remain outside `.uvproj.zip` payloads.

## Verification

Historical pre-finding evidence:

- material root-staging head `386e5a8794dd79e53f1920a78cd06a8657a857fb`, CI #4574: **5/5 SUCCESS**;
- synchronized Draft head `963e85123dd36ac4e6bef84ed5d702c915a3fc00`, CI #4577: **5/5 SUCCESS**;
- prior Ready head `4f8f1e55c9bfd3ef8289a3964fa94707ee4b1f1c`, post-Ready CI #4583: **5/5 SUCCESS**;
- mandatory fresh review on `4f8f1e55...`: **CURRENT / FINDINGS / 1 P2 / 17 rejected candidates**.

Current repair evidence:

- documentation-synchronized Draft head `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8`, CI #4598 (`33740778124`): **5/5 SUCCESS**;
- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS, including the new redo-only terminal-split regression;
- Windows full unit suite — SUCCESS, including the same regression;
- Ubuntu app-baseline — SUCCESS including API, real-media, frontend lint/audit/build and browser Product Truth;
- Windows app-baseline — SUCCESS including API, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

This context-only evidence synchronization does not change runtime, test, schema or product behavior. It requires its own exact-head Draft context gate before review refreeze.

## Next required action

1. require exact-head Draft CI 5/5 on this context-synchronized head;
2. synchronize the PR body and re-resolve live BASE/HEAD/mergeability/threads;
3. refreeze lifecycle `draft -> review` without material runtime/test changes;
4. mark PR #89 Ready and require a new post-Ready exact-head CI 5/5;
5. perform a **new** genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0 because the `4f8f1e55...` review is stale after this repair;
6. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live BASE/HEAD/CI/thread identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
