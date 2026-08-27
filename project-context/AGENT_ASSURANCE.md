# Agent Assurance

## Purpose

`UV-AVS-0` adds a small deterministic assurance layer for already accepted Stage-16/17 Agent behavior before D-066 layer 4 introduces background workers, leases, heartbeats and longer recovery paths.

This is **test infrastructure only**. It does not add a second Agent runtime, planner, permission system, provider path, canonical state store or product execution authority.

The pilot turns high-value review findings into executable guarantees:

```text
review finding
 -> named guarantee
 -> exact curated source mutation
 -> exact existing regression detector
 -> isolated mutated source overlay
 -> KILLED / SURVIVED / ERROR
```

## Pilot suite

Manifest: `project-context/agent-assurance-stage17.json`

Runner: `tools/agent_assurance.py`

Detector helper: `tools/agent_assurance_detector.py`

Regression/meta-tests: `tests/test_agent_stage17_assurance.py`

The initial `stage17-curated-v1` suite contains exactly six mutants:

| ID | Guarantee | Exact detector |
| --- | --- | --- |
| `UV-ROLE-001` | persistence revalidates plan/media output against the role allowlist | `test_persist_plan_revalidates_media_role_for_exactly_addressed_result` |
| `UV-CTX-001` | delegation fails closed if bounded canonical context changes while the proposer runs | `test_delegate_fails_closed_when_role_context_changes_during_proposal` |
| `UV-CTX-002` | persistence rejects a role result whose bounded context became stale after delegation | `test_persist_rejects_stale_plan_role_result_after_project_change` |
| `UV-NS-001` | proposals cannot mint canonical identities in the reserved delegation namespace | `test_planned_canonical_output_cannot_occupy_delegation_namespace` |
| `UV-PROV-001` | delegation-looking syntax alone is not Stage-17 provenance; the durable Plan binding is required | `test_delegation_like_stage16_canonical_refs_are_not_stage17_origin` |
| `UV-AUTH-001` | an injected Stage-17 task coordinator must share the exact AgentHarness, Project Store and Planner authority | `test_injected_task_coordinator_must_share_exact_harness_authority` |

The exact module, target file, detector and replacement anchor for every case live in the manifest so the mutation is reviewable rather than hidden in runner code.

## Execution model

For each mutant the runner performs these steps:

1. copy the full `uv_studio` package to a fresh temporary directory, excluding bytecode caches;
2. hash the checkout target and copied target and require exact equality;
3. launch the exact detector in a **fresh Python process** against the unmodified overlay;
4. require the baseline detector to pass exactly once;
5. require the manifest mutation anchor to occur exactly once;
6. apply the mutation only inside the temporary overlay;
7. hash the mutated target and require the digest to differ from baseline;
8. launch the same exact detector in another fresh Python process;
9. prove the target module was imported from the temporary overlay, that its source path equals the exact declared target path inside that overlay, and that the imported source SHA-256 equals the exact expected baseline/mutated bytes;
10. classify the result and delete the temporary overlay.

The checkout is never edited by the mutation runner.

## Classification

### `KILLED`

A valid baseline detector passed, exact source binding passed, and the mutated implementation produced a normal unittest **assertion failure** with no unittest error.

This is the only accepted result for a curated pilot mutant.

### `SURVIVED`

The exact baseline detector passed and the same detector also passed after the exact mutation.

A surviving curated mutant is a real assurance gap: either the guarantee lacks sufficient detector coverage or the mutant does not actually invalidate the stated guarantee.

### `ERROR`

The runner cannot establish a meaningful mutant result. Examples:

- invalid manifest;
- missing/non-unique mutation anchor;
- baseline detector failure;
- import failure;
- detector resolution failure;
- target module imported from the normal checkout instead of the overlay;
- imported module path differs from the exact declared mutation target;
- imported source SHA mismatch;
- timeout;
- unittest error rather than assertion failure;
- target/source-copy mismatch.

`ERROR` is never treated as `KILLED`. The harness fails closed rather than turning broken test infrastructure into false assurance.

## Commands

Run all curated mutants:

```text
python tools/agent_assurance.py
```

Run one mutant:

```text
python tools/agent_assurance.py --mutant UV-PROV-001
```

Write a machine-readable report:

```text
python tools/agent_assurance.py --report agent-assurance-report.json
```

List the suite without executing mutants:

```text
python tools/agent_assurance.py --list
```

The ordinary unit suite also runs the full curated pilot through `tests/test_agent_stage17_assurance.py`, so both Ubuntu and Windows bootstrap checks exercise the same assurance contract.

## Source-binding boundary

The pilot deliberately does not accept "we wrote mutated bytes somewhere" as proof that those bytes were executed.

The detector helper imports the named target module from an isolated overlay, checks that `module.__file__` is physically inside that overlay **and equals the exact declared manifest target**, hashes that exact source path, and compares it with the digest calculated by the parent runner after the mutation. A dedicated regression test supplies a deliberately wrong expected digest and requires a source-binding `ERROR`.

This is a test-harness provenance guarantee, not an authorization mechanism and not a claim about cryptographic attestation of the Python interpreter itself.

## Relationship to ordinary tests and review

Mutation assurance supplements rather than replaces normal regression tests or independent review.

The policy for future defects is:

```text
concrete review/production defect
 -> permanent regression test
 -> named guarantee
 -> curated mutation/adversarial case when the defect class is mechanically expressible
```

Repeated defect classes should therefore become harder to reintroduce. Independent review can spend more effort finding *new* invariant classes rather than rediscovering already known ones.

## Boundaries of UV-AVS-0

Included:

- curated deterministic Stage-17 mutations;
- exact detector mapping;
- isolated overlays;
- baseline-before-mutation proof;
- exact source-path/SHA binding;
- Windows/Linux execution through the existing bootstrap suite;
- machine-readable results.

Not included:

- automatic mutation enumeration across the repository;
- third-party mutation frameworks or new runtime dependencies;
- production code changes merely to make mutation tooling easier;
- fuzzing every Agent input;
- background-worker/lease/heartbeat mutants (those belong with D-066 layer 4 after the runtime exists);
- replacement of human/independent review;
- a claim that six killed mutants prove the whole Agent subsystem correct.

## Promotion rule

`stage17-curated-v1` is acceptable only when all six cases are `KILLED`, with zero `SURVIVED` and zero `ERROR`, while the permanent repository CI remains green on the exact review head.

After merge and lifecycle closure, D-066 layer 4 must preserve this suite while adding its own concurrency/recovery guarantees rather than weakening Stage-16/17 assurance implicitly.
