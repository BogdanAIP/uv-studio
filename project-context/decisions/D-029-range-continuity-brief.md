# D-029 — RangeContinuityBrief is bounded provider-neutral evidence for a targeted edit intent

Status: pending  
Date: 2026-08-12

## Decision

UV Studio stores Stage 4B continuity intelligence in a dedicated typed/versioned project document:

```text
timeline/range-continuity-briefs.json
```

There is at most one `RangeContinuityBrief` per logical `edit_id`. The brief is intentionally valid **before a replacement exists and before an `AcceptedRangeEdit` is persisted**. Its portable target identity is:

```text
edit_id
source_path
start_us
end_us
```

`replacement_path` is not part of the brief. Replacement planning, preparation/generation, review and eventual acceptance happen later.

If an accepted edit with the same `edit_id` already exists or is created later, its source/range identity must exactly match the brief. Changing only the accepted replacement file does not invalidate the continuity brief, because continuity requirements belong to the target range, not one particular take.

This ordering preserves the intended product flow:

```text
select target range
  -> build bounded continuity brief
  -> approve replacement plan/method
  -> prepare or generate replacement
  -> review in context
  -> accept replacement
  -> explicit render/export
```

## Evidence boundary

Each evidence item has a stable `evidence_id`, project-relative path and one role:

- `before`;
- `requested`;
- `after`;
- `reference`.

Source-coordinate evidence uses integer microseconds and is bounded to at most 30 seconds per item. A brief contains exactly one `requested` evidence item.

Temporal evidence is fail-closed:

- `before`, `requested` and `after` must reference the target `source_path`;
- `before` must end exactly at `start_us`;
- `requested` must exactly equal `[start_us, end_us)`;
- `after` must start exactly at `end_us`;
- a `reference` may point at another project asset/artifact/export without source coordinates;
- if a `reference` carries source coordinates, it must itself reference the target source.

These rules prevent a semantically invalid brief from labelling an unrelated asset as the actual source context or leaving an unobserved gap at an edit boundary.

Evidence and target source files must be existing regular project files when a brief is saved or explicitly project-validated. Structural load remains independent so stale state can still be inspected and repaired.

## Knowledge separation

The canonical schema separates four kinds of information instead of mixing them into one provider-specific prompt:

1. `MechanicalFact` — typed deterministic/project facts such as dimensions, stream presence or timing facts; values are string/integer/boolean, not floating pseudo-precision.
2. `ContinuityObservation` with `kind=observation` — a supported visible/audible observation.
3. `ContinuityObservation` with `kind=inference` — an interpretation or likely continuity implication that remains distinguishable from an observed fact.
4. `ContinuityConstraint` and `ReviewTarget` — explicit replacement requirements and later verification criteria.

Observations/inferences use discrete `low | medium | high` confidence and must cite at least one known evidence ID. Facts, constraints and review targets may also cite evidence IDs; unknown references fail closed.

Collection sizes are bounded in the domain model so one portable brief cannot grow without limit.

## Provider neutrality

The brief schema has no provider, model, runtime, API-key, host-path, PID, consent-token, execution-offer or replacement-runtime fields. Strict JSON/API schemas reject unknown fields.

Mechanical fact keys are additionally rejected when they attempt to encode runtime-binding concepts such as provider/model/runtime/token/host/process/offer/endpoint identity. Runtime execution provenance belongs outside this portable document.

Natural-language observations and constraints remain content, not an execution configuration surface; provider-assisted enrichment may write supported observations/inferences, but the provider/model used to produce them is not canonical brief identity.

A valid baseline brief requires no FFmpeg, VLM, MCP or remote/provider call. Future model-assisted enrichment must use the existing semantic capability and D-017 execution boundary.

## Repairability and lifecycle

Structural canonical brief state remains readable/removable if linked files later become stale.

`validate_project()` is the explicit current-health gate and fails when:

- the target source or evidence file is missing/invalid;
- an accepted edit with the same `edit_id` exists but points at another source/range.

The absence of an accepted edit is **not** a validation failure: a brief is a pre-replacement planning artifact by design. Removing/rejecting one accepted replacement therefore does not destroy reusable continuity knowledge for another take.

## Persistence and API

Brief updates/removals are serialized under the Project Store lock and written with the canonical atomic JSON primitive. The UV-owned HTTP API exposes list/get/put/delete and does not add an execution endpoint.

Portable project archives already include the canonical timeline tree and per-file SHA-256 manifest. This slice proves export -> import -> fresh ProjectStore reopen preserves a pre-replacement typed brief exactly, without requiring a replacement artifact to exist.

## Consequences

1. Stage 4 replacement planning can actually consume continuity state before a replacement is created.
2. A future VLM can enrich the same schema without owning the project model.
3. Mechanical facts, observations and inferences remain distinguishable for later review/audit.
4. Exact target source/range identity survives across plan, generation, review and acceptance gates.
5. Multiple replacement takes can reuse the same valid continuity brief when the target range is unchanged.
6. Stage 4C can present evidence and constraints independently of whichever implementation created them.
7. Provider-specific prompt compilation remains an adapter/runtime concern rather than canonical state.

## Acceptance evidence required

Before D-029 becomes accepted, final PR #26 review head must pass all five Ubuntu/Windows checks and prove:

- strict typed round-trip of a full brief;
- creation before any replacement/accepted edit exists;
- later matching accepted edit remains compatible while replacement-only changes do not invalidate the brief;
- a conflicting accepted source/range fails validation;
- exactly one requested evidence item;
- source-bound adjacent before/requested/after evidence intervals;
- bounded evidence windows and bounded collection counts;
- observations/inferences with explicit confidence and known evidence links;
- provider/runtime unknown fields and runtime-binding mechanical fact keys rejected;
- no media artifact or execution side effect from brief persistence;
- stale-file repairability plus explicit validation failure;
- archive/import/fresh reopen exactness before replacement;
- HTTP list/get/put/delete and 404/422 boundaries;
- existing real-media, security, lint, high-severity audit and production-build gates remain green.
