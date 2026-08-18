# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: semantic-api-docs -->

**Updated:** 2026-08-18

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 8 Additional Recipes is merged through PR #37 / merge commit `5eb8f6c2256b9b67dd1e896fc929682eb19b16ca` after Chat-first review on exact head `91dcf820b8df76730584f3c27457c782db00b213`. The final pre-merge review head passed all five permanent CI jobs in Actions run `31971331754`, including API integration, real HTTP, FFmpeg/MLT real-media evidence, frontend lint/audit/build and Playwright browser outcomes on Ubuntu and Windows.

The Stage 8 lifecycle was closed to canonical `idle` on `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3`. A narrow cross-cutting documentation slice, `semantic-api-docs`, is now active on `chore/semantic-api-docs`. It documents the existing UV-owned semantic integration boundary without changing product code, provider/runtime behavior, Project Store authority or the Stage 9 handoff.

## Stage 8 delivered product modes

Stage 8 broadens UV Studio by composition rather than by introducing another universal project, timeline or provider engine:

1. **Story Video** — composition-first brief/script workspace with exact project-owned image/video/audio bindings.
2. **Commercial / Product** — the same portable workspace model with product-oriented media roles and truthful capability readiness.
3. **Photo → Video** — semantic capability `video.compose_photos` through deterministic local FFmpeg, ordered project-owned stills plus optional project-owned audio, bounded render settings and artifact provenance.
4. **Audio Visualizer** — semantic capability `audio.visualize` through deterministic local FFmpeg, project-owned master audio plus optional artwork, waveform rendering and measured-duration verification.
5. **Performance / Lip-sync** — optional local MuseTalk 1.5 supplied portrait + finished speech path, exposed only when the reviewed runtime boundary is satisfied.
6. **Free Project** — intentionally no required one-click pipeline; users compose the UV-owned primitives their project needs.

Story/commercial/free persist typed/versioned Stage 8 input workspaces beneath the canonical Project Store. Photo/visualizer remain bounded local/free deterministic media operations. Performance/lip-sync keeps heavyweight ML/runtime/model installation outside the normal UV Studio dependency graph.

## Stage 8 review findings closed

Before merge, review and exact-head CI closed the following concrete defects and trust-boundary gaps:

- restored semantic capability identity `video.compose_photos` in blocked execution-plan diagnostics;
- removed browser races that treated an already-visible control as proof of completed asynchronous project-source registration;
- synchronized performance portrait/speech selection with exact registered source IDs;
- removed source-count-driven component remounts that could discard user-selected media and manual photo order;
- added browser regression proving a user-defined photo order survives a later audio upload and is preserved in final render provenance;
- hardened the verified MuseTalk checkout against untracked/ignored importable or executable shadows and untracked symlinks outside explicitly allowed `.venv/` / `venv/` trees;
- disabled MuseTalk checkout bytecode creation with Python `-B`;
- pinned exact SHA-256 identities for the six binary model payloads used by the accepted MuseTalk 1.5 inference profile because those payloads participate in executable deserialization/runtime loading;
- rejected loader-preferred alternative VAE/Whisper payloads that could cause different bytes to execute while pinned files remained present;
- persisted stable `runtime_profile` and full `model_payload_sha256` provenance into successful verified lip-sync artifacts.

D-043 records the complete optional MuseTalk trust boundary. The accepted Stage 8 profile is deliberately fail-closed: future upstream/model revisions require an explicit reviewed profile/fingerprint update rather than silent compatibility.

## Current cross-cutting documentation slice

`semantic-api-docs` gives a stable name and explicit contract to the integration-facing semantic boundary that already exists across the Project Store, UV Command API, Capability Registry/execution path, Recipe Registry and execution planning surfaces.

This slice must not introduce a second command implementation, a second project/capability registry, a raw canonical-state mutation path, a new provider/runtime abstraction, or a new remote-access trust boundary. The existing `uv_studio/editor`, `uv_studio/capabilities`, `uv_studio/projects`, `uv_studio/recipes`, `uv_studio/mcp` and `uv_studio/api` implementations remain authoritative.

## Architecture invariants

- Project Store and UV-owned domain state are canonical; engines, model runtimes and compatibility surfaces are adapters rather than competing authorities.
- GUI, scripts, AI and MCP converge on UV-owned semantic capabilities/commands/workflows.
- UV Semantic API is an integration-facing projection of those existing contracts, not a second command system or blanket designation for every `/api/uv` route.
- Paid/remote execution remains optional and behind D-017; provider/model identifiers remain outside canonical project state.
- Stage 8 remains composition-first under D-042; it did not add a second universal media/project/timeline engine.
- Performance/lip-sync remains `configuration_required`/partial unless the exact D-043 checkout, shadow-code, model-payload, runtime and CUDA preflight succeeds.
- Windows and Linux remain continuous engineering targets.
- Development/review remains Chat-first under D-040; automatic Codex review is excluded.

## Verification history

- Stable Stage 7 idle base: `main@b68669a9eb56e2d85601b9e35f1783ce23a33c1a`, green CI #1431.
- Stage 8 product baseline: `2fb903794cf6b6bef576f941c21c18bee9059377`, green CI #1572 / Actions `31969309483`.
- Initial Stage 8 review transition: `18f46b504feffad7d67878408c15070244381af9`, green CI #1574 / Actions `31969673721`.
- Final security-reviewed Stage 8 head: `91dcf820b8df76730584f3c27457c782db00b213`, all five permanent jobs green in Actions run `31971331754`.
- Stage 8 merge commit: `5eb8f6c2256b9b67dd1e896fc929682eb19b16ca`.
- Stage 8 idle closure head: `d57bc315c27ed21f26c9050d661c792f95ab8aa3`.

## Cross-cutting backlog

Non-blocking debt remains deliberately outside this documentation slice: broader codec/device fixtures, reproducible Python dependency locking, schema migration/versioning for growing extension state, generated frontend contracts, a future common command envelope, reusable frontend primitives, CI job decomposition, deeper renderer file-handle/TOCTOU hardening, richer continuity authoring and eventual retirement of transitional compatibility surfaces.

## Next handoff

`stage-9-desktop-productization-release-hardening` remains the declared next slice. Its entry conditions are defined in `project-context/NEXT_TASK.md`; this documentation slice must be reviewed, merged and closed back to `idle` before that handoff starts.
