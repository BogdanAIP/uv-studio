# D-043 — MuseTalk 1.5 is the optional local performance/lip-sync pack

**Status:** accepted  
**Date:** 2026-08-16

## Context

Stage 8 requires a truthful Performance / lip-sync mode. UV Studio already has the semantic capability `video.digital_human`, but no accepted executable offer satisfies the exact supplied portrait + finished speech contract. The legacy VideoClaw `digital_human` pipeline is product-promo oriented and must not be presented as compatible.

Current open-source candidates were rechecked before integration. Wav2Lip's open-source release restricts commercial use, so it is not suitable as UV Studio's default reusable pack. MuseTalk documents an MIT code license, commercial model use, Windows inference, an input contract accepting video/image + audio, and a tested low-end Windows configuration using an RTX 3050 Ti Laptop GPU with 4 GB VRAM in fp16 mode.

The inspected MuseTalk upstream is `TMElyralab/MuseTalk` at commit `0a89dec45a0192b824e3cf4daf96c239440c5ed8` (MuseTalk 1.5 layout). The inspected `scripts/inference.py` at that commit has Git blob SHA-1 `428afb99a8fbb3175598e18c096b12dbfdf943d5`.

MuseTalk and its dependencies load several model payloads through PyTorch/Transformers/Diffusers loaders. In particular, the accepted MuseTalk 1.5 UNet path is loaded with `torch.load`, so model files are part of the executable trust boundary rather than interchangeable opaque data. The Stage 8 verified profile therefore pins the exact binary payloads expected from the reviewed upstream download layout.

## Decision

1. MuseTalk 1.5 is the preferred optional local pack for the Stage 8 `video.digital_human` / `performance_lip_sync` supplied-media path.
2. UV Studio does **not** vendor MuseTalk source, model weights, test data or Python/CUDA dependencies into the normal application dependency graph.
3. The adapter is pinned to the exact inspected upstream commit, not merely to a compatible-looking directory layout. A separately installed MuseTalk root and Python environment are required before the offer can become available.
4. The public MuseTalk offer is `available` only when the configured root is a readable Git checkout whose `HEAD` equals `0a89dec45a0192b824e3cf4daf96c239440c5ed8`, whose tracked worktree is clean, and whose `scripts/inference.py` matches Git blob `428afb99a8fbb3175598e18c096b12dbfdf943d5`. A different commit, tracked modification or mismatched inference entrypoint remains `configuration_required`.
5. Tracked-clean is necessary but not sufficient because MuseTalk is executed from the checkout root and Python resolves checkout-local modules before the configured environment. The verified offer therefore also rejects untracked or ignored executable/importable runtime files outside explicitly allowed `.venv/` / `venv/` environment trees. This includes Python source/bytecode/native extensions, executable/script files, checkout-local `ffmpeg`/`ffprobe`/`ffplay`, and untracked symlinks that could shadow an imported module or executable.
6. Verified MuseTalk Python invocations use `-B` so UV Studio does not create new `__pycache__` / `.pyc` files inside the checkout after verification.
7. The Stage 8 profile requires exact SHA-256 values for the six binary model payloads that participate in the accepted inference layout:
   - `models/musetalkV15/unet.pth` — `7ebf6c98c181e20838e4c0054e96e944ac60d5d692cc01db42839fe11b787007`;
   - `models/sd-vae/diffusion_pytorch_model.bin` — `1b4889b6b1d4ce7ae320a02dedaeff1780ad77d415ea0d744b476155c6377ddc`;
   - `models/whisper/pytorch_model.bin` — `9607f98a2b22d9e229ae43c52ecea79dcede9e0c5cfae67e8da6eda86d8aac1d`;
   - `models/dwpose/dw-ll_ucoco_384.pth` — `0d9408b13cd863c4e95a149dd31232f88f2a12aa6cf8964ed74d7d97748c7a07`;
   - `models/face-parse-bisent/79999_iter.pth` — `468e13ca13a9b43cc0881a9f99083a430e9c0a38abd935431d1c28ee94b26567`;
   - `models/face-parse-bisent/resnet18-5c106cde.pth` — `5c106cde386e87d4033832f2996f5493238eda96ccf559d1d62760c4de0613f8`.
