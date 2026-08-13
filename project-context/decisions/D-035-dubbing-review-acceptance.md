# D-035 — Dubbing review and acceptance boundary

**Status:** Accepted

**Date:** 2026-08-13

## Context

Stage 5 now has canonical transcript/translation revisions and project-owned prepared speech takes. A speech file must not become an accepted timeline edit merely because transcription/TTS/import or FFmpeg completed successfully.

The acceptance boundary must detect stale script/audio revisions and must combine machine-measurable evidence with explicit human confirmation where UV Studio cannot yet prove semantic fidelity automatically.

## Decision

Introduce a typed/versioned `DubbingReview` followed by an immutable `AcceptedDubbingEdit`.

A review binds the exact current:

- dubbing transcript revision;
- optional translation revision;
- prepared speech take revision;
- prepared audio SHA-256;
- target source/range;
- measured audio duration;
- local FFmpeg loudness/true-peak evidence.

The review contains two machine assessments:

1. **timing** — prepared speech must fit its target range without hidden retiming; it may end early, but may exceed the target by at most 100 ms;
2. **audio safety** — loudness must be measurable and true peak must be at or below -1.0 dBTP.

Integrated LUFS and LRA are recorded as evidence but are not yet forced to one delivery target; final delivery loudness belongs to an explicit export profile rather than being silently baked into editing.

For `approved`, both machine assessments must pass and the reviewer must explicitly confirm:

- spoken/script content fidelity;
- perceptual synchronization/placement.

A review may still be `needs_revision` or `rejected` even when machine checks pass.

## Acceptance

Only a current `approved` review may create an `AcceptedDubbingEdit`.

Acceptance revalidates the exact current script, prepared take and audio revisions under the Project Store lock. It stores only portable IDs, hashes, integer-microsecond target timing and an explicit audio composition policy.

No caller may supply or override revision hashes, host paths, FFmpeg filters, loudness measurements or acceptance target timing.

## Initial audio composition policy

Stage 5 acceptance records the policy separately from the speech asset. The first deterministic renderer may support only policies it can prove safely. Unsupported policies must fail closed rather than silently mix or delete source audio.

Professional preservation of background/ambience should reuse a mature separation/dialogue-isolation component if required; it must not be approximated with an unreviewed home-grown separator.

## Consequences

- ASR/TTS/import success is not acceptance.
- Editing text after voice preparation invalidates the dependent path before review/acceptance.
- Editing/replacing audio bytes invalidates review/acceptance.
- Loudness evidence is generated server-side from the exact registered audio.
- Human semantic/sync confirmation remains explicit until a separately accepted automated review capability exists.
- Final render can consume only accepted dubbing state, not arbitrary audio uploads.
