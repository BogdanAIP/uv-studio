# Next Task

<!-- uv-next-slice: post-roadmap-release-maintenance -->

## Goal

After Stage 9 Desktop Productization & Release Hardening is reviewed, merged and closed to a green idle lifecycle, transition UV Studio from roadmap implementation to release maintenance and explicitly scoped follow-up development.

## Required direction

- treat the Stage 9 packaged Windows release and its project/archive compatibility contract as the maintained product baseline;
- triage real release feedback, crashes, security findings, dependency/toolchain advisories and hardware/codec compatibility issues into bounded fix/chore/research slices;
- preserve project migration, backup/recovery and release-manifest compatibility across maintenance releases;
- keep installer/update/signing provenance and third-party notices current;
- require explicit architecture decisions before adding new universal engines, mandatory cloud dependencies or provider-specific canonical state;
- continue permanent packaged-app and user-outcome regressions for every release-affecting change;
- add future product capabilities only as separately scoped slices with their own evidence and lifecycle.

## Preserved future capability: UV Character Asset

Do not lose the post-Stage-9 character-consistency direction recorded in `docs/uv-character-asset-design.md`.

The intended architecture is a provider-neutral portable `.uvcharacter` whose canonical truth is source references + human-authored character description, while face/subject embeddings, crops, FLUX/video conditioning payloads, LoRA coordinates, scores and continuity summaries are versioned rebuildable caches.

This capability must be designed for **both image and video generation from the first format version**:

- image native multi-reference conditioning without mandatory per-character training;
- optional trained adapters/LoRAs as replaceable provider payloads, never identity truth;
- local face/whole-subject identity evaluation and candidate ranking;
- video still/keyframe/motion/pose conditioning behind provider-neutral capabilities;
- sampled-frame identity evaluation, intra-shot temporal drift and previous-shot continuity;
- scene/shot appearance-state overlays so outfit/hair/story changes do not overwrite base character identity;
- cross-project portability, provenance, privacy and no silent remote upload of biometric-like references/embeddings.

Inline Studio is useful architectural research for this idea, but its GPL implementation must not be copied into the UV Studio MIT codebase. Reimplement the concept behind UV-owned Project Store and semantic capability boundaries.

Implementation starts only after Stage 9 is merged and idle, beginning with a dedicated architecture decision for the concrete Character Asset format and capability contracts.

## Completion proof

This handoff is entered only after Stage 9 is merged, the repository returns to `idle`, and the exact post-merge idle `main` passes all permanent required checks. Subsequent maintenance or feature work must start from that verified baseline under the normal one-active-slice protocol.

## Entry gate

Do not start post-roadmap release maintenance while `stage-9-desktop-productization-release-hardening` is still draft/review, unmerged, not atomically closed to `idle`, or has a failing post-merge required check.
