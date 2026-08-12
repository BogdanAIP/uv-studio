# D-031 — Replacement preparation creates reviewable candidates, never accepted edits

Status: pending  
Date: 2026-08-12

## Decision

Stage 4B replacement preparation produces project-owned **candidate artifacts** bound to a currently valid D-030 `ReplacementPlan`. Preparation success does not create or modify `timeline/range-edits.json`.

Canonical candidate state lives in:

```text
timeline/replacement-candidates.json
```

Each `ReplacementCandidate` stores portable state only:

```text
candidate_id
edit_id
source_path
start_us
end_us
plan_sha256
method_class
stage
artifact_id
artifact_path
execution_run_id?   # portable task-record identifier, not provider identity
```

The exact target and method class are inherited from the current approved plan. `plan_sha256` is computed by UV Studio from canonical plan JSON. Any later plan/Brief revision makes an old candidate stale until a new candidate is prepared under the current approval.

The candidate artifact must be an existing non-empty regular UV Studio project artifact under `artifacts/` and must match the registered ProjectReference id/path. Candidate state never stores an arbitrary host path.

## Method-class enforcement

Preparation must not silently switch the method class approved in D-030.

### `prepared_asset`

A project-relative existing file under the allowed project roots may be copied into a new UV Studio-owned candidate artifact. Host paths are never accepted. The source is not itself treated as the candidate; preparation creates a distinct project artifact so later review/history is stable.

### `deterministic_edit`

Capability-based deterministic preparation is restricted to:

- deterministic-media or assembly semantic capability;
- selected offer `local + free`;
- video output;
- full candidate stage only.

This prevents an approved deterministic plan from silently widening into remote/non-free generation.

### `generative_transform`

Generation/transformation remains optional and must use the existing semantic Capability Registry, selection policy and D-017 authorization path. The candidate-preparation API delegates to the existing generic prepare/authorize/execute functions; it does not implement a parallel consent system.

Runtime offer/provider/model identity remains in execution provenance, not candidate state.

## Sample-first gate

Generative preparation has two candidate stages:

```text
sample
full
```

Only generative candidates may use `sample`. A `full` generative candidate is blocked before authorization/execution unless a current generative sample candidate for the same `edit_id + plan_sha256` has been explicitly approved.

Sample approval is portable state:

```text
edit_id
candidate_id
plan_sha256
```

Changing/reapproving the plan invalidates the prior sample approval for full-generation purposes. This prevents a sample approved under old continuity/method constraints from authorizing a new full generation.

## External MCP output ownership

D-019 already made project-file **inputs** binding-owned. Candidate generation requires the symmetric output rule: an MCP tool may not nominate an arbitrary output host path in its JSON response.

`MCPToolBinding` may declare explicit `project_file_outputs` entries containing only:

```text
argument_name
media_kind
suffix
required
```

For each declared output UV Studio:

1. rejects any caller-supplied value for that argument;
2. allocates a fresh `artifacts/art_<uuid>.<suffix>` destination under Project Store;
3. injects the absolute host path only into the short-lived MCP invocation after authorization/provenance input binding;
4. requires the returned invocation to have produced a regular non-symlink non-empty file at that exact allocated path;
5. re-resolves the path under the canonical project boundary;
6. only then registers a ProjectReference;
7. rolls back files and registered references if output validation or execution completion fails.

The injected absolute path is runtime-only and is not part of portable authorization input, project state or candidate state.

Malformed/missing required MCP outputs use the existing MCP gateway error boundary rather than surfacing as an unclassified server error.

Tools that only return an arbitrary URL/path in untrusted JSON are **not** considered artifact-producing candidate adapters. They require a future explicit trusted download/import adapter rather than path trust.

## Candidate provenance

ProjectReference metadata for external outputs contains only portable non-secret linkage such as capability ID and run ID. Provider/profile/tool/runtime IDs are not copied into candidate state. The task record remains the detailed non-secret execution provenance record.

Candidate removal removes candidate/sample-approval state but intentionally does not delete the artifact; generated/prepared media remains project history until an explicit cleanup policy exists.

## Review boundary

The following Stage 4B review gate is mandatory. It will consume a current candidate plus its current Plan/Brief and persist an explicit verdict (`approved`, `rejected`, or `needs_revision`). Only a current reviewed-approved candidate may later become an `AcceptedRangeEdit`.

## Consequences

1. Preparation cannot bypass plan approval or silently accept its own output.
2. Generative full execution cannot consume money before the sample-first gate is satisfied for the current plan revision.
3. External generators write only to UV-owned allocated output paths.
4. Candidate state stays provider-neutral and archive-portable while detailed execution remains traceable by run ID.
5. Prepared/local deterministic workflows remain first-class and do not require a cloud provider.
6. Review/rejection/history remain possible without mutating the original source or accepted edit state.

## Acceptance evidence required

Before D-031 becomes accepted, final PR #28 review head must pass all required Ubuntu/Windows checks and prove:

- prepared project asset becomes a distinct project candidate artifact without creating an accepted edit;
- candidate exact target/method/digest are inherited from a current plan;
- missing/empty/unregistered candidate artifact is rejected;
- a plan/Brief revision makes prior candidate/sample approval stale but structurally inspectable;
- full generative candidate is blocked before authorization/execution until a current sample is approved;
- a real remote/potentially-paid MCP `video.generate` fixture performs `sample -> explicit sample approval -> full` through D-017 one-shot tokens;
- replayed authorization token remains invalid;
- binding-owned MCP output argument cannot be caller supplied;
- missing/empty MCP output is rolled back and maps through the gateway error boundary;
- generated MCP output becomes a project-owned registered artifact without host paths/provider identity in portable project state;
- prepared-asset real-media candidate remains a valid video and byte-preserves the prepared project clip;
- candidate/archive/fresh reopen preserves candidate state and artifact without creating accepted edit state;
- existing Stage 4A/D-028 real-media regressions, security gates, frontend lint, high-severity audit and production build remain green.
