# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-9-desktop-productization-release-hardening -->

## Current lifecycle

Stage 9 Desktop Productization & Release Hardening is active in draft on `stage-9/desktop-productization-release-hardening`, based on exact green idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8 Additional Recipes merged as PR #37 (`5eb8f6c2256b9b67dd1e896fc929682eb19b16ca`).

The Stage 8 post-merge idle CI #1614 / Actions run `31971649798` passed all five permanent required jobs on that exact base, including cross-platform bootstrap, API/HTTP, real-media, frontend build and Playwright user outcomes.

Stage 9 draft PR #38 is the single active implementation slice. Internal productization phases remain commits/evidence inside this PR rather than separate lifecycle PRs.

## Stage 9 product goal

Produce a native Windows release that a user can install and run without separately preparing Python, Node/npm or FFmpeg, while preserving the canonical Project Store, portable archives, semantic capability boundaries and all permanent user-facing regression scenarios.

Stage 9 must cover the complete release surface rather than only a development launcher:

- reproducible product-owned Python and frontend dependency resolution;
- a versioned self-contained release layout and runtime manifest;
- bundled/provisioned required media binaries with provenance and diagnostics;
- launcher/process supervision and clean shutdown/cancellation behavior;
- installer/uninstaller plus versioned update and project migration behavior;
- backup/recovery and user-readable diagnostics;
- capability self-checks for required and optional dependencies;
- clean-machine Windows evidence plus representative weak-hardware/long-project evidence;
- final license/security/dependency audit and signed release artifacts;
- packaged-app proof for the permanent browser/user outcomes.

## Release architecture fixed so far

D-044 defines the immutable product-owned release payload. `release-manifest.json` schema v1 records product/build/target identity, the exact baseline component set and a complete sorted file inventory with byte sizes and SHA-256. Manifest parsing rejects non-canonical/traversing paths, duplicate/missing components, missing entrypoints and unsupported targets. Release verification rejects symlinks, missing payloads, unlisted extra files and size mismatches; deep verification detects same-size SHA-256 substitution.

Secret-safe diagnostics distinguish development from packaged mode, report manifest/component/integrity state and required media-tool availability without dumping environment variables, provider credentials or arbitrary absolute developer tool paths. The same diagnostics/manifest code is exposed through the product API and `tools/uv_release.py`.

D-045 separates mutable installed state from the immutable release payload. Development keeps repository-local `data/projects` and `data/config`; packaged mode defaults to `%LOCALAPPDATA%/UV Studio/projects` and `%LOCALAPPDATA%/UV Studio/config`, with explicit user/admin overrides retained. Project/config roots cannot overlap vendor, the release payload or one another. `RuntimeConfigStore` applies the same boundary even to explicit constructor paths.

D-046 pins the first Windows x86_64 shipping language runtimes only after dedicated compatibility proof: CPython 3.13.14 passed the complete unit contract and Node.js 24.19.0 passed locked frontend install/lint/audit/build. `requirements-uv-release-win-x86_64.txt` contains the exact 32-package Python shipping graph; `packaging/runtime-profile.windows-x86_64.json` records exact Python/Node versions. The release Python CI installs through the lock and rejects wrong Python versions, package drift or unmanaged runtime packages.

D-047 makes release-manifest executable identity authoritative in packaged mode. The local FFmpeg facade receives manifest-verified `ffmpeg`/`ffprobe` paths, and packaged capability availability is projected from the same verified release toolchain rather than development PATH. A system PATH shadow must not become an execution fallback; release corruption must make the local capability unavailable. Deep release verification is cached per immutable running payload, with update/recovery expected to activate a new payload through process restart rather than mutate the active installation.

The current frontend remains Next.js with dynamic `/projects/[projectId]`; Stage 9 therefore uses the official standalone-server path rather than assuming static export. The user-facing contract is no separately prepared Node/npm: a versioned Node runtime may be bundled until equivalent routing is proven without it.

## Current evidence

The runtime-lock head `beda2a39bd9cf3400a4ffbd93a46c424576d56c4` has green `development-context`, both bootstrap jobs, the exact Python 3.13.14 release-runtime gate and exact Node 24.19.0 release-frontend gate. Both Ubuntu and Windows real-media steps also passed while the remaining permanent browser tails continued.

Python 3.13.14 Windows evidence includes successful server import, `pip check`, all 379 unit tests and the captured 32-package graph used by the release lock. Node 24.19.0 Windows evidence includes `npm ci`, lint, high-severity audit and production Next build.

## Next implementation layers

1. Complete packaged toolchain execution/availability evidence on the current head.
2. Enable/stage official Next standalone output and prove arbitrary project routes with the bundled Node 24 runtime.
3. Build a Windows one-folder backend bundle on CPython 3.13.14 with build tooling kept outside the installed runtime graph.
4. Stage the pinned FFmpeg/FFprobe/MLT dependency closure and assemble one complete Windows release folder under D-044.
5. Launch backend + frontend from that folder with no repository/system Python/Node/npm/FFmpeg dependency and run packaged HTTP/browser outcomes.
6. Add launcher/process supervision, logs, cancellation/shutdown, backup/recovery and version/migration state.
7. Build installer/uninstaller and staged update/recovery on top of the verified release folder.
8. Finish clean-machine/weak-hardware evidence, license/security audit, checksums/signing and final packaged regressions.

## Preserved invariants

- Project Store remains canonical; generated/runtime/provider state does not replace project truth.
- External model/provider IDs remain adapter/runtime concerns, not canonical project semantics.
- Paid/remote execution remains optional and explicit under D-017.
- Existing FFmpeg/MLT and Stage 8 execution boundaries remain bounded to project-owned verified media.
- MuseTalk remains optional and fail-closed under D-043; its large runtime/model pack is not a baseline desktop dependency.
- Chat-first review plus permanent CI remain readiness authority under D-040.
- Stage 9 is one active development slice/PR; internal productization phases are commits/evidence within that slice, not parallel lifecycle slices.

## Completion gate

Stage 9 may move to review only after the packaged product is proven through required Windows release/installer flows, existing permanent user outcomes remain green, project backup/upgrade/recovery behavior is demonstrated, release diagnostics and security/license evidence are present, and the exact review head passes all permanent required checks.

After Stage 9 is merged and atomically closed to a green idle `main`, roadmap-driven development hands off to `post-roadmap-release-maintenance` for release feedback, security/compatibility maintenance and explicitly scoped future enhancements.
