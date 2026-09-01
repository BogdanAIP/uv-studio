# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `eaee4f1518638baaf8b4247e25183f2df1d70059` passed authoritative post-Ready CI #4321 (`33515948282`) **5/5** on Ubuntu and Windows, including full unit suites, API integration, pinned real-media verification, frontend lint/audit/build and browser Product Truth. Before a fresh semantic review was launched, two new inline P2 review findings appeared on that exact frozen head. Both were independently confirmed, PR #89 returned to Draft, and the freeze/CI evidence is stale for merge authority.

## Third review repair — confirmed findings

### P2 — managed publication recovery must match reference identity

`tasks/pub_<uuid>.json` markers already persist both the canonical `relative_path` and the expected `reference_id`. Current recovery only checks whether any Project source/artifact already names the marker path. A pre-existing dangling ProjectReference can therefore share the same path while naming a different identity; after a hard crash following replacement of bytes but before registration of the new reference, restart can incorrectly clear the marker and leave the new bytes falsely attributed to the old reference.

Repair requirement: a pending publication may be treated as already canonical only when the registered ProjectReference matches both the marker path and marker `reference_id`. A path-only match with the wrong identity must remain interrupted state and quarantine the crash-left bytes rather than silently clearing the marker.

### P2 — Generation recovery must preserve explicit Take Undo

A BASE-compatible interrupted Generation can have durable artifact + Take but still retain a failed/cancelled/RUNNING Job attempt because Job success persistence failed. The user may then explicitly Undo the `production.register_take` transaction before restart. Current recovery sees no live Take and creates a replacement Take, reversing the user's durable Undo and changing historical Take identity.

Archive already has durable UOW proof logic for the exact case where a `production.register_take` transaction created a Take and the latest committed operation for that transaction is Undo. Recovery must honor the same authority: if the artifact-owning attempt's historical Take is explicitly undone, recovery may reconcile the attempt without recreating that Take or inventing a new Take ID. Out-of-band/malformed missing-Take states remain fail-closed.

## Previous repair evidence retained

The current third repair must preserve all prior Stage-19 behavior:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, while historical schema-v1 undo/redo migrates only for validation and restores exact recorded bytes;
- coherent cross-runtime Generation Job/publication fencing;
- Generation recovery/archives validated by exact artifact-owning attempt identity, exact byte size/SHA-256 and full Job/model/execution/request/contract provenance;
- retry/fail/cancel blocked while any attempt owns unreconciled durable materialization;
- current Production Take authority distinguished from immutable Generation Job Take provenance, with archive accepting an absent Take only through exact durable Undo evidence;
- source `src_<uuid>` crash-orphan quarantine;
- arbitrary-path `timeline.assemble` durable publication markers;
- WebVTT `sub_<uuid>` orphan quarantine;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exclusion and symlink fail-closed behavior;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair;
- no provider replay during recovery.

## Verification history

- Frozen `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5**, then three confirmed findings.
- Draft repair `1ad82d4c0475eb4fc05ad79ab45ede375601538d`: CI #4293 **5/5**.
- Frozen `a6324ec9f4113f62e82e19004a1ab82b276f8b3a`: post-Ready CI #4298 **5/5**, then two confirmed P1 findings.
- Second material/test repair `e037d20c773a141dc24f35369179a581d4081e9c`: CI #4311 **5/5**.
- Final second-repair Draft head `4ef9f2f75497467f4b6ac68fb4b0961deef4fa99`: CI #4318 **5/5**.
- Frozen `eaee4f1518638baaf8b4247e25183f2df1d70059`: post-Ready CI #4321 **5/5**, then two new confirmed P2 findings above.

## Current repair gate

Lifecycle is `draft`; material/runtime/test repair is authorized only for the two confirmed P2 defects and focused regressions that reproduce their exact reachable states. After material repair and documentation synchronization:

1. require exact final Draft-head CI **5/5**;
2. reply to both open review threads with exact repair/test/CI evidence and resolve them only after validation;
3. perform one context-only `draft -> review` refreeze;
4. return PR #89 to Ready without changing the frozen head;
5. require authoritative post-Ready exact-head CI **5/5**;
6. verify zero unresolved review threads and exact live base/head identity;
7. run another completely fresh ordinary-ChatGPT semantic review under BASE `.agents/skills/code-review/SKILL.md` v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final base/head/CI/thread identity is re-resolved. Lifecycle closure remains a separate follow-up after merge.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
