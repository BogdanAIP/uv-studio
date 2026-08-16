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

## Initial architecture direction

The current frontend is Next.js and still contains the dynamic `/projects/[projectId]` route. Its development configuration uses a Next rewrite to proxy `/api/uv/*` to the FastAPI backend. Therefore Stage 9 will not assume that a static export can replace the runtime without first proving routing compatibility.

The release contract is user-facing, not implementation-facing: the user must not need a system Python, Node/npm or FFmpeg. A release may initially carry its own pinned/versioned runtimes inside the installed product if that preserves routing and behavior more safely. Removing a bundled Node runtime is desirable only if the frontend can be exported/served by UV Studio without breaking arbitrary project routes or browser outcomes.

The packaging boundary must remain fail-closed and locally auditable. Bundled executables and runtime payloads need explicit version/provenance information; optional WSL/cloud/provider integrations must not become prerequisites for normal native-Windows startup.

## Implemented Stage 9 foundation

D-044 defines the product-owned immutable release payload boundary. `release-manifest.json` schema v1 records product/build/target identity, the exact baseline component set and a complete sorted file inventory with byte sizes and SHA-256. Manifest parsing rejects non-canonical/traversing paths, duplicate/missing components, missing entrypoints and unsupported targets. Release verification rejects symlinks, missing payloads, unlisted extra files and size mismatches; explicit deep verification also detects same-size SHA-256 substitution.

Secret-safe diagnostics distinguish development from packaged mode, report manifest/component/integrity state and required media-tool availability without dumping environment variables, provider credentials or arbitrary absolute developer tool paths. The same diagnostics/manifest code is exposed to the product API and the Stage 9 release utility so launcher, installer, support and CI can converge on one contract.

D-045 separates mutable packaged state from the immutable release payload. Development keeps repository-local `data/projects` and `data/config`; packaged mode defaults to `%LOCALAPPDATA%/UV Studio/projects` and `%LOCALAPPDATA%/UV Studio/config`, with explicit `UV_STUDIO_USER_DATA_DIR`, `UV_STUDIO_PROJECTS_DIR` and `UV_STUDIO_CONFIG_DIR` overrides retained. Project/config roots must not overlap vendor, the configured release payload or one another.

This foundation deliberately does not make repository `PATH` discovery authoritative for packaged media. The actual packaged launcher must resolve trusted component entrypoints from the verified release manifest.

## Release-hardening priorities

1. Replace broad Python runtime ranges with a reproducible release dependency graph while keeping provider/optional ML runtimes outside the baseline.
2. Define a machine-readable release manifest and diagnostics contract before building an installer around opaque files. **Foundation implemented; packaging integration and CI proof remain.**
3. Package backend/frontend/media prerequisites into a deterministic Windows release layout and test it without relying on repository development paths.
4. Add launcher supervision, logs, cancellation/shutdown, backup/recovery and version/migration checks before installer/update UX is declared complete.
5. Build installer/uninstaller and update/recovery flows only on top of the verified release layout.
6. Extend CI with packaged-app and clean-machine-oriented evidence while retaining all permanent existing gates.
7. Finish with license/security/dependency review, artifact integrity metadata and signing/release documentation.

## Preserved invariants

- Project Store remains canonical; generated/runtime/provider state does not replace project truth.
- External model/provider IDs remain adapter/runtime concerns, not canonical project semantics.
- Paid/remote execution remains optional and explicit under D-017.
- Existing FFmpeg/MLT and Stage 8 execution boundaries remain bounded to project-owned verified media.
- MuseTalk remains optional and fail-closed under D-043; its large runtime/model pack is not a baseline desktop dependency.
- Chat-first review plus permanent CI remain readiness authority under D-040.
- Stage 9 is one active development slice/PR; internal productization phases are commits/evidence within that slice, not parallel lifecycle slices.

## Completion gate

Stage 9 may move to review only after the packaged product is proven through the required Windows release/installer flows, existing permanent user outcomes remain green, project backup/upgrade/recovery behavior is demonstrated, release diagnostics and security/license evidence are present, and the exact review head passes all permanent required checks.

After Stage 9 is merged and atomically closed to a green idle `main`, roadmap-driven development hands off to `post-roadmap-release-maintenance` for release feedback, security/compatibility maintenance and explicitly scoped future enhancements.
