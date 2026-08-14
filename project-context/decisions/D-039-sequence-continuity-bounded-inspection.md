# D-039 — Optional sequence continuity uses explicit accepted anchors and derived bounded inspection context

Status: accepted  
Date: 2026-08-14

## Decision

Stage 6 sequence continuity is opt-in project state. A project with independent clips does not acquire sequence records, anchor semantics, continuity locks or take-review state merely because the editor is opened.

When continuity is enabled, UV Studio owns a typed/versioned provider-neutral sequence model under the canonical project timeline. The model separates:

1. **planned continuity** for a shot: intent, exact accepted anchor identity when one exists, locked traits, explicitly allowed changes and review targets;
2. **observed continuity** for a concrete take: supported observations/inferences about what the accepted media actually contains;
3. **take lifecycle**: prepared, accepted or rejected, bound to exact project-owned artifact bytes and the exact plan revision it was produced/reviewed against;
4. **re-anchor state**: an explicit command that selects one accepted observed take as the anchor for later linked shots.

Planned and observed state are never collapsed into one free-form prompt. A later shot must not silently infer its anchor from file order, timestamps, newest-take sorting or whichever model produced the media.

## Take and anchor identity

A sequence take is bound server-side to a project-owned media reference and current SHA-256/size identity. Acceptance revalidates the exact media bytes and the exact current shot plan/review binding. Rejected or stale takes cannot become anchors.

Re-anchor is explicit. A re-anchor operation names an accepted take and updates the sequence anchor only after current-byte and current-state validation. Changing an earlier plan or mutating take bytes invalidates downstream operations that claim the old binding; historical state remains inspectable rather than being silently rewritten.

## Bounded TimelineContext

Stage 6 adopts the useful `browser-use/video-use` idea of reasoning from compact structured state plus visual drill-down only at decision points, but not its session/project authority.

UV Studio exposes a **derived bounded TimelineContext** for an anchor/candidate boundary. It may include exact artifact identity, bounded source/output time windows, sampled frame timestamps, deterministic media facts and relevant transcript/audio/timeline facts where available. Visual frames are generated on demand from the exact registered project media.

TimelineContext is not canonical project state and is not persisted as a second timeline, EDL or chat-memory file. Canonical inputs remain Project Store/domain records. This prevents `project.md`, `takes_packed.md`, `edl.json` or an external agent workspace from becoming a competing authority.

## Rendered-output evidence and review

Review must be capable of inspecting the actual produced take, not only the prompt or plan. Local deterministic inspection may provide sampled frames, media facts and bounded boundary context. Optional VLM assistance can enrich review through the existing Capability Registry and D-017 authorization boundary.

Model/provider/runtime identity is execution provenance, not portable continuity identity. A complete manual/human review path remains valid when no VLM is configured or automated evidence is uncertain.

Review verdicts remain evidence-based and bind the exact current plan, anchor and candidate-take bytes. An approved current review is required before a prepared take becomes accepted.

## Reuse-first evaluation

### `browser-use/video-use`

Evaluated at upstream commit `92c2b34e44c205cbc2acae7f6ca7c1c219d5dd66` (MIT).

Useful concepts adopted architecturally:

- compact structured reasoning instead of frame dumping;
- on-demand filmstrip/timeline inspection around ambiguous boundaries;
- deterministic EDL/render separation as a general pattern already aligned with UV semantic commands;
- self-evaluation of the rendered output before presenting/accepting it.

Direct integration is rejected for Stage 6 because its `project.md`/`takes_packed.md`/`edl.json` session files would duplicate UV canonical state, transcription is directly coupled to ElevenLabs Scribe, and its FFmpeg editing rules are specialized policy rather than universal UV editor invariants. No `video-use` code is copied and it is not a runtime dependency.

### PySceneDetect

PySceneDetect 0.7.x (BSD-3-Clause) is a credible maintained component for deterministic shot/transition detection, including VFR-aware processing. It is not added to the Stage 6 baseline because linked-shot continuity operates on explicit project/take boundaries and does not require automatic scene segmentation to satisfy the user outcome. If later workflows need automatic boundary discovery, PySceneDetect is the preferred first spike rather than a custom detector.

## Capability boundary

Optional generation, VLM understanding and model-assisted review reuse semantic Capability Registry offers and existing authorization semantics. Stage 6 does not create a privileged provider API or a second execution framework.

GUI, scripts, AI and MCP automation must converge on UV-owned sequence commands for plan creation, take registration/review/acceptance and re-anchor. Direct canonical JSON mutation is not an automation API.

## Consequences

1. Standalone clips remain simple and carry no sequence overhead.
2. Connected shots have explicit, auditable planned-versus-observed continuity.
3. An accepted take, not a model prompt, becomes the factual anchor for the next shot.
4. Bounded visual context is cheap and decision-oriented without frame dumping or a second project authority.
5. Automated review can improve evidence quality without making a VLM or paid API mandatory.
6. Existing D-029 continuity evidence concepts can be reused where their semantics fit, while range-edit and linked-shot state remain distinct domains.
7. Future music-video continuity can compose this optional Stage 6 layer instead of inventing another take ledger.