8. Each pinned model payload must be a regular non-symlink file. A hash mismatch keeps the offer `configuration_required` and blocks execution.
9. The accepted Stage 8 layout deliberately uses the pinned VAE/Whisper `.bin` payloads from the reviewed download path. Loader-preferred alternatives such as `models/sd-vae/diffusion_pytorch_model.safetensors` or `models/whisper/model.safetensors` are rejected in this profile because their presence could cause a different model file to be loaded while the pinned `.bin` still exists. A future alternate layout requires explicit review and a revised decision/fingerprint set.
10. Because the bounded Stage 8 adapter deliberately uses the low-memory fp16 MuseTalk profile, availability also requires the configured MuseTalk Python environment to import the required inference modules and report an available CUDA device. A CPU-only or incomplete environment remains `configuration_required` rather than being advertised as executable and failing later.
11. Exact checkout, untracked-runtime-code, model-payload and CUDA/runtime preflight checks are repeated immediately before execution. Cached capability discovery therefore cannot authorize a MuseTalk tree, model payload or runtime that changed after discovery.
12. Normal UV Studio startup, editing, photo-to-video, visualizer, music, dubbing and other recipes must remain functional when MuseTalk is absent or fails provenance/runtime verification.
13. The UV adapter accepts project-owned source IDs, not arbitrary filesystem paths. It revalidates registered portrait/audio bytes before execution.
14. For a still portrait, UV Studio first creates a bounded 25 fps temporary avatar video matching the supplied speech duration, then invokes MuseTalk 1.5 with generated task configuration. This avoids relying on upstream still-image cleanup quirks while preserving MuseTalk's documented video+audio contract.
15. MuseTalk execution uses a server-generated task/result directory and server-generated artifact path. The user cannot provide arbitrary command-line flags, model paths, result paths or shell fragments through the capability payload.
16. Output must be probed and registered as a project-owned video artifact with exact input SHA bindings and output SHA/size/duration evidence.
17. GPU/device/provider details remain runtime configuration, not canonical project state. Stage 8 exposes only the verified local/free semantic offer, while Stage 9 owns optional-pack installation and diagnostics.
18. Performance/lip-sync remains explicitly `partial`/`configuration_required` when the optional pack is not configured and verified. No incompatible fallback is allowed.
19. Stage 9 optional-pack setup/diagnostics must provision or validate this exact pinned checkout, exact accepted model payload set and an executable CUDA environment (or a future explicitly reviewed replacement with a new decision/fingerprint set); it must not silently accept an arbitrary MuseTalk source tree, checkout-local shadow code or substituted model weights.
20. Third-party dependencies used by a configured MuseTalk installation remain subject to their own licenses; the pack cannot make upstream test data commercial assets.
21. Automatic Codex code review remains excluded under D-040.

## Consequences

- UV Studio gains a professional open-source lip-sync direction without making PyTorch/CUDA a mandatory app dependency.
- A clean Windows installation can remain lightweight; Stage 9 can later offer explicit optional-pack setup/diagnostics.
- Runtime provenance is fail-closed: a modified/wrong MuseTalk checkout, checkout-local import/executable shadow, substituted executable model payload, incomplete Python environment or CPU-only machine cannot be represented as the inspected executable fp16 implementation merely because expected paths exist.
- Local virtual environments and ordinary generated/non-code data remain compatible with the optional-pack design, while executable/importable material and model payloads that can participate in deserialization are explicitly part of the trust boundary.
- The strict Stage 8 profile prefers reproducibility over silently accepting alternate model layouts; alternative safetensors or future upstream weight revisions require an explicit reviewed profile update.
- CI can verify checkout/fingerprint policy, untracked shadow rejection, model hash enforcement, CUDA preflight behavior and command construction without downloading multi-GB model weights, while real MuseTalk execution remains an optional hardware-dependent acceptance path.
- The product remains truthful on machines without the pack: the recipe is visible, but execution is reported as configuration-required/partial rather than silently failing or switching to a different workflow.
