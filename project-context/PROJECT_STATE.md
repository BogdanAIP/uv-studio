# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is temporarily back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The production/runtime repair is unchanged. Regression-first commit `75aed8ea5326dd2891007632ef42dbf20fc60ba0` covers direct `GenerationService.run()` retry in the redo-only terminal split, and runtime repair `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09` places the Redo-aware durable-materialization guard at the shared `GenerationJobManager.start_execution()` boundary before another attempt/provider execution can begin.

The lifecycle was returned from `review` to `draft` only to correct a process-context ordering mismatch discovered before the new mandatory fresh review. No runtime, test, schema, product, review-policy or merge-policy behavior is being changed.

## Repaired invariant

A validated Generation materialization reachable only through the current durable ProjectUnitOfWork Redo suffix blocks every failed-job execution entry point before new attempt/provider execution. Direct `GenerationService.run()`, explicit HTTP retry and Job terminal transitions converge on the same fail-closed authority. Explicit Redo may restore the exact validated reference, after which local recovery may complete the owning attempt without provider replay.

## Verification already obtained

Accepted evidence includes:

- prior frozen Ready head `16f597ff5a1bea7e0353c64e824712b69829b235`, post-Ready CI #4609 (`33746380980`): **5/5 SUCCESS**, followed by a fresh review that returned one confirmed P1 and therefore became stale after repair;
- P1 repair/context head `9b3fd0ce5814ead7b36579b073c11f13f9f315de`, CI #4619 (`33761623377`): **5/5 SUCCESS**;
- synchronized Draft head `5b59495e9b733f4af790c16bc8b4e869089214aa`, CI #4624 (`33762251065`): **5/5 SUCCESS**;
- prior refrozen head `5bc3943f188c0c96958c2480b5a22d4f02b30b34`, Ready-triggered CI #4628 (`33763695643`): **5/5 SUCCESS** across development-context, both Ubuntu/Windows full unit suites, and both Ubuntu/Windows app-baseline API/real-media/frontend/browser Product Truth jobs.

CI #4628 is retained as useful preliminary exact-head evidence, but it is **not** the final merge CI gate because the accepted BASE `AGENTS.md`, `DEVELOPMENT_PROTOCOL.md` and `code-review` v1.0 require the governed sequence to place the mandatory fresh semantic review before the final exact-head CI/acceptance confirmation.

No runtime, test, schema or product behavior has changed after `c53ce45b8f2ff4c5d50dae147e6e649c4af9ff09`.

## Correct governed continuation

The accepted sequence for this review-significant PR is:

1. keep PR #89 Draft while this context correction is synchronized and validated;
2. refreeze lifecycle `draft -> review` without runtime/test/schema/product changes and mark the PR Ready;
3. freeze the resulting exact BASE/HEAD identity;
4. launch the mandatory genuinely fresh ordinary-ChatGPT read-only semantic review using the BASE `AGENTS.md` and `.agents/skills/code-review/SKILL.md` v1.0;
5. validate every reported finding; any confirmed material finding returns the PR/lifecycle to Draft before repair and makes that review stale;
6. only after a `CURRENT / PASS / 0 findings` review, require the final exact-head permanent CI/browser/real-media acceptance confirmation on the same reviewed HEAD;
7. re-resolve live BASE/HEAD, mergeability and unresolved review threads, then merge with expected HEAD SHA;
8. after merge, perform mandatory D-038 lifecycle closure to `idle` before starting the declared handoff.

The review launcher must contain immutable `REVIEW_REQUEST_V1` identity plus a neutral direct instruction to perform the repository `code-review` skill. It must not include developer reasoning, proposed findings or an argument that the change is correct.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
