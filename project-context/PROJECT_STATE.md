# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: independent-code-review-policy -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`independent-code-review-policy` is the active process-only slice, started from lifecycle-idle `main` after architecture-compression inventory closure PR #78 merged as `aa0d17308ca8c034175e4429f8535fb70dc8d026`.

This slice changes repository review/bootstrap policy only. It does not change UV Studio runtime, frontend, canonical project state, CI implementation or product architecture. The declared product handoff remains `donor-ui-retirement`.

The policy being introduced is not self-applying: this adoption PR is governed by the previously accepted merge discipline. After the policy is merged and lifecycle-closed, later review-significant PRs must use the accepted fresh ordinary-ChatGPT semantic review protocol.

## Accepted architecture baseline

The accepted caller/migration inventory is `docs/architecture/LEGACY_SURFACE_INVENTORY.md`. PR #77 satisfied the D-070 **architecture-compression gate**. The separate D-070 **golden-vertical gate** remains open.

Modern product work continues to target:

- canonical Project Store;
- Production Directions;
- shared Production Semantic Core;
- Studio/Application Commands;
- canonical Timeline;
- Generation/Model Job authority;
- Capability/D-017 boundaries.

Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 composition and donor workflow APIs remain compatibility/migration surfaces under the accepted no-new-modern-caller rule. Useful dubbing, targeted-edit, continuity and music domain state/capabilities are not deleted as collateral damage.

The accepted detailed retirement order and exact caller/deletion gates remain owned by `docs/architecture/LEGACY_SURFACE_INVENTORY.md` and the current `NEXT_TASK.md`; this state file does not duplicate that table.

## Accepted Stage 18 guarantees

D-066 layer 4 bounded background Agent execution remains accepted infrastructure. Later work must preserve:

- the shared cross-runtime project mutation fence;
- Production/Timeline/project JSON serialization guarantees;
- exact canonical freshness for background claims;
- Generation same-key idempotency and one-shot D-017 consumption/reservation atomicity;
- foreground/background coordinator ownership;
- restart/recovery rules that avoid replay of ambiguous work;
- Agent convergence on the same Studio/Application Commands and Generation/Capability authorities as GUI/scripts/MCP.

## D-070 gate state

The **architecture-compression gate is satisfied**.

The **golden-vertical gate remains open**. Required combined user-visible proof remains:

`New Project -> micro_drama -> Scene -> Shot -> named generation Job -> Take candidate -> Accept -> canonical Timeline -> Export`

D-066 layers 5-7 remain deferred until the golden-vertical gate is also satisfied.

## Active review-policy change

The current process slice introduces `.agents/skills/code-review/SKILL.md` and wires it into repository bootstrap and merge discipline.

Once accepted, review-significant changes will require:

1. a frozen exact `BASE_SHA..HEAD_SHA`;
2. a fresh ordinary-ChatGPT review context using the repository `code-review` skill;
3. read-only independent evidence reconstruction and falsification of candidate findings;
4. explicit validation of every reported finding as `CONFIRMED`, `REJECTED` or `SUPERSEDED`;
5. a fresh review after material post-review changes;
6. final exact-head CI/physical evidence as applicable;
7. exact reviewed base/head identity still matching before merge.

Codex Review remains optional additional evidence when quota is available. Codex quota exhaustion alone must not block merge after the mandatory ordinary-ChatGPT review and all other applicable gates pass.

Skill discovery is repository-driven: fresh development invocations enumerate `.agents/skills/*/SKILL.md` from the live source ref and load applicable skills before planning/implementation rather than relying on remembered skill names or cached text.

## Verification state

PR #77 merged as `c6831a36eb88289947eed1da65609654a2353524` after its final head passed all five permanent CI jobs and review conversations were resolved. Lifecycle closure PR #78 then passed the permanent checks on exact head `23781ee6b87f6a6f19fb1bfc7ca78399c03f1e5e` and merged as `aa0d17308ca8c034175e4429f8535fb70dc8d026`.

During closure, GitHub had two CI runs for the same exact SHA; one Windows browser run hit the known `micro_drama` form-remount race while another same-SHA run passed. Re-running only the failed duplicate Windows job passed the full browser suite, allowing the protected merge without changing closure bytes.

## Known adjacent implementation risk

A timing-sensitive production-form remount race remains open: `ProductionWorkspacePanel` can remount production semantics after history refresh and discard Shot input entered before refresh completion. Repeated same-SHA Windows browser runs have alternated between passing and timing out on disabled `Создать кадр`.

This is a separate implementation defect/risk. It is not silently folded into the review-policy slice or donor UI retirement.

## Handoff

The declared next product slice remains `donor-ui-retirement`.

Its accepted prerequisites remain: first eliminate or safely replace every supported write-capable donor frontend restoration path while preserving only intended read-only provenance checks; then migrate `/settings -> modelRegistry.ts -> fetchApiModels` to a modern model/capability client; only then remove donor-only UI/client remainder after exact zero-supported-caller, route, build and browser proof.
