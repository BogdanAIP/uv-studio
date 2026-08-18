# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-9-desktop-productization-release-hardening -->

## Current lifecycle

Stage 9 Desktop Productization & Release Hardening is the single active draft slice in PR #38 on `stage-9/desktop-productization-release-hardening`, based on exact green idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8 merged as PR #37.

The branch remains **Draft**. Productization is substantially implemented, but Stage 9 is not allowed to move to review until the final media-redistribution boundary, signing/release audit and exact-head permanent checks are complete.

## Product goal

Ship a native Windows product that requires no separately prepared Python, Node/npm, FFmpeg or MLT while preserving canonical projects, archives, capability authorization, user data and all permanent user-facing workflows through packaged execution.

## Implemented and previously proven

The following Stage 9 architecture is already implemented and has exact-head evidence on earlier accepted decision heads:

- **D-044 immutable release manifest** — complete sorted payload inventory with size/SHA-256, path/symlink rejection and deep same-size tamper detection;
- **D-045 packaged mutable-state boundary** — immutable application payload separated from `%LOCALAPPDATA%/UV Studio` projects/config/logs;
- **D-046 exact release input profile** — CPython 3.13.14, exact 32-package shipping graph, Node.js 24.19.0, pinned media input and build-tool identities;
- **D-047 packaged toolchain resolution** — FFmpeg/FFprobe/MLT resolve only from the verified release manifest, never system PATH fallback;
- **D-048 official Next standalone frontend** with dynamic project routes and a bundled Node runtime;
- **D-049 desktop launcher supervision** for frozen backend + standalone frontend lifecycle;
- **D-050 per-user versioned NSIS installation** with deep verification before activation;
- **D-051 fail-closed project migration preparation/recovery**;
- **D-052 evidence-based media-payload curation rule** introduced for the original carrier;
- **D-053 installer-carried A -> B -> A update/rollback** while preserving user data;
- **D-054 secret-safe diagnostics/recovery health**;
- **D-055 installed clean-machine proof** with host Python/Node/FFmpeg/FFprobe/MLT removed from PATH;
- **D-056 cancellable local FFmpeg jobs** with process termination/reaping and no partial Project Store artifact publication.

The Windows Release workflow has already proven, on earlier accepted heads, the frozen backend, standalone frontend, bundled language/media runtimes, D-044 deep verification, same-size tamper rejection, native desktop supervision, NSIS build, silent install, installed launch, safe uninstall and versioned A -> B -> A rollback.

## D-057 constrained-host and long-project work

D-057 remains **Proposed** pending final exact-head evidence. Its implementation is present:

- coarse secret-safe logical CPU / total+available RAM diagnostics with fail-soft OS probes;
- no hostname/user/process/environment/path inventory in resource diagnostics;
- 2,000 source + 2,000 artifact Project Store round-trip/load/JSON evidence under a bounded traced Python allocation envelope;
- real ten-minute CPU-only media with extraction near 598–600 seconds through `LocalFFmpegAdapter`;
- D-056 cancellation remains the bounded escape path for expensive local work.

A prior exact implementation head completed the Windows release workflow and all Windows product gates; the corresponding Ubuntu app-baseline was cancelled by the job timeout while `apt-get update` was stalled on the hosted runner mirror after API/HTTP tests had already passed. D-057 is not Accepted until one current exact head completes the complete required set.

## Release legal/provenance hardening now in progress

Review of the original Kdenlive 26.04.3 carrier found that its actual FFmpeg 8.1.1 self-report included `--enable-nonfree`. Runtime success therefore does not make that carrier acceptable for a public UV Studio release.

**D-058 is now the active release-hardening boundary inside Stage 9 and remains Proposed.** The current implementation:

- replaces the release-profile media acquisition with official Shotcut portable `26.4.30`, pinned by SHA-256;
- keeps MLT + FFmpeg as one upstream-built Windows runtime closure rather than mixing unproven DLL sets;
- adds `tools/audit_ffmpeg_release.py`, which executes the exact selected `ffmpeg.exe -buildconf` and rejects `--enable-nonfree` fail-closed;
- stages bounded `legal/ffmpeg-buildconf.json` before D-044 manifests the payload;
- switches Node acquisition from a bare executable to the official Node 24.19.0 Windows ZIP, verifies its SHA-256 and stages the complete upstream `LICENSE` from the same archive;
- stages the UV Studio license, current third-party notices and exact runtime profile under manifest-owned `legal/` paths;
- updates third-party notices so the shipped MLT `melt` GPL boundary and FFmpeg build-specific obligations are explicit instead of describing the media stack generically as LGPL.

D-058 is accepted only after the exact Shotcut carrier passes archive hash validation, executable buildconf audit, `melt`/FFmpeg/FFprobe execution, D-044 integrity, packaged browser/diagnostics behavior, installer/update/rollback and all permanent CI checks.

## Remaining release blockers

1. **D-058 exact-head proof and final redistribution evidence.** The replacement carrier must pass the complete product/release workflow and required source/license/notice obligations for the actual shipped payload must be recorded.
2. **D-057 exact-head acceptance.** Constrained-host/long-project implementation must be backed by a complete current permanent CI run.
3. **Windows artifact signing.** The roadmap requires signed release artifacts. No signing credential/service is assumed or fabricated; Stage 9 remains Draft until a real signing path and evidence exist.
4. **Final release/security/dependency audit and checksums.** This must describe the exact review payload, not an earlier candidate.
5. **Context/review transition.** PR body, decisions and project state must identify the final exact review head and its green evidence before `draft -> review`.

## Preserved invariants

- Project Store remains canonical; runtime/provider state never replaces project truth.
- Provider/model IDs remain adapter/runtime concerns rather than canonical semantics.
- Paid/remote execution stays optional and explicit under D-017.
- FFmpeg/MLT execution remains bounded to project-owned verified media and packaged executables are manifest-owned.
- MuseTalk remains optional/fail-closed under D-043 and is not a baseline desktop dependency.
- Chat-first review plus ordinary GitHub CI remain readiness authority under D-040.
- Stage 9 remains one PR/slice; internal release research and hardening are evidence within this lifecycle, not competing active slices.

## Completion gate

Stage 9 may move to review only after D-057/D-058 are accepted on exact evidence, signing and final redistribution/security audit are present, the packaged Windows installer/update/recovery flows remain green, and the exact review head passes all five permanent required checks plus the Stage 9 Windows Release workflow.

After merge, the repository must atomically return to green `idle` on `main` before `post-roadmap-release-maintenance` begins.
