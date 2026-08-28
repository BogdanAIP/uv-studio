# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: independent-code-review-policy -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

The repository is lifecycle-idle after `independent-code-review-policy` merged through PR #80 as `d0a59e62a96c3f0fcee60cc7db6286357b79f1a4`.

The declared next product slice remains `donor-ui-retirement`.

## Accepted review policy

Repository-local semantic review is now part of the accepted development process.

For later review-significant PRs:

1. fresh development/review invocations enumerate `.agents/skills/*/SKILL.md` from the live source ref before planning and load every applicable skill;
2. the required primary semantic reviewer is a separate fresh ordinary-ChatGPT context using `.agents/skills/code-review/SKILL.md` against an exact frozen `BASE_SHA..HEAD_SHA`;
3. the reviewer is read-only, reconstructs evidence independently, attempts to falsify candidate findings and reports only surviving correctness/security/recovery/concurrency/identity/authority/verification/acceptance issues introduced by the reviewed change;
4. every reported finding is validated by the development context as `CONFIRMED`, `REJECTED` or `SUPERSEDED` before merge;
5. material post-review changes invalidate the previous semantic review and require a fresh exact-head review;
6. Codex Review is optional additional evidence when quota is available and is not a merge dependency;
7. final exact-head CI/required physical evidence and zero unresolved review threads remain mandatory.

The adoption PR itself was intentionally governed by the previously accepted policy; the new rule governs subsequent review-significant PRs after this merge/closure.

## Accepted architecture baseline

The accepted caller/migration inventory is `docs/architecture/LEGACY_SURFACE_INVENTORY.md`. PR #77 satisfied the D-070 architecture-compression gate. The separate D-070 golden-vertical gate remains open.

Modern product work continues to target canonical Project Store, Production Directions, shared Production Semantic Core, Studio/Application Commands, canonical Timeline, Generation/Model Job authority and Capability/D-017 boundaries.

Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 composition and donor workflow APIs remain compatibility/migration surfaces under the accepted no-new-modern-caller rule. Useful dubbing, targeted-edit, continuity and music domain state/capabilities are not deleted as collateral damage.

## Accepted Stage 18 guarantees

D-066 layer 4 bounded background Agent execution remains accepted infrastructure. Later work must preserve the shared cross-runtime mutation fence, exact canonical freshness, Generation idempotency/D-017 atomicity, foreground/background coordinator ownership, restart-safe recovery and convergence of Agent/GUI/scripts/MCP on the same application/domain commands and Generation/Capability authorities.

## D-070 gate state

The architecture-compression gate is satisfied.

The golden-vertical gate remains open. Required combined user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

D-066 layers 5-7 remain deferred until the golden-vertical gate is also satisfied.

## Verification state

PR #80 final head `41e3c9db6661cd32d9322afabe8f99063c61b798` passed all five permanent checks in CI run #3806 and had no unresolved review threads before merge. An earlier duplicate run retained a stale draft-event payload and therefore failed only `development-context` after the PR had already transitioned to review; rerunning that old event necessarily reproduced `event.pull_request.draft does not match lifecycle_state`. The later Ready-for-review run used the correct event state and passed 5/5, and GitHub branch protection accepted the expected-head merge.

## Known adjacent implementation risk

A timing-sensitive production-form remount race remains open: `ProductionWorkspacePanel` can remount production semantics after history refresh and discard Shot input entered before refresh completion. This remains a separate implementation defect/risk and is not silently folded into donor UI retirement.

## Handoff

The next slice is `donor-ui-retirement`.

Its accepted prerequisites remain: eliminate or safely replace all supported write-capable donor frontend restoration paths while preserving only intended read-only provenance checks; migrate `/settings -> modelRegistry.ts -> fetchApiModels` to a modern model/capability client; only then remove donor-only UI/client remainder after exact zero-supported-caller, route, build and browser proof.
