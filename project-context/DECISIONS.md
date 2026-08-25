# Architecture Decisions

This is the compact decision authority index. Read `docs/architecture/CURRENT_ARCHITECTURE.md` first for the current system shape; detailed ADRs are historical records whose status may be accepted, partially superseded or superseded.

## Current product / application authority

- **D-064 — Production Directions over shared Studio Core.** Current product-composition/direction authority.
- **D-065 — Shared Production Semantic Core beneath Production Directions.** Current factoring authority for reusable Scene/Shot/Take/accepted-material semantics and direction extensions.
- **D-033 — Reuse-first scriptable editor foundation.** Current editor/MLT ownership foundation.
- **D-009 — Project Store is file-first and product-owned.** Canonical local-first project authority.
- **D-017 — Exact one-shot execution authorization.** Current remote/non-free execution authorization boundary.
- **D-038 — Explicit idle development lifecycle.** Current repository development-state lifecycle.

## Supporting accepted decisions

- D-001 — Repository is durable development memory.
- D-003 — Pin upstream before modification.
- D-004 — No universal mandatory media pipeline; task/domain composition may differ over shared execution foundations.
- D-005 — Continuity and VLM review are optional policies unless a direction/user journey requires them.
- D-007 — Windows is a first-class target.
- D-008 — Vendored upstream is a compatibility boundary.
- D-010 — User-facing frontend is UV Studio-owned derived code.
- D-011 — Capability Registry has peer adapters; no mandatory OpenClaw hop.
- D-012 — Qwen-MM is optional capability/workflow donor, not a required paid dependency.

Detailed supporting records:

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
- [D-041 — Music Map / reference-only storyboard research](decisions/D-041-music-video-map-reference-only-storyboard.md)
- [D-043 — Optional MuseTalk lip-sync pack](decisions/D-043-musetalk-optional-lipsync-pack.md)
- [D-064 — Production Directions over shared Studio Core](decisions/D-064-production-directions-over-shared-studio-core.md)
- [D-065 — Shared Production Semantic Core](decisions/D-065-shared-production-semantic-core.md)

## Partially superseded / historical product-composition decisions

These records remain useful for rationale and migration evidence but are not co-equal current product authority:

- [D-062 — Product Truth Recovery Gate](decisions/D-062-product-truth-recovery-gate.md) — Product Truth invariants remain; Product Orchestrator as long-term center is superseded.
- [D-063 — Studio-first product architecture](decisions/D-063-studio-first-product-architecture.md) — shared Studio application/model/job/command architecture remains; prohibition on meaningful Production Direction choice is superseded by D-064.
- [D-042 — Stage 8 composition-first additional recipes](decisions/D-042-stage-8-composition-first-additional-recipes.md) — recipe-first product composition is superseded; technical media/capability evidence remains historical reference.

## Historical donor-era decisions

D-002 (VideoClaw as initial base) and D-006 (provider-specific containment before D-011) describe earlier migration choices. They must not override current UV-owned Studio, production semantics, capability and adapter authority.

When documents disagree, use this order:

`CURRENT_ARCHITECTURE.md` -> D-064 (product direction) + D-065 (shared production semantics) -> active foundational ADR for the specific concern -> compatibility/historical records.
