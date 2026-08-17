# D-052 — Curated Windows media payload excludes upstream Qt test/build artifacts

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The Stage 9 Windows release acquires the exact pinned Kdenlive standalone distribution because it is a proven carrier for compatible FFmpeg, FFprobe, MLT binaries, plugins and runtime data. Earlier staging copied that entire extracted distribution into the immutable UV Studio payload.

That correctness-first carrier also contains files that are not application runtime dependencies. A real per-user NSIS installation exposed one such subtree under `bin/Qt/test/**`: Qt test/build object files, including deeply nested `*.obj` output, were present in the source release manifest but were not reproduced by the installer. D-044 correctly rejected the installed payload before activation.

UV Studio must not solve this by disabling integrity checks, silently accepting partial installs, or requiring users to enable Windows long-path policy merely to ship upstream test/build artifacts.

## Decision

The exact Kdenlive standalone archive remains the pinned acquisition source, but the UV Studio Windows shipping payload is a curated runtime payload rather than a byte-for-byte copy of every upstream file.

The first exclusion is intentionally narrow and evidence-based:

`**/bin/Qt/test/**`

This removes Qt test/build material only. Normal Qt runtime plugins/data, FFmpeg, FFprobe, MLT, DLLs and the rest of the acquired distribution remain staged unless a future accepted decision proves another exclusion safe.

The staging implementation:

1. validates the complete acquired media tree for symlinks/non-regular files before applying exclusions;
2. rejects any required FFmpeg/FFprobe/MLT entrypoint that would fall inside an exclusion;
3. copies all non-excluded files without PATH/system-runtime fallback;
4. reports the exact exclusion rule and excluded file count as release evidence;
5. leaves D-044 to inventory and hash the resulting curated immutable payload.

A removal rule may not be broadened merely because a path contains words such as `test`, `debug`, `docs`, or a build-looking extension. Each additional exclusion requires runtime evidence and a recorded product decision.

### Windows install-path budget

Stage 9 also introduces a release analyzer that evaluates every manifest-owned final installed path under the real per-user versioned layout against the classic Windows path budget. This is a product compatibility gate, not permission to weaken the release manifest. UV Studio should install without requiring a user or administrator to change the machine-wide long-path policy.

## Verification

The release gate must continue to prove, using the curated payload:

- FFmpeg and FFprobe execute from manifest-owned paths;
- MLT `melt` executes with its packaged plugins/data;
- D-044 full deep verification succeeds before installer creation;
- same-size payload substitution still fails closed;
- frozen backend + standalone frontend packaged E2E succeeds;
- desktop supervisor smoke succeeds;
- the compiled NSIS installer silently installs the same manifest payload;
- the installed release passes its own D-044 deep verifier before activation;
- installed desktop smoke succeeds;
- uninstall removes immutable application state while preserving D-045 user data.

## Consequences

- The Kdenlive standalone package is an acquisition/provenance carrier, not the canonical definition of UV Studio's shipping file set.
- Upstream Qt test/build objects no longer inflate or constrain the Windows product installation.
- Integrity remains strict because the release manifest is built **after** curation and the installer must reproduce that exact curated payload.
- The media payload can be narrowed further later, but only from runtime dependency and licensing evidence rather than speculative pruning.
- This decision reduces installer size/path surface and also narrows the set that must be covered by final redistribution/license review.
