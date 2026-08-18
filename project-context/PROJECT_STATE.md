# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-9-desktop-productization-release-hardening -->

## Current lifecycle

Stage 9 Desktop Productization & Release Hardening is the single active draft slice in PR #38 on `stage-9/desktop-productization-release-hardening`, based on exact green idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8 merged as PR #37.

The branch remains **Draft**. Productization is substantially implemented. D-057 is accepted; D-058 source-provenance acceptance, final exact-payload release/security audit and real Windows signing remain before review.

## Product goal

Ship a native Windows product that requires no separately prepared Python, Node/npm, FFmpeg or MLT while preserving canonical projects, archives, capability authorization, user data and all permanent user-facing workflows through packaged execution.

## Implemented and proven Stage 9 foundation

- **D-044 immutable release manifest** — complete sorted payload inventory with size/SHA-256, path/symlink rejection and deep same-size tamper detection;
- **D-045 packaged mutable-state boundary** — immutable application payload separated from `%LOCALAPPDATA%/UV Studio` projects/config/logs;
- **D-046 exact release input profile** — CPython 3.13.14, exact 32-package shipping graph, Node.js 24.19.0, pinned binary/source media coordinates and build-tool identities;
- **D-047 packaged toolchain resolution** — FFmpeg/FFprobe/MLT resolve only from verified manifest-owned paths;
- **D-048 official Next standalone frontend** with dynamic project routes and bundled Node runtime;
- **D-049 desktop launcher supervision** for frozen backend + standalone frontend lifecycle;
- **D-050 per-user versioned NSIS installation** with deep verification before activation;
- **D-051 fail-closed project migration preparation/recovery**;
- **D-052 evidence-based media-payload curation rule**;
- **D-053 installer-carried A -> B -> A update/rollback** while preserving user data;
- **D-054 secret-safe diagnostics/recovery health**;
- **D-055 installed clean-machine proof** with host Python/Node/FFmpeg/FFprobe/MLT removed from PATH;
- **D-056 cancellable local FFmpeg jobs** with process termination/reaping and no partial Project Store artifact publication;
- **D-057 constrained-host/long-project evidence**, accepted on exact head `e1fba386f5fefd46806317a844023169e7ecacc7` using CI product evidence, fresh development-context validation and Windows Release #112.

## D-057 acceptance evidence

D-057 is **Accepted**. Exact head `e1fba386f5fefd46806317a844023169e7ecacc7` proved:

- coarse secret-safe logical CPU / total+available RAM diagnostics with fail-soft OS probes;
- no hostname/user/process/environment/path inventory in resource diagnostics;
- 2,000 source + 2,000 artifact Project Store round-trip/load/JSON evidence under a bounded traced Python allocation envelope;
- real ten-minute CPU-only media with extraction near 598–600 seconds through `LocalFFmpegAdapter`;
- Linux and Windows application baselines, both bootstraps, shipping-Python/runtime compatibility and frontend compatibility;
- Stage 9 Windows Release #112 / Actions run `32107133982` including packaged execution, clean-machine install/uninstall and A -> B -> A rollback;
- fresh CI #1758 / Actions run `32109010491` passing `development-context` after the PR journal was restored to the required six-section contract.

D-056 cancellation remains the bounded escape path for work that is too expensive on a constrained host; D-057 does not invent a universal RAM/CPU minimum.

## D-058 media redistribution and source provenance

Review of the original Kdenlive 26.04.3 carrier found actual FFmpeg 8.1.1 self-report with `--enable-nonfree`; that carrier is rejected for public release.

**D-058 remains Proposed.** Current implementation and evidence:

- official Shotcut portable `26.4.30` binary carrier pinned at SHA-256 `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`;
- release-profile schema v5 also pins official `shotcut-src-26.4.30.txz` corresponding-source SHA-256 `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`;
- the corresponding-source coordinate is preserved in manifest-owned `legal/release-inputs.windows-x86_64.json` without bloating the installed payload with the 266 MB source archive;
- `tools/audit_ffmpeg_release.py` executes exact selected `ffmpeg.exe -buildconf` and rejects `--enable-nonfree` fail-closed;
- bounded `legal/ffmpeg-buildconf.json` is staged before D-044 manifests the payload;
- Node acquisition uses official Node 24.19.0 Windows ZIP and stages its complete upstream `LICENSE`;
- Stage 9 staging prunes only proven-unneeded Shotcut application/UI/helper surface (`shotcut.exe`, `share/shotcut/**`, `ffplay.exe`, `glaxnimate.exe`, `whisper-cli.exe`) while retaining the runtime closure;
- exact head `e1fba386f5fefd46806317a844023169e7ecacc7` passed Windows Release #112 with that pruned carrier, including archive/audit, FFmpeg/FFprobe/MLT execution, packaged browser/backend behavior, silent install/uninstall, clean-machine proof and A -> B -> A rollback.

D-058 may be accepted only after the schema-v5 provenance head itself passes the permanent exact-head CI and Windows Release gates and the final component-level license/source sufficiency audit confirms the actual shipped payload.

## Remaining release blockers

1. **D-058 exact-head source-provenance acceptance.** Run the schema-v5 candidate through permanent CI and Windows Release, then close the exact corresponding-source/license/notice sufficiency review for shipped GPL/LGPL components.
2. **Windows artifact signing.** No signing credential/service is assumed or fabricated; Stage 9 remains Draft until a real public code-signing path and evidence exist.
3. **Final release/security/dependency audit and checksums.** This must describe the exact review payload, not an earlier candidate.
4. **Context/review transition.** PR body, decisions and project state must identify the final exact review head and its green evidence before `draft -> review`.

## Preserved invariants

- Project Store remains canonical; runtime/provider state never replaces project truth.
- Provider/model IDs remain adapter/runtime concerns rather than canonical semantics.
- Paid/remote execution stays optional and explicit under D-017.
- FFmpeg/MLT execution remains bounded to project-owned verified media and packaged executables are manifest-owned.
- Shotcut is only an acquisition carrier, not a second editor authority.
- MuseTalk remains optional/fail-closed under D-043 and is not a baseline desktop dependency.
- Chat-first review plus ordinary GitHub CI remain readiness authority under D-040.
- Stage 9 remains one PR/slice; release research and hardening are evidence within this lifecycle, not competing active slices.

## Completion gate

Stage 9 may move to review only after D-058 is accepted on exact evidence, real Windows signing and final redistribution/security audit are present, the packaged installer/update/recovery flows remain green, and the exact review head passes all five permanent required checks plus Stage 9 Windows Release.

After merge, the repository must atomically return to green `idle` on `main` before `post-roadmap-release-maintenance` begins.
