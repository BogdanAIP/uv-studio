# Third-Party Notices

UV Studio includes, adapts or interoperates with third-party software. This file distinguishes code actually vendored/adapted, optional runtime integrations and external system tools. Source-code licenses do not automatically cover model weights, datasets, hosted-service terms or generated assets.

## VideoClaw

Project: `HITsz-TMG/VideoClaw`  
License: MIT  
Pinned source revision: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`  
Vendored subtree: `video-claw/video-claw`

The exact upstream license/provenance are retained under `vendor/videoclaw-app/`. The complete upstream runtime is not the default UV Studio application root after D-025.

## OpenCut Classic timeline interaction

Project: `OpenCut-app/opencut-classic`  
License: MIT  
Pinned source revision: `cf5e79e919144200294fb9fed22a222592a0aeea`

Stage 4C selectively adapts compatible timeline interaction/layout ideas and portions while keeping UV Project Store/Command state canonical. The donor license is retained at `third_party/opencut-classic/LICENSE`.

## MLT Multimedia Framework

Project: `mltframework/mlt`  
Upstream describes MLT as an LGPL multimedia framework. D-033 selects it as the editing/timeline engine behind a UV-owned adapter.

Development/CI obtains MLT from system packages on Linux and from a SHA-256-pinned KDE/Kdenlive standalone carrier on Windows. This proves deployment feasibility; it is not yet the final redistribution plan. Stage 9 packaging must audit the exact MLT build, linked modules/plugins and accompanying notices before redistribution.

## FFmpeg / FFprobe

Project: FFmpeg  
Default upstream license: LGPL v2.1-or-later, with GPL applying when GPL-covered optional parts are enabled.

UV Studio invokes FFmpeg/FFprobe as external deterministic media tools. Development/CI provisioning is not a final shipping decision. Any packaged Windows release must record the exact distributed FFmpeg build/configuration and comply with the licenses of enabled components/codecs rather than assuming every FFmpeg binary has identical terms.

## Playwright (development/browser E2E only)

Project: `microsoft/playwright-python` / `microsoft/playwright`  
Source license: Apache-2.0  
UV Studio development dependency: `playwright==1.61.0`

Playwright is used only by the maintained browser user-outcome suite under `e2e/` and CI. It is not a UV Studio core/runtime dependency and is not required to open or execute a user project. Browser binaries are provisioned separately for CI rather than being treated as canonical project assets.

## whisper.cpp (optional local ASR runtime)

Project: `ggml-org/whisper.cpp`  
Source license: MIT

Stage 5 uses whisper.cpp as the preferred local/free `speech.transcribe` runtime when configured. UV Studio does not treat ASR model weights as covered automatically by the whisper.cpp source-code license; model provenance/license remains a separate packaging gate.

## Argos Translate (optional)

Project: `argosopentech/argos-translate`  
Library source license: dual MIT / CC0 according to upstream.

Argos is an optional local translation runtime and is not a core dependency. Installed language packages/models remain outside portable project state. Their individual provenance/license must be checked separately before UV Studio distributes any language package; the library source license alone is not sufficient evidence for every model package.

## WhisperX (optional precision alignment)

Project: `m-bain/whisperX`  
Source license: BSD-2-Clause in the currently evaluated upstream revision.

WhisperX remains an optional heavy precision/alignment runtime with explicit local model-cache configuration and no hidden model downloads. Its transitive dependencies and any separately downloaded model weights keep their own license/redistribution obligations.

## edge-tts (optional remote client)

Project: `rany2/edge-tts`  
UV Studio dependency set: `requirements-edge-tts.txt`  
Supported dependency line: `edge-tts>=7.2.8,<8`  
Recorded package license metadata: LGPLv3

UV Studio does not vendor `edge-tts` source or install it through the core dependency set. It is an optional client for the exact `native_videoclaw.edge_tts` offer. The client software license does not grant or determine Microsoft-hosted service terms, regional availability or rights in generated content.

## Research-only candidates

OpenClaw, Qwen-MM-Plugins profiles, dialogue/background separation candidates and later workflow/component research do not become distributed dependencies merely because they are evaluated or mentioned in architecture documents. Adoption requires an explicit integration/license decision.

## Model and hosted-service terms

Every bundled model needs its own license/commercial-use/redistribution review. Every hosted provider is governed by the applicable service terms separately from an adapter library's source license. Final Stage 9 release audit must evaluate the exact binaries, models and notices that are actually shipped.
