# Architecture Decisions

This file is the compact decision index. Detailed records from D-013 onward live under `project-context/decisions/`; do not duplicate their full rationale here.

## Foundational decisions

- **D-001 — Repository is durable development memory.** Durable state belongs in GitHub/repository, not only chat history.
- **D-002 — VideoClaw modern application is the initial base.** Reuse the modern application as donor/compatibility baseline rather than making its workflow universal.
- **D-003 — Pin upstream before modification.** Vendored upstream comes from an exact commit with provenance.
- **D-004 — No universal mandatory media pipeline.** Task recipes compose optional capabilities.
- **D-005 — Continuity and VLM review are optional policies.** They are not mandatory project fields.
- **D-006 — Provider-specific growth must be contained.** Superseded in runtime preference by D-011; semantic separation remains.
- **D-007 — Windows is a first-class target.** Continuous Windows/Linux engineering evidence is required.
- **D-008 — Vendored upstream is a compatibility boundary.** Ordinary UV work stays outside `vendor/`.
- **D-009 — Project Store is file-first and product-owned.** Canonical state is UV-owned, local-first and versioned.
- **D-010 — User-facing frontend is UV Studio-owned derived code.** The pinned donor snapshot remains provenance, not live product authority.
- **D-011 — Capability Registry has peer adapters; no mandatory OpenClaw hop.** Local/native/MCP/runtime implementations are peers.
- **D-012 — Qwen-MM is an optional capability/workflow donor, not a paid dependency.** Cloud use remains explicit.

## Detailed decision records

- [D-013 — Capability offers](decisions/D-013-capability-offers.md)
- [D-014 — Execution permission](decisions/D-014-execution-permission.md)
- [D-015 — Direct MCP discovery](decisions/D-015-direct-mcp-discovery.md)
- [D-016 — Qwen-MM optional pack](decisions/D-016-qwen-mm-pack.md)
- [D-017 — Exact one-shot execution authorization](decisions/D-017-execution-authorization.md)
- [D-018 — Authorized MCP invocation](decisions/D-018-authorized-mcp-invocation.md)
- [D-019 — MCP project-file inputs](decisions/D-019-mcp-project-file-inputs.md)
- [D-020 — Exact native VideoClaw Edge TTS](decisions/D-020-native-videoclaw-edge-tts.md)
- [D-021 — Exact media-range extraction](decisions/D-021-exact-media-range-extraction.md)
- [D-022 — Deterministic range reinsertion](decisions/D-022-deterministic-range-reinsertion.md)
- [D-023 — Agent development workflow](decisions/D-023-agent-development-workflow.md)
- [D-024 — Roadmap runtime gates](decisions/D-024-roadmap-runtime-gates.md)
- [D-025 — Runtime security boundary](decisions/D-025-runtime-security-boundary.md)
- [D-026 — Dependency ownership](decisions/D-026-dependency-ownership.md)
- [D-027 — Stage 4A real-media evidence](decisions/D-027-stage4a-real-media-evidence.md)
- [D-028 — Non-destructive edit state](decisions/D-028-non-destructive-edit-state.md)
- [D-029 — Range continuity brief](decisions/D-029-range-continuity-brief.md)
- [D-030 — Replacement plan gate](decisions/D-030-replacement-plan-gate.md)
- [D-031 — Replacement candidate preparation](decisions/D-031-replacement-candidate-preparation.md)
- [D-032 — Replacement review gate](decisions/D-032-replacement-review-gate.md)
- [D-033 — Reuse-first scriptable editor foundation](decisions/D-033-reuse-first-scriptable-editor-foundation.md)
- [D-034 — Local ASR baseline](decisions/D-034-local-asr-baseline.md)
- [D-035 — Dubbing review/acceptance](decisions/D-035-dubbing-review-acceptance.md)
- [D-036 — Dialogue/background separation evaluation](decisions/D-036-dialogue-background-separation-evaluation.md)
- [D-037 — Stage 5 language/audio precision stack](decisions/D-037-stage-5-language-audio-precision-stack.md)
- [D-038 — Explicit idle development lifecycle](decisions/D-038-explicit-idle-development-lifecycle.md)
- [D-039 — Optional sequence continuity and bounded inspection](decisions/D-039-sequence-continuity-bounded-inspection.md)
- [D-040 — Chat-first development; no automatic Codex review](decisions/D-040-chat-first-no-automatic-codex-review.md)
- [D-041 — Music Video Mode: UV-owned Music Map and reference-only storyboard research](decisions/D-041-music-video-map-reference-only-storyboard.md)
- [D-042 — Stage 8 composition-first additional recipes](decisions/D-042-stage-8-composition-first-additional-recipes.md)
- [D-043 — MuseTalk optional lip-sync pack](decisions/D-043-musetalk-optional-lipsync-pack.md)
- [D-044 — Stage 9 product-owned release runtime manifest](decisions/D-044-stage-9-release-runtime-manifest.md)
- [D-045 — Packaged mutable state outside immutable release payload](decisions/D-045-packaged-mutable-state-boundary.md)
- [D-046 — Exact supported language runtimes and Windows Python release lock](decisions/D-046-stage-9-release-runtime-lock.md)
- [D-047 — Packaged product-owned executables never fall back to system PATH](decisions/D-047-packaged-toolchain-resolution.md)
