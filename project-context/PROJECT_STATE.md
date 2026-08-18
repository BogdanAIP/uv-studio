# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-9-desktop-productization-release-hardening -->

## Current lifecycle

Stage 9 Desktop Productization & Release Hardening is the single active draft slice in PR #38 on `stage-9/desktop-productization-release-hardening`, based on exact green idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8 merged as PR #37.

The branch remains **Draft**. Productization is substantially implemented and both Stage 9 evidence decisions are now accepted:

- D-057 constrained-host/long-project evidence — **Accepted**;
- D-058 redistributable Windows media runtime boundary — **Accepted** on exact head `6060f620fe6f0751496e98ba85e5405ece3613a7`.

The remaining blockers before `draft -> review` are real Windows artifact signing and the final whole-payload release/security/dependency/license audit, followed by post-signing checksums and one exact review-head proof.

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
- **D-057 constrained-host/long-project evidence**, accepted with 2,000+2,000 Project Store scale evidence and real ten-minute media work;
- **D-058 redistributable Windows media boundary**, accepted with exact Shotcut/FFmpeg/MLT runtime closure, component provenance and hash-pinned license/notice payload;
- **release checksum generator** — deterministic fail-closed `SHA256SUMS` writer/verifier committed and tested, intentionally reserved for the post-signing publication step.

## D-057 acceptance evidence

D-057 is **Accepted**. Exact head `e1fba386f5fefd46806317a844023169e7ecacc7` proved:

- coarse secret-safe logical CPU / total+available RAM diagnostics with fail-soft OS probes;
- no hostname/user/process/environment/path inventory in resource diagnostics;
- 2,000 source + 2,000 artifact Project Store round-trip/load/JSON evidence under a bounded traced Python allocation envelope;
- real ten-minute CPU-only media with extraction near 598–600 seconds through `LocalFFmpegAdapter`;
- Linux and Windows application baselines, both bootstraps, shipping-Python/runtime compatibility and frontend compatibility;
- Stage 9 Windows Release #112 / run `32107133982` including packaged execution, clean-machine install/uninstall and A -> B -> A rollback;
- fresh CI #1758 / run `32109010491` passing `development-context` after the PR journal was restored to the required six-section contract.

D-056 cancellation remains the bounded escape path for work that is too expensive on a constrained host; D-057 does not invent a universal RAM/CPU minimum.

## D-058 acceptance evidence

D-058 is **Accepted** on exact head `6060f620fe6f0751496e98ba85e5405ece3613a7`.

The accepted media boundary contains:

- official Shotcut portable `26.4.30` carrier SHA-256 `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`;
- official `shotcut-src-26.4.30.txz` corresponding-source SHA-256 `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`;
- exact FFmpeg `n8.1-11-g75d37c499d`, with machine-audited `nonfree_enabled=false` and `legal/ffmpeg-buildconf.json` included before D-044;
- exactly four MLT runtime modules: `libmltavformat.dll`, `libmltcore.dll`, `libmltqt6.dll`, `libmltxml.dll`;
- exact media closure of **446 files / 128,695,917 bytes (122.73 MiB)**;
- **52 retained PE binaries** mapped exactly once into **28 component groups** by `packaging/media-runtime-components.windows-x86_64.json`;
- **27 exact license/notice assets** covering all 28 component groups by `packaging/media-runtime-license-files.windows-x86_64.json`;
- mandatory SHA-256 pinning for all 27 license assets;
- corrected `liblzma-5.dll` licensing scope of `0BSD` based on the upstream XZ 5.8.3 liblzma boundary;
- fail-closed unknown/duplicate PE, incomplete provenance, changed license bytes, unsafe paths and partial legal staging.

Acceptance evidence:

- CI #1788 / run `32139063217`: **completed / success** across every permanent job;
- Stage 9 Windows Release #142 / run `32139063188`: **completed / success** through exact acquisition, pinned license staging, D-044 build/deep verification, tamper rejection, packaged media/frontend/backend execution, desktop supervision, installer, silent install/uninstall and A -> B -> A rollback;
- Windows Release #142 artifact id `9325376444`, digest `sha256:e676ab832c7f5c536d6f1783051c895505a9b8bf932d98f9831f6cf95e901446`;
- direct artifact inspection confirmed **27/27** expected license files, **27/27** pinned SHA matches and **27/27** corresponding D-044 file/hash entries.

The former Kdenlive carrier remains rejected historical evidence because its exact FFmpeg self-report contained `--enable-nonfree`.

## Remaining release blockers

1. **Real Windows artifact signing.** No signing identity/service is fabricated. UV-owned executable/installer signing needs a real public trust path and exact verification evidence.
2. **Final whole-payload release/security/dependency/license audit.** D-058 closes the media-runtime redistribution boundary, not every dependency or release obligation in the complete product.
3. **Post-signing release checksums.** `tools/write_release_checksums.py` is ready, but `SHA256SUMS` must be generated only after signing because signing modifies executable bytes.
4. **Exact review-head evidence and context transition.** PR body, decisions and state must identify the final signed/audited head and green permanent checks before PR #38 changes from Draft to Review.

## Signing/publication boundary

The required publication order remains:

`build -> final immutable runtime -> sign UV-owned binaries -> build/sign installer as applicable -> verify Authenticode -> SHA256SUMS -> publish`

Third-party FFmpeg/MLT/Qt/runtime DLLs are not to be silently re-signed with a UV identity merely because they are carried in the installer.

Self-signed certificates are not accepted as public-release evidence.

## Preserved invariants

- Project Store remains canonical; runtime/provider state never replaces project truth.
- Provider/model IDs remain adapter/runtime concerns rather than canonical semantics.
- Paid/remote execution stays optional and explicit under D-017.
- FFmpeg/MLT execution remains bounded to project-owned verified media and packaged executables are manifest-owned.
- Shotcut is only an acquisition carrier, not a second editor authority.
- MuseTalk remains optional/fail-closed under D-043 and is not a baseline desktop dependency.
- Chat-first review plus ordinary GitHub CI remain readiness authority under D-040.
- Stage 9 remains one PR/slice; release research and hardening are evidence within this lifecycle, not competing active slices.

## Preserved post-Stage-9 direction

The provider-neutral UV Character Asset design for image **and video** continuity remains recorded in `docs/uv-character-asset-design.md` and `project-context/NEXT_TASK.md`. It is intentionally not mixed into Stage 9 product code.

## Completion gate

Stage 9 may move to review only after real Windows signing and the final whole-payload audit are present, post-signing checksums are produced from the exact signed bytes, the packaged installer/update/recovery flows remain green, and the exact review head passes all permanent required checks plus Stage 9 Windows Release.

After merge, the repository must atomically return to green `idle` on `main` before `post-roadmap-release-maintenance` begins.
