# Third-Party Notices

UV Studio includes, adapts or interoperates with third-party software. This file distinguishes code actually vendored/adapted, binaries carried in the current Stage 9 Windows payload, optional runtime integrations and development-only tools. Source-code licenses do not automatically cover model weights, datasets, hosted-service terms or generated assets.

The immutable Windows release also contains a copy of this notice, the UV Studio license and the exact reviewed Windows runtime input profile under `legal/`. Component-specific notices that must accompany a shipped binary are kept with that release evidence rather than being treated as covered by this summary alone.

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

## Node.js runtime

Project: `nodejs/node`  
Stage 9 Windows runtime: Node.js `24.19.0`  
Acquisition artifact: official `node-v24.19.0-win-x64.zip`

The release profile pins the official Windows x64 archive by SHA-256. Stage 9 extracts `node.exe` and the complete upstream `LICENSE` from that same verified archive. The complete Node.js license/third-party notice bundle is staged in the immutable product payload at `legal/node/LICENSE.txt`; this summary is not a substitute for that full file.

Node.js is bundled only to run the current official Next.js standalone frontend. Users do not need a separately installed Node/npm runtime, and Node/provider identity does not enter canonical UV project state.

## MLT Multimedia Framework and `melt`

Project: `mltframework/mlt`

MLT upstream distinguishes licensing by component. The framework libraries and `libmvcp` are LGPL-family components, while the `melt`/`melted` applications are identified by upstream as GPL applications; individual modules/plugins can carry additional or different compatible terms.

UV Studio uses MLT behind a UV-owned editor adapter and currently stages `melt.exe` plus its required Windows runtime/plugin closure from the exact SHA-256-pinned Kdenlive `26.04.3` standalone carrier. Therefore the Stage 9 redistribution audit must cover the actual `melt` application and every shipped module/plugin/library in the curated media payload; describing the whole payload merely as "LGPL MLT" would be inaccurate.

The Kdenlive standalone archive is an acquisition/provenance carrier, not the canonical UV Studio file set. D-052 removes only specifically proven non-runtime Qt test/build material before D-044 inventories and hashes the resulting immutable payload.

## FFmpeg / FFprobe

Project: FFmpeg

FFmpeg is LGPL-family by default, but enabled GPL-covered parts can make a particular build GPL and `--enable-nonfree` creates a build that upstream states is not redistributable. Consequently UV Studio does not infer redistribution terms from the executable name alone.

The current Stage 9 Windows payload obtains FFmpeg/FFprobe as part of the pinned Kdenlive `26.04.3` standalone carrier. Before a public release is declared complete, the exact staged build configuration and the licenses/source obligations of enabled components/codecs must be captured and reviewed. D-044 integrity proves which bytes are shipped; it does not by itself prove license compliance.

A separate closed research PR tested a pinned shared FFmpeg candidate built without `--enable-gpl` or `--enable-nonfree`, but that probe is research evidence only and is not silently substituted for the current Stage 9 media payload.

## Next.js and production frontend dependencies

The production frontend is built from the exact committed `frontend/package-lock.json` and shipped using the official Next.js standalone output. The frontend release gate runs `npm ci`, lint, a high-severity dependency audit and production build before staging. The final release audit must retain notices required by the exact transitive packages that are present in the standalone output.

## PyInstaller and NSIS build tooling

PyInstaller and NSIS are Stage 9 build/installer tooling, not canonical UV project dependencies. The shipping Python runtime graph is verified before the build-only PyInstaller package is installed. NSIS is acquired at the pinned Stage 9 version to compile the per-user installer. Generated installer redistribution obligations remain part of the final release audit rather than being inferred from the Python runtime lock.

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

## MuseTalk optional runtime pack

MuseTalk remains an independently installed optional local capability under D-043. It is not part of the baseline Windows release payload. UV Studio verifies the exact reviewed checkout/runtime profile and pinned model-payload identities before exposing the capability; those model/runtime licenses remain separate from UV Studio's own MIT license and from the baseline desktop installer.

## Research-only candidates

OpenClaw, Qwen-MM-Plugins profiles, dialogue/background separation candidates and later workflow/component research do not become distributed dependencies merely because they are evaluated or mentioned in architecture documents. Adoption requires an explicit integration/license decision.

## Model and hosted-service terms

Every bundled model needs its own license/commercial-use/redistribution review. Every hosted provider is governed by the applicable service terms separately from an adapter library's source license.

## Stage 9 release-audit boundary

This notice records known provenance and the current packaging model; it is not a claim that the final public redistribution audit or Windows artifact signing is already complete. Stage 9 can close only after the exact release payload is audited, required source/license/notice obligations are satisfied, signing/checksum provenance is established, and the exact review head passes the permanent product/release gates.
