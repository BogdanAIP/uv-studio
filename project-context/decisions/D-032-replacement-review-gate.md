# D-032 — Accepted replacement edits require an exact current approved review

Status: provisional  
Date: 2026-08-12

## Decision

Stage 4B introduces a project-owned replacement review gate between D-031 `ReplacementCandidate` preparation and D-028 `AcceptedRangeEdit` creation.

Canonical replacement review state lives under the project `reviews/` root. Review state is portable domain state: it binds an exact current candidate and approved-plan revision, records evidence-based observations/inferences and one assessment per current Brief review target, and stores only an optional portable execution run identifier for model-assisted provenance. Provider/model/profile/runtime identity and authorization tokens are never review fields.

A final review verdict is one of:

```text
approved
rejected
needs_revision
```

Only a current `full` candidate may receive a final replacement review. Sample approval remains a D-031 preparation gate and is not a final replacement review.

## Review binding

UV Studio computes and persists candidate/plan/target bindings server-side. A client may nominate a current candidate and submit review evidence, but it cannot supply canonical source/range/replacement paths for acceptance.

The review must remain valid only while all of the following are still current:

- candidate ID and canonical candidate digest;
- candidate exact target identity;
- candidate approved-plan digest;
- current `RangeContinuityBrief` for the same target;
- the complete current Brief review-target set.

Any candidate, Plan or Brief revision makes an older review structurally inspectable history but invalid for new acceptance.

## Evidence and criteria

Mechanical validity and review judgment are separate concerns.

Before review registration, `ReplacementCandidateStore.validate_candidate()` proves the candidate is mechanically current and project-owned. Review observations then represent either `observation` or `inference`, carry explicit confidence, and cite bounded evidence IDs. Review evidence may cite current Brief evidence and the exact candidate artifact ID; arbitrary host paths are not evidence identifiers.

Every current Brief `ReviewTarget` must have exactly one assessment. Assessments use:

```text
pass
fail
uncertain
```

An `approved` review requires every required review target to pass. `rejected` requires at least one failed target. `needs_revision` requires at least one failed or uncertain target. This keeps the verdict mechanically consistent with the persisted target assessments.

## Acceptance boundary

The existing caller-controlled HTTP create-edit route is not a valid Stage 4B acceptance gate because it lets a client nominate `source_path`, range and `replacement_path` directly. This slice removes that product bypass.

New accepted edit creation takes only an approved review identity. Under the project lock UV Studio revalidates the review, exact candidate, current Plan/Brief and candidate artifact, then constructs `AcceptedRangeEdit` from the candidate's own exact source/range/artifact path and delegates persistence to the existing D-028 `RangeEditStateStore`.

`RangeEditStateStore.accept()` remains an internal low-level persistence primitive. Public HTTP read/remove operations remain available; a new edit must enter through the approved review gate.

## Model-assisted review

Model assistance is optional, not canonical. Existing `media.understand` capability execution already provides semantic selection and D-017 authorization for remote/non-free analysis. A review may carry a portable execution run reference when observations were informed by such a run, but the review schema does not depend on a provider or require automated analysis. Manual/local evidence entry remains a complete baseline path.

## Consequences

1. Candidate preparation can no longer self-accept or be bypassed by caller-supplied replacement paths.
2. Review and acceptance are revision-bound and fail closed after Candidate/Plan/Brief changes.
3. Rejected and needs-revision outcomes remain durable project history.
4. Provider choice remains execution provenance rather than portable review state.
5. Stage 4C can build UI on a complete domain chain with a single safe acceptance path.

## Acceptance evidence required

Before D-032 becomes accepted, the final review head must prove:

- final reviews reject sample/stale/missing candidates;
- criteria exactly trace the current Brief review targets;
- observation/inference evidence references are bounded and valid;
- approved/rejected/needs-revision verdict consistency is enforced;
- archive/fresh reopen preserves review history;
- changed Brief/Plan/Candidate invalidates old approval for acceptance without deleting history;
- public caller-controlled edit creation cannot bypass review;
- accepting an approved review writes the exact reviewed candidate artifact/range and cannot accept rejected/needs-revision reviews;
- overlap/reference validation from D-028 still applies;
- a real-media prepared candidate can be reviewed/accepted without mutating the original source and remains renderable by the existing one-pass edit renderer;
- all existing Ubuntu/Windows unit/API/real-media/frontend/security gates remain green.
