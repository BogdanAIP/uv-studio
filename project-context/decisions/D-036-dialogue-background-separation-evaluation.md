# D-036 — Dialogue/background separation evaluation gate

**Status:** Proposed

**Date:** 2026-08-13

## Context

Professional dubbing should preserve music, ambience and effects when the original dialogue is replaced. Simply muting or replacing the complete source mix in the dialogue interval is deterministic but is not a professional preservation strategy.

Reuse-first research found that the original Meta Demucs repository is archived, so it should not become a new primary UV Studio dependency solely because it is well known. Current reusable candidates include:

- `nomadkaraoke/python-audio-separator` — MIT, maintained CLI/Python wrapper over multiple UVR-family architectures including MDX, Demucs and RoFormer models;
- `modelscope/ClearerVoice-Studio` — Apache-2.0, maintained speech enhancement/separation toolkit aimed at speech restoration/separation tasks.

The available model families solve related but not identical problems. Music vocal separation is not automatically equivalent to film/UGC dialogue isolation, and speech enhancement can remove background rather than reconstruct a clean background stem.

## Proposed evaluation

Do not advertise `replace_dialogue_preserve_background` as executable until a real-media fixture proves it.

Evaluate at least:

1. mixed dialogue + music;
2. dialogue + ambience/noise;
3. dialogue + transient effects;
4. stereo source where background spatial character matters;
5. overlapping speech where a single dialogue stem may be insufficient.

For each candidate, retain exact upstream/model/version/license provenance and measure:

- dialogue leakage left in the background stem;
- background loss/warbling around speech;
- transient damage;
- stereo image change;
- CPU/GPU/runtime footprint on ordinary Windows hardware;
- deterministic/repeatable invocation and bounded adapter surface.

The test must compare actual rendered stems/media, not merely successful process exit or model self-report.

## Integration boundary

If a candidate passes, expose it as semantic capability `audio.separate_dialogue` (or a more precise capability if the proven contract is narrower).

Canonical project state stores only project-owned input/output asset IDs, hashes and accepted semantic policy. Model path, checkpoint identity, raw CLI arguments and temporary files remain runtime/adapter state.

A separation result is a candidate artifact, not accepted dubbing state. It must still flow through the Stage 5 review/acceptance boundary.

## Current consequence

`replace_source_audio_range` may be implemented as an explicit deterministic fallback because its semantics are honest and testable.

`replace_dialogue_preserve_background` and any automatic ducking/separation policy must fail closed until their concrete adapter and real-media evidence are accepted. No home-grown separator should be introduced while mature open-source candidates remain unevaluated.
