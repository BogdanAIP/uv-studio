# Next Task

<!-- uv-next-slice: product-recovery-narrated-orchestration -->

## Goal

Recover the existing `narrated_video` production journey through Product Orchestrator after repository hygiene is merged. Reuse canonical project/domain state and existing capability execution boundaries; do not create a second durable workflow store or revive retired legacy pipeline routes.

## Required direction

- inventory the as-built Narrated path before changing it: script/narration state, prepared or generated audio, visual sources, assembly/render state and any current Review/acceptance evidence;
- project truthful Narrated readiness, prerequisites, relevant workspace, diagnostics, current outcome and bounded semantic next actions from canonical state;
- keep provider/runtime execution behind Capability Registry and the existing D-017 execution boundary;
- require verified project-owned source/artifact bytes anywhere readiness, Review, acceptance or rendering depends on media identity;
- fail closed on stale revisions, missing/tampered media and unavailable required local/free runtime rather than falling back to retired VideoClaw routes;
- preserve the five already recovered Product Orchestrator journeys and the repository-hygiene guarantees from PR #49;
- keep portable JSON/non-finite-value rejection and per-project corruption quarantine in their explicit bounded hardening queue unless Narrated exposes a concrete blocker that cannot be isolated;
- do not resume Stage 9 packaging/release work.

## Completion proof

The slice is complete when the visible Narrated journey can progress through Product Orchestrator from truthful setup/readiness to its current canonical final outcome, with focused API/browser evidence for semantic actions, stale/tampered-state rejection and preservation of existing recovered routes. Exact Draft and Review heads must pass all five permanent Ubuntu/Windows CI checks.

This proof remains Product Truth Recovery evidence only; it does not claim Class C cold-start usability, installed Windows human acceptance or release readiness.

## Entry gate

Begin only from idle `main` after repository-hygiene PR #49 is reviewed, merged and lifecycle closure records its contract/documentation cleanup as complete. If PR #49 discovers a hard blocker that requires a separate persistence-hardening slice before Narrated, update this handoff explicitly instead of silently broadening Narrated.
