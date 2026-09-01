# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Frozen head `a6324ec9f4113f62e82e19004a1ab82b276f8b3a` passed authoritative post-Ready CI #4298 **5/5**, but a completely fresh ordinary-ChatGPT semantic review returned two new `CURRENT` P1 findings. Both were independently confirmed against the exact frozen code. The review/freeze/CI evidence is therefore stale for merge authority and material repair is authorized only after this `review -> draft` transition.

## Confirmed fresh-review findings

### P1 — historical older-attempt Generation artifact can remain permanently unarchivable

The accepted BASE runtime could publish/register a Generation artifact, then fail before Take/Job success, mark that attempt `FAILED`, and permit a later retry. That creates a supported historical state where a durable artifact belongs to an older attempt while a newer attempt is current.

Current recovery scopes artifact discovery to `job.current_attempt`, so it cannot reconcile the older registered artifact. Current archive validation iterates every Generation ProjectReference but requires each one to match `attempts[-1]`, so the older durable reference can never become portable. The repair must reconcile and validate Generation authority by the artifact's own attempt identity rather than assuming every artifact belongs to the current attempt.

### P1 — SUCCEEDED Job can outlive its Production Take after ordinary Undo

Successful Generation persists artifact ProjectReference, Production Take, and Job success in separate durable operations. Project-level Undo can legitimately undo the `production.register_take` transaction while durable Generation Job provenance remains outside user Undo history.

Current archive validation only checks that the succeeded attempt contains a non-empty `take_id`; it does not resolve current Production Semantics. This can archive a Job claiming a Take that is absent from current Production authority. The repair must validate the actual Take/Shot/reference relationship and preserve explicit Undo/Redo semantics rather than treating the Job's string field alone as current Take authority.

## Previously repaired Stage-19 behavior retained

The new repair must preserve all earlier accepted behavior:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- fresh `ProjectUnitOfWork.commit()` rejection of raw schema-v1 `project.json`, with historical schema-v1 undo/redo migrated only for validation and restored as exact bytes;
- coherent cross-runtime Generation Job/publication fencing;
- exact Generation byte/digest/provenance verification and no provider replay during restart reconciliation;
- source `src_<uuid>` crash-orphan quarantine;
- arbitrary-path `timeline.assemble` durable publication markers;
- WebVTT `sub_<uuid>` orphan handling;
- archive raw-schema consistency, exact streamed ZIP hashing, technical lock-file exception and symlink fail-closed behavior;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair.

## Verification history

- Frozen head `e31f42afe652d7238be99388084a81684626fe08`: post-Ready CI #4265 **5/5**, then three confirmed findings.
- Draft repair head `1ad82d4c0475eb4fc05ad79ab45ede375601538d`: CI #4293 **5/5**.
- Frozen head `a6324ec9f4113f62e82e19004a1ab82b276f8b3a`: post-Ready CI #4298 **5/5**, then fresh review returned the two confirmed P1 findings above.

## Current repair gate

Lifecycle is `draft`. Next required work is bounded to the two confirmed Generation authority defects and focused regressions for their exact reachable states. After material repair and documentation synchronization, require exact Draft-head CI **5/5**, resolve any corresponding review threads with evidence, perform one context-only `draft -> review` freeze, return PR #89 to Ready, require post-Ready exact-head CI **5/5**, and run another completely fresh semantic review under BASE code-review v1.0.

Merge remains prohibited until a later `CURRENT` review reports zero findings and final live base/head/CI/thread identity is re-resolved.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
