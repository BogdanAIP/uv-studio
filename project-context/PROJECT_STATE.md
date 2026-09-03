# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The production/runtime repair is unchanged. Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` covers direct `GenerationService.run()` retry in the redo-only terminal split, and runtime repair `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` places the Redo-aware durable-materialization guard at the shared `GenerationJobManager.start_execution()` boundary before another attempt/provider execution can begin.

Process-context correction commit `90531357773ba1bc1360a66f7c3c143b56b121c8` returned the lifecycle to Draft only to align the active merge sequence with accepted BASE policy. It changed no runtime, test, schema, product, review-policy or merge-policy behavior. Authoritative Draft CI #4632 (`33770513959`) then passed **5/5 SUCCESS** across development-context, both Ubuntu/Windows full unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs.

## Repaired invariant

A validated Generation materialization reachable only through the current durable ProjectUnitOfWork Redo suffix blocks every failed-job execution entry point before new attempt/provider execution. Direct `GenerationService.run()`, explicit HTTP retry and Job terminal transitions converge on the same fail-closed authority. Explicit Redo may restore the exact validated reference, after which local recovery may complete the owning attempt without provider replay.

## Verification already obtained

Accepted evidence includes:

- prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235`, CI #4609 (`33746380980`): **5/5 SUCCESS**, followed by a fresh review that returned one confirmed P1 and became stale after repair;
- P1 repair/context head `9b3fd0ce5814ead7b36579b073c11f13f9f315de`, CI #4619 (`33761623377`): **5/5 SUCCESS**;
- synchronized Draft head `5b59495e9b733f4af790c16bc8b4e869089214aa`, CI #4624 (`33762251065`): **5/5 SUCCESS**;
- prior refrozen head `5bc3943f188c0c96958c2480b5a22d4f02b30b34`, Ready-triggered CI #4628 (`33763695643`): **5/5 SUCCESS**; this is preliminary evidence, not the post-review final merge gate;
- corrected Draft head `90531357773ba1bc1360a66f7c3c143b56b121c8`, authoritative post-body-sync CI #4632 (`33770513959`): **5/5 SUCCESS**.

No runtime, test, schema or product behavior has changed after `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09`.

## Governed continuation

The accepted sequence for this review-significant PR is now explicit and synchronized:

1. this context-only refreeze establishes a new exact review HEAD and prohibits material runtime/test/schema/product changes;
2. mark PR #89 Ready and verify live BASE/HEAD/lifecycle identity;
3. launch the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review using the BASE `AGENTS.md` and `.agents/skills/code-review/SKILL.md` v1.0;
4. validate every reported finding; any confirmed material finding requires returning the PR/lifecycle to Draft before repair and makes that review stale;
5. only after a `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` result, require the final exact-head permanent CI/browser/real-media acceptance confirmation on that same reviewed HEAD;
6. re-resolve live BASE/HEAD, mergeability and unresolved review threads, then merge with expected HEAD SHA;
7. after merge, perform mandatory D-038 lifecycle closure to `idle` before starting the declared handoff.

The review launcher contains immutable `REVIEW_REQUEST_V1` identity plus a neutral direct instruction to perform the repository `code-review` skill. It must not include developer reasoning, proposed findings or an argument that the change is correct.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
