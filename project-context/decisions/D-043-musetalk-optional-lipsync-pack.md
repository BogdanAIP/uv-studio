# D-043 — MuseTalk 1.5 is the optional local performance/lip-sync pack

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 8 requires a truthful Performance / lip-sync mode. UV Studio already has the semantic capability `video.digital_human`, but no accepted executable offer satisfies the exact supplied portrait + finished speech contract. The legacy VideoClaw `digital_human` pipeline is product-promo oriented and must not be presented as compatible.

Current open-source candidates were rechecked before integration. Wav2Lip's open-source release restricts commercial use, so it is not suitable as UV Studio's default reusable pack. MuseTalk documents an MIT code license, commercial model use, Windows inference, an input contract accepting video/image + audio, and a tested low-end Windows configuration using an RTX 3050 Ti Laptop GPU with 4 GB VRAM in fp16 mode.

The inspected MuseTalk upstream is `TMElyralab/MuseTalk` at commit `0a89dec45a0192b824e3cf4daf96c239440c5ed8` (MuseTalk 1.5 layout). The inspected `scripts/inference.py` at that commit has Git blob SHA-1 `428afb99a8fbb3175598e18c096b12dbfdf943d5`.

## Decision

1. MuseTalk 1.5 is the preferred optional local pack for the Stage 8 `video.digital_human` / `performance_lip_sync` supplied-media path.
2. UV Studio does **not** vendor MuseTalk source, model weights, test data or Python/CUDA dependencies into the normal application dependency graph.
3. The adapter is pinned to the exact inspected upstream commit, not merely to a compatible-looking directory layout. A separately installed MuseTalk root and Python environment are required before the offer can become available.
4. The public MuseTalk offer is `available` only when the configured root is a readable Git checkout whose `HEAD` equals `0a89dec45a0192b824e3cf4daf96c239440c5ed8`, whose tracked worktree is clean, and whose `scripts/inference.py` matches Git blob `428afb99a8fbb3175598e18c096b12dbfdf943d5`. A different commit, tracked modification or mismatched inference entrypoint remains `configuration_required`.
5. Because the bounded Stage 8 adapter deliberately uses the low-memory fp16 MuseTalk profile, availability also requires the configured MuseTalk Python environment to import the required inference modules and report an available CUDA device. A CPU-only or incomplete environment remains `configuration_required` rather than being advertised as executable and failing later.
6. The exact-checkout and CUDA/runtime preflight tests are repeated immediately before execution. Cached capability discovery therefore cannot authorize a MuseTalk tree or runtime that changed after discovery.
7. Normal UV Studio startup, editing, photo-to-video, visualizer, music, dubbing and other recipes must remain functional when MuseTalk is absent or fails provenance/runtime verification.
8. The UV adapter accepts project-owned source IDs, not arbitrary filesystem paths. It revalidates registered portrait/audio bytes before execution.
9. For a still portrait, UV Studio first creates a bounded 25 fps temporary avatar video matching the supplied speech duration, then invokes MuseTalk 1.5 with generated task configuration. This avoids relying on upstream still-image cleanup quirks while preserving MuseTalk's documented video+audio contract.
10. MuseTalk execution uses a server-generated task/result directory and server-generated artifact path. The user cannot provide arbitrary command-line flags, model paths, result paths or shell fragments through the capability payload.
11. Output must be probed and registered as a project-owned video artifact with exact input SHA bindings and output SHA/size/duration evidence.
12. GPU/device/provider details remain runtime configuration, not canonical project state. Stage 8 exposes only the verified local/free semantic offer, while Stage 9 owns optional-pack installation and diagnostics.
13. Performance/lip-sync remains explicitly `partial`/`configuration_required` when the optional pack is not configured and verified. No incompatible fallback is allowed.
14. Stage 9 optional-pack setup/diagnostics must provision or validate this exact pinned checkout plus an executable CUDA environment (or a future explicitly reviewed replacement with a new decision/fingerprint); it must not silently accept an arbitrary MuseTalk source tree.
15. Third-party dependencies used by a configured MuseTalk installation remain subject to their own licenses; the pack cannot make upstream test data commercial assets.
16. Automatic Codex code review remains excluded under D-040.

## Consequences

- UV Studio gains a professional open-source lip-sync direction without making PyTorch/CUDA a mandatory app dependency.
- A clean Windows installation can remain lightweight; Stage 9 can later offer explicit optional-pack setup/diagnostics.
- Runtime provenance is fail-closed: a modified/wrong MuseTalk checkout, incomplete Python environment or CPU-only machine cannot be represented as the inspected executable fp16 implementation merely because expected files exist.
- CI can verify adapter trust boundaries, exact checkout/fingerprint policy, CUDA preflight behavior and command construction without downloading multi-GB model weights, while real MuseTalk execution remains an optional hardware-dependent acceptance path.
- The product remains truthful on machines without the pack: the recipe is visible, but execution is reported as configuration-required/partial rather than silently failing or switching to a different workflow.
