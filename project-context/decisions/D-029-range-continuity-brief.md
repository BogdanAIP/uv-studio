# D-029 — RangeContinuityBrief is bounded provider-neutral evidence attached to one accepted edit

Status: pending  
Date: 2026-08-12

## Decision

UV Studio stores Stage 4B continuity intelligence in a dedicated typed/versioned project document:

```text
timeline/range-continuity-briefs.json
```

There is at most one `RangeContinuityBrief` per accepted `edit_id`. The brief snapshots the complete D-028 edit identity:

```text
edit_id
source_path
start_us
end_us
replacement_path
```

A brief is current only while that complete identity exactly matches the accepted edit decision. Reusing an `edit_id` with another source, interval or replacement does not inherit old continuity state.

## Evidence boundary

Each evidence item has a stable `evidence_id`, project-relative path and one role:

- `before`;
- `requested`;
- `after`;
- `reference`.

Source-coordinate evidence is integer-microsecond based and bounded to at most 30 seconds per item.

Role rules are fail-closed:

- `before` may end at the target start but may not enter the requested interval;
- `requested` must exactly equal the accepted edit interval;
- `after` may start at the target end but may not enter the requested interval;
- `reference` may be a project asset/artifact/export without source coordinates.

Evidence files must be existing regular project files when a brief is saved or explicitly project-validated.

## Knowledge separation

The canonical schema separates four different kinds of information instead of mixing them into one free-form prompt:

1. `MechanicalFact` — typed deterministic/project facts such as dimensions, stream presence or timing facts; values are string/integer/boolean, not floating pseudo-precision.
2. `ContinuityObservation` with `kind=observation` — a supported visible/audible observation.
3. `ContinuityObservation` with `kind=inference` — an interpretation or likely continuity implication that must remain distinguishable from an observed fact.
4. `ContinuityConstraint` and `ReviewTarget` — explicit replacement requirements and later verification criteria.

Observations/inferences use discrete `low | medium | high` confidence and must cite at least one known evidence ID. Facts, constraints and review targets may also cite evidence IDs; unknown evidence references fail closed.

## Provider neutrality

The brief schema has no provider, model, runtime, API-key, host-path, PID, consent-token or execution-offer fields. Strict JSON/API schemas reject unknown fields rather than preserving provider metadata in an extension blob.

A valid baseline brief can be created from existing project evidence with no FFmpeg, VLM, MCP or remote/provider call. Future model-assisted enrichment may produce observations/inferences only through the existing semantic capability and D-017 execution boundary; execution provenance remains outside the portable brief.

## Repairability

Like D-028 edit state, structural canonical brief state remains readable/removable if linked media or the accepted edit later becomes stale. `validate_project()` is the explicit current-health gate and fails if:

- the target edit no longer exists or its complete identity changed;
- an evidence file is missing/invalid.

This prevents a stale project condition from making its own continuity state impossible to inspect or delete.

## Persistence and API

Brief updates/removals are serialized under the Project Store lock and written with the canonical atomic JSON primitive. The UV-owned HTTP API exposes list/get/put/delete without adding any execution endpoint.

Portable project archives already include the canonical timeline tree and per-file SHA-256 manifest. This slice proves export -> import -> fresh ProjectStore reopen preserves the typed brief exactly.

## Consequences

1. Stage 4 replacement planning can consume bounded structured continuity state instead of a provider-specific prompt string.
2. A future VLM can enrich the same schema without owning the project model.
3. Mechanical facts, observations and inferences remain distinguishable for later review/audit.
4. Exact accepted edit identity remains the anchor across plan, generation and review gates.
5. Stage 4C can present evidence and constraints independently of whichever implementation created them.
6. Richer provider-specific prompt compilation becomes an adapter/runtime concern rather than canonical state.

## Acceptance evidence required

Before D-029 becomes accepted, final PR #26 review head must pass all five Ubuntu/Windows checks and prove:

- strict typed round-trip of a full brief;
- bounded and role-consistent evidence intervals;
- exact accepted edit identity including replacement path;
- observations/inferences with explicit confidence and known evidence links;
- provider/runtime unknown fields rejected;
- no media artifact or execution side effect from brief persistence;
- stale target repairability plus explicit validation failure;
- archive/import/fresh reopen exactness;
- HTTP list/get/put/delete and 404/422 boundaries;
- existing real-media, security, lint, high-severity audit and production-build gates remain green.
