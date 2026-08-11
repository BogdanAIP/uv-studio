# Next Task

<!-- uv-next-slice: stage-4-range-continuity-brief -->

Updated: 2026-08-11

## Gate first

PR #19 — **deterministic exact range reinsertion foundation** — was independently audited and merged to `main` as `f9d850d6fb2ea5fbd84d071752139e151d494ea4` after its exact final head passed the complete Linux/Windows matrix.

Do not start the product slice until the active agent-development guardrail slice in `ACTIVE_SLICE.json` has:

- one coordinator-owned final head;
- the `development-context` contract green;
- Ubuntu and Windows bootstrap/unit green;
- Ubuntu and Windows API + real HTTP smoke + frontend build green;
- no unresolved review threads;
- D-023 accepted;
- merge to `main` confirmed.

If that process slice is not merged, continue/fix it rather than opening a parallel Stage 4 branch.

## Primary target after PR #19

Build the first provider-neutral **range continuity / replacement brief** layer.

The product already has the mechanical boundaries:

```text
ProjectMediaRange
  -> exact requested interval

video.extract_range
  -> context_before
  -> requested clip
  -> context_after

video.replace_range
  -> deterministic reinsertion of a prepared replacement
```

The next missing piece is to describe **what a replacement must preserve** before any particular VLM/video generator is selected.

The next slice should therefore produce a portable structured brief from the exact range + nearby context rather than jumping directly to a provider-specific generation pipeline.

## Required product contract

Introduce a small versioned provider-neutral model, expected conceptually as:

```text
RangeContinuityBrief
  -> exact ProjectMediaRange identity
  -> context artifact references
  -> source technical facts
  -> continuity observations
  -> replacement constraints
  -> review/check requirements
```

Do not put provider/model/runtime IDs in the portable brief.

The brief must be useful both to:

- a later generative adapter constructing a replacement request;
- a later review adapter comparing generated replacement with source context.

## Separate evidence from interpretation

Keep concrete evidence distinct from model conclusions.

Example structure:

```text
evidence
  -> source/context project paths
  -> exact start/end microseconds
  -> technical probe facts
  -> sampled frame/time references when created

observations
  -> scene/subject/action/camera/lighting/audio continuity facts

constraints
  -> what must remain consistent across the replacement

review_targets
  -> what a later validator must compare
```

A provider response should never overwrite or redefine the original requested range.

## Context should stay bounded

Reuse D-021 context rather than analyzing the whole source by default.

The first continuity path should consume only the requested range and bounded context necessary for the edit. Whole-video analysis must be an explicit separate decision when genuinely needed.

This keeps 5–10 second edits from turning into mandatory analysis of a 30-minute file.

## Provider-neutral semantic capability

Decide the clean semantic capability boundary before implementing an adapter. A likely shape is one of:

```text
video.range_understand
media.range_understand
```

or a composition of the existing provider-neutral `media.understand` capability with the range-context model.

Choose the smallest contract that avoids duplicating the Capability Registry.

Do not create `qwen.*`, `gpt.*`, `gemini.*`, `videoclaw.*` or similar semantic capability IDs.

## Execution policy

The portable brief/model must exist independently of any one provider.

If a concrete analysis adapter is added in this slice:

- local/free remains preferred when a real tested local implementation exists;
- remote execution must pass D-017;
- potentially-paid execution must expose cost/unknown-cost consent as already defined;
- no local failure may silently widen into remote/paid execution;
- exact input project-file contracts must be explicit for MCP adapters.

Do not mark an analysis offer `AVAILABLE` until its execution transport and file contract are real.

## Structured observations

The first useful continuity schema should cover at least fields needed for seamless short-scene replacement, without forcing every field to exist:

```text
scene / environment
subjects / visible identity cues
subject position and scale
pose / motion direction
camera framing
camera motion
depth / perspective
lighting direction and intensity cues
color / exposure continuity
objects entering/leaving the range
start-boundary state
end-boundary state
audio/speech/music state when relevant
```

Observations should support confidence/evidence references rather than pretending uncertain model output is ground truth.

## Replacement constraints

Derive a provider-neutral replacement brief containing explicit constraints such as:

```text
required duration / tolerance
required resolution / media format contract
start-boundary continuity
end-boundary continuity
camera/subject continuity
whether source audio must be retained/replaced
forbidden unintended changes
```

Mechanical duration/media constraints should come from D-021/D-022 facts, not be invented by an LLM/VLM.

## No direct generation yet unless the brief contract is complete

Do not add a video generator merely to demonstrate the flow.

Generation may begin only after the portable brief can be created, stored, exported/imported and passed to a provider without losing the exact range identity or mechanical constraints.

If time remains in the same PR after the brief is complete and tested, generation integration should still be a separate adapter path over existing `video.generate`/transformation semantics, not part of the brief model itself.

## Tests required

At minimum prove:

1. exact `ProjectMediaRange` survives brief serialization unchanged;
2. all file references remain canonical project-relative paths;
3. host paths/provider credentials/tokens cannot enter portable brief state;
4. context references cannot escape approved project roots;
5. technical duration/resolution constraints are derived from project/probe facts rather than model prose;
6. model observations can be absent/partial without corrupting mechanical constraints;
7. uncertain observations have explicit confidence/evidence representation;
8. provider/model IDs are not required by the portable schema;
9. archive/export round-trip preserves the brief;
10. any remote adapter path remains behind D-017 authorization;
11. API tests cover creation/read/update or task output as appropriate;
12. Ubuntu/Windows unit/API/frontend matrix stays green.

## Explicit non-goals for the first continuity slice

Do not add yet:

- automatic full-video analysis by default;
- automatic scene generation before the brief exists;
- provider-specific prompt fields in canonical project schema;
- automatic replacement retiming hidden inside analysis;
- final delivery/export codec policy;
- timeline UI editor;
- dubbing/music-specific workflow.

The continuity/brief layer should make later generation/review swappable while keeping exact D-021/D-022 mechanics stable.
