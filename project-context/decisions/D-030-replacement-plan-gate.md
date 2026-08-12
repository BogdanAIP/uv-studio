# D-030 — Replacement preparation requires an explicit provider-neutral approved plan

Status: pending  
Date: 2026-08-12

## Decision

UV Studio stores one canonical approved replacement plan per logical targeted `edit_id` in:

```text
timeline/replacement-plans.json
```

Saving this document is the **plan approval gate**. Draft UI/form state is not canonical project state in this slice.

A caller proposes only the semantic preparation strategy. UV Studio itself loads and validates the current D-029 `RangeContinuityBrief`, then copies exact target identity and computes the Brief binding. The caller does not provide or override canonical target coordinates or the Brief digest.

Canonical plan target identity is:

```text
edit_id
source_path
start_us
end_us
```

and is inherited exactly from the current Brief.

## Brief revision binding

The plan stores `brief_sha256`, computed by UV Studio over canonical sorted JSON serialization of the complete `RangeContinuityBrief`.

This means a change to evidence, observations/inferences, constraints, review targets or target identity makes an already approved plan stale. UV Studio does not silently migrate the approval to the new Brief; explicit reapproval is required.

The plan also carries the current Brief constraint IDs and review-target IDs for direct traceability. They are derived by the store rather than caller-supplied during approval.

## Approved method classes

Portable plan state chooses only one semantic method class:

- `deterministic_edit` — local/deterministic media preparation where suitable;
- `prepared_asset` — use/prepare an existing project-scoped asset without provider generation;
- `generative_transform` — optional generated replacement path.

These are product semantics, not provider implementations. Provider/model/offer/runtime identity is not part of the plan.

Runtime preparation in a later slice must implement the approved method class and may not silently substitute another class. A generative runtime, if used, remains behind Capability Registry selection and D-017 authorization.

## Change and audio scope

The proposal persists bounded:

- `goal`;
- `required_changes` (at least one);
- `allowed_changes`;
- `forbidden_changes`;
- `audio_strategy` (`preserve_source` or `replacement_audio`).

The three change lists are duplicate-free, pairwise disjoint and bounded in count/text length. They describe approved semantic changes, not raw tool/provider arguments.

## Sample-first rule

`sample_policy` is derived by UV Studio and cannot be chosen independently by the caller:

- `generative_transform` -> `required_before_full_generation`;
- deterministic/prepared methods -> `not_required`.

A future preparation executor must refuse full generative replacement creation until the sample-first condition recorded by the approved plan is satisfied.

## Lifecycle

A valid approved plan requires a **current valid RangeContinuityBrief**, but it does not require replacement media or an `AcceptedRangeEdit`.

The intended lifecycle is:

```text
target range
  -> validated RangeContinuityBrief
  -> approved ReplacementPlan
  -> candidate preparation / optional generation
  -> independent evidence-based review
  -> accepted replacement decision
  -> explicit render/export
```

Plan approval itself performs no FFmpeg, VLM, MCP, provider or media-generation execution and creates no replacement artifact.

Structural plan state remains readable/removable after its Brief becomes stale or missing. `validate_project()` is the explicit current-health gate and fails when the bound Brief is unavailable, invalid, changed, or no longer matches the plan target/traceability snapshot.

## Provider neutrality

Strict domain/API schemas reject unknown fields, so provider/model/offer/runtime/credential fields have no structured canonical home in the plan.

Natural-language `goal` and change descriptions are semantic content, not an execution configuration surface. Exact runtime/provider selection and external authorization stay in execution preparation/provenance outside canonical plan state.

## Consequences

1. Replacement generation/preparation cannot begin as an unreviewed implicit method choice.
2. A changed continuity brief invalidates old approval instead of silently inheriting it.
3. Deterministic and prepared local paths remain first-class peers to generation.
4. Generative replacement explicitly carries a sample-first obligation before full generation.
5. The next preparation slice can select exact implementations while respecting D-017 and the approved method class.
6. Candidate creation remains separate from final `AcceptedRangeEdit` acceptance.

## Acceptance evidence required

Before D-030 becomes accepted, final PR #27 review head must pass all required Ubuntu/Windows checks and prove:

- exact target identity is inherited from a validated Brief, not caller supplied;
- canonical Brief SHA-256 is server-computed and stable across archive/fresh reopen;
- changed Brief content makes an existing plan stale but structurally repairable;
- explicit reapproval after a Brief change refreshes digest and traceability;
- method/audio/change-scope validation is strict and bounded;
- generative method always derives mandatory sample-first policy;
- provider/runtime unknown fields and invalid method classes are rejected;
- approval works before replacement media/AcceptedRangeEdit exists and creates no artifacts/execution side effects;
- archive/import/fresh reopen preserves the approved plan exactly;
- HTTP list/get/put/delete and 404/422 boundaries are proven;
- existing Stage 4A/D-028 real-media regressions, security gates, frontend lint, high-severity audit and production build remain green.
