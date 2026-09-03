# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The prior frozen Ready head `4f8f1e55c9bfd3ef8289a3964fa94707ee4b1f1c` passed post-Ready CI #4583 **5/5 SUCCESS**, then the mandatory genuinely fresh ordinary-ChatGPT `code-review` v1.0 returned `review_validity=CURRENT`, `status=FINDINGS`, `reported_findings=1`, `rejected_candidates=17`. The single P2 was confirmed and is now materially repaired. That earlier review is stale.

The repaired documentation-synchronized Draft head `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8` passed CI #4598 (`33740778124`) **5/5 SUCCESS**. The final synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066` then passed authoritative Draft gate CI #4602 (`33741327112`) **5/5 SUCCESS**. Live PR identity before refreeze remained open, Draft, mergeable, BASE `52be1939eca51d7147990288cfc6258b023c2cd2`, HEAD `106b7396b9e8681550cb59b411b8cb0935f88066`; live inline review-thread count was zero unresolved.

Lifecycle commit `c65e2451766c0375c3e4ea90d5be68e3df1db320` changes only `ACTIVE_SLICE.json` from `draft` to `review`. This synchronized context commit records the corresponding review freeze; no runtime, test, schema or product behavior changes after the successful Draft gate.

## Confirmed fresh-review P2: redo-only legacy Generation terminal split

A supported legacy terminal split can contain exact durable Generation bytes and ProjectReference provenance while the owning attempt/job remains `FAILED` after a local post-artifact failure. If the user Undo-es `generation.register_output`, the reference becomes reachable only through the durable Redo suffix while its bytes remain present.

On the old review head, redo-owned validation incorrectly required completed `SUCCEEDED + output_reference_id + take_id` authority before startup could reach the reconciler that establishes those fields. At the same time, retry scanned only live `Project.artifacts`, so it could miss the redo-only durable output and permit a duplicate provider attempt.

The repair preserves explicit user Undo and separates two authority levels:

- incomplete immutable Generation materialization authority: exact Job/Attempt/request/provenance/path/size/SHA, including bounded RUNNING/FAILED/CANCELLED split states;
- completed Generation authority: the stricter successful attempt/output-reference/Take authority still required by archive/success paths.

Startup can therefore validate and preserve redo-only incomplete materialization bytes without resurrecting current Project/Take state or replaying the provider. Retry validates current Redo authority and remains blocked while that unreconciled materialization is reachable. Explicit user Redo restores the exact reference only after binary validation; ordinary local recovery can then complete the owning attempt without another provider execution. Archive remains strict and does not export incomplete materialization as successful Generation authority.

Regression `tests/test_stage19_redo_terminal_split_recovery.py` covers the exact chain: post-artifact local failure -> legacy `FAILED` attempt -> Undo `generation.register_output` -> restart -> retry rejection -> explicit Redo -> local reconciliation, with executor invocation count remaining exactly one.

Repair commits:

- `6a2c1f67a9a805248fb132ee4ad1be4249fc91bb` — distinguish incomplete materialization authority from completed Generation authority;
- `19cec67a23f107efdcb0429e40bd86428a14d98e` — include validated redo-owned materialization in the retry guard;
- `8c8a1b2c27f4bc8198eeb832e92e20a9ad4c6210` — add the combined terminal-split/Undo/restart/retry/Redo regression;
- `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8` — synchronize portable archive documentation with incomplete-vs-completed Generation authority.

## Verification

Current repair evidence:

- material/documentation repair head `0c757c86eda9a489ea403f27c1f1cb0c6c2bead8`, CI #4598 (`33740778124`): **5/5 SUCCESS**;
- synchronized Draft head `106b7396b9e8681550cb59b411b8cb0935f88066`, CI #4602 (`33741327112`): **5/5 SUCCESS**;
- development-context — SUCCESS;
- Ubuntu full unit suite — SUCCESS, including the redo-only terminal-split regression;
- Windows full unit suite — SUCCESS, including the same regression;
- Ubuntu app-baseline — SUCCESS including API, real-media, frontend lint/audit/build and browser Product Truth;
- Windows app-baseline — SUCCESS including API, pinned media toolchain, real-media, frontend lint/audit/build and browser Product Truth.

All earlier Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, exact legacy recipe compatibility, ProjectUnitOfWork exact-byte v1/v2 Undo/Redo, prepared-UOW archive recovery, archive snapshot locking, source/WebVTT/Generation publication fences, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation and byte validation, publication-marker reference identity, Generation digest/provenance/path/lineage authority, direct Redo binary validation, leased root staging with cross-runtime allocation/recovery serialization, and immediate-next-action Product Truth behavior.

## Review freeze

No material runtime/test/schema/product mutation is allowed while this freeze remains current. Any supported material finding requires returning PR #89 and lifecycle to Draft before repair.

## Next required action

1. synchronize the PR body with this repaired review freeze and exact frozen HEAD;
2. mark PR #89 Ready without material changes;
3. require a **new post-Ready exact-head CI 5/5** distinct from Draft CI #4602;
4. re-resolve live BASE/HEAD/mergeability and zero unresolved inline threads;
5. perform a **new** genuinely fresh ordinary-ChatGPT read-only semantic review under immutable BASE `.agents/skills/code-review/SKILL.md` v1.0;
6. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live identity and exact-head CI.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
