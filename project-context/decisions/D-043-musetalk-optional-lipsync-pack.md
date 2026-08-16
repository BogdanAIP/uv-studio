# D-043 — MuseTalk 1.5 is the optional local performance/lip-sync pack

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 8 requires a truthful Performance / lip-sync mode. UV Studio already has the semantic capability `video.digital_human`, but no accepted executable offer satisfies the exact supplied portrait + finished speech contract. The legacy VideoClaw `digital_human` pipeline is product-promo oriented and must not be presented as compatible.

Current open-source candidates were rechecked before integration. Wav2Lip's open-source release restricts commercial use, so it is not suitable as UV Studio's default reusable pack. MuseTalk documents an MIT code license, commercial model use, Windows inference, an input contract accepting video/image + audio, and a tested low-end Windows configuration using an RTX 3050 Ti Laptop GPU with 4 GB VRAM in fp16 mode.

The inspected MuseTalk upstream is `TMElyralab/MuseTalk` at commit `0a89dec45a0192b824e3cf4daf96c239440c5ed8` (MuseTalk 1.5 layout).

## Decision

1. MuseTalk 1.5 is the preferred optional local pack for the Stage 8 `video.digital_human` / `performance_lip_sync` supplied-media path.
2. UV Studio does **not** vendor MuseTalk source, model weights, test data or Python/CUDA dependencies into the normal application dependency graph.
3. The adapter is pinned to the inspected upstream layout/contract. A separately installed MuseTalk root and Python environment are required before the offer becomes available.
4. Normal UV Studio startup, editing, photo-to-video, visualizer, music, dubbing and other recipes must remain functional when MuseTalk is absent.
5. The UV adapter accepts project-owned source IDs, not arbitrary filesystem paths. It revalidates registered portrait/audio bytes before execution.
6. For a still portrait, UV Studio first creates a bounded 25 fps temporary avatar video matching the supplied speech duration, then invokes MuseTalk 1.5 with generated task configuration. This avoids relying on upstream still-image cleanup quirks while preserving MuseTalk's documented video+audio contract.
7. MuseTalk execution uses a server-generated task/result directory and server-generated artifact path. The user cannot provide arbitrary command-line flags, model paths, result paths or shell fragments through the capability payload.
8. Output must be probed and registered as a project-owned video artifact with exact input SHA bindings and output SHA/size/duration evidence.
9. The default low-memory inference profile uses MuseTalk 1.5 fp16. GPU/device/provider details remain runtime configuration, not canonical project state.
10. Performance/lip-sync remains explicitly `partial` when the optional pack is not configured. No incompatible fallback is allowed.
11. Third-party dependencies used by a configured MuseTalk installation remain subject to their own licenses; the pack cannot make upstream test data commercial assets.
12. Automatic Codex code review remains excluded under D-040.

## Consequences

- UV Studio gains a professional open-source lip-sync direction without making PyTorch/CUDA a mandatory app dependency.
- A clean Windows installation can remain lightweight; Stage 9 can later offer explicit optional-pack setup/diagnostics.
- CI can verify adapter trust boundaries and command construction without downloading multi-GB model weights, while real MuseTalk execution remains an optional hardware-dependent acceptance path.
- The product remains truthful on machines without the pack: the recipe is visible, but execution is reported as configuration-required/partial rather than silently failing or switching to a different workflow.
