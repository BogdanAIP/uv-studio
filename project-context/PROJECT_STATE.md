# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-02

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is refrozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The previous fresh ordinary-ChatGPT review of frozen head `a8b9844ccc93a91512f96bf0edc0338070bb694e` returned one `CURRENT` P2: archive export could trigger recovery of crash-left prepared UOW state only after sampling schema, Project ownership and filesystem membership. PR #89 returned to Draft before repair.

## Eighth repair accepted in Draft

Regression `1999185c0c7f01cca765345caa3e63cd01572dfd` deterministically interrupts a real UOW commit after after-snapshots/history are written but before the committed marker. It proves a prepared first schema-v1→v2 transaction is recovered to exact historical v1 bytes before archive sampling and remains importable, and proves prepared artifact registration cannot leave stale pre-recovery media ownership in the archive.

Runtime `80fe2b3076b64a94c8d6ebc7118f79c3af88688d` adds only four lines in `export_project()`: under the already-held shared project fence, call recovery-capable `ProjectUnitOfWork(store).history(project_id)` before loading Project state, reading raw schema version or enumerating filesystem membership. UOW semantics and binary-history authority are unchanged.

Material/test head `80fe2b3076b64a94c8d6ebc7118f79c3af88688d` passed CI #4418 (`33601095299`) **5/5**. Final synchronized Draft head `1f36c87a2f4cd1b0c9c2b4376ede7089b3f991c4` passed authoritative post-body-sync CI #4422 (`33601720381`) **5/5**: development-context, both full unit suites, and both app-baseline API/real-media/frontend/browser Product Truth jobs succeeded.

The prepared-UOW P2 thread `PRRT_kwDOT0Lyms6eXd2v` was replied to with concrete regression/runtime/CI evidence and resolved. Live recheck showed no unresolved inline review threads before this context-only refreeze.

## Frozen review boundary

Only `project-context/ACTIVE_SLICE.json` and this `PROJECT_STATE.md` change during the refreeze from the accepted Draft head. No runtime, test, schema or product behavior changes after CI #4422. The exact frozen review HEAD is resolved externally after these context commits and must remain unchanged through Ready state, post-Ready CI and the next fresh independent semantic review.

All previous Stage-19 repairs remain in force: schema-v1/v2 compatibility and exact historical identity, archive locking/snapshot/digest authority, staged/fenced publication, Generation attempt/Job/artifact/Take recovery and corruption checks, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation across startup/archive, publication-marker reference identity, and immediate-next-action Product Truth behavior.

## Next required action

1. synchronize the PR body with the exact frozen review HEAD;
2. mark PR #89 Ready for review without changing Git HEAD;
3. require authoritative post-Ready exact-head CI 5/5 and recheck live BASE/HEAD/thread identity;
4. run a completely fresh ordinary-ChatGPT semantic review under governing BASE `.agents/skills/code-review/SKILL.md` v1.0 against exact BASE..HEAD;
5. merge only on `CURRENT PASS` with zero findings and clean final live identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
