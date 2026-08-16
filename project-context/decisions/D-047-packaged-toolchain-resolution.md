# D-047 — Packaged product-owned executables never fall back to system PATH

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

D-044 makes the installed UV Studio payload exact and hash-addressed, and D-046 pins the shipping language runtimes. That guarantee would be undermined if media execution still resolved `ffmpeg`, `ffprobe`, MLT or Node from the user's ambient `PATH`: an unrelated or malicious executable could shadow the reviewed packaged component while the release manifest remained perfectly valid.

Historically, development adapters correctly used `shutil.which` because FFmpeg/MLT were developer-provisioned dependencies. Stage 9 needs a different installed-product boundary without rewriting the existing bounded FFmpeg argv and project-path semantics.

## Decision

`uv_studio.toolchain` is the product-owned executable resolver.

In **development mode** (`UV_STUDIO_RELEASE_ROOT` absent), current behavior remains compatible: explicit test/developer paths are accepted after resolving to regular non-symlink files and otherwise the tool may be discovered through the supplied PATH lookup.

In **packaged mode**:

- the D-044 `release-manifest.json` is loaded;
- the entire immutable payload receives deep SHA-256 verification once per process/release-manifest identity;
- component entrypoints are resolved under the release root and must be regular files;
- `ffmpeg`, `ffprobe`, `melt` and `node` map only to their exact manifest components;
- ambient system `PATH` is not consulted for these product-owned executables;
- an explicit override is accepted only if it resolves to the same verified component path;
- corrupt/missing/unlisted/substituted release payloads fail closed rather than falling back to a system tool.

The local FFmpeg package facade injects exact verified `ffmpeg` and `ffprobe` paths into the existing bounded adapter delegate. Existing media command construction therefore remains unchanged.

The capability registry also re-projects every `local_ffmpeg` offer in packaged mode from verified release readiness instead of the legacy development PATH probe. A healthy release enables those local deterministic offers even on a clean machine with no system FFmpeg. A corrupted release marks them unavailable even if a system PATH contains a working executable.

## Cache and mutation boundary

Deep payload verification is cached for the lifetime of a normal product process using the release root and manifest file identity. Stage 9 treats an installed application payload as immutable while running; updates/recovery must stage a new payload and activate it through process restart rather than mutate the active release in place.

This does not claim to solve arbitrary hostile in-place filesystem TOCTOU after a successful verification. D-025/D-043-style exact input/runtime checks remain the pattern for security-sensitive optional runtimes, and future stronger OS-level immutable/install permissions can further reduce that surface.

## Consequences

- A clean Windows machine does not need FFmpeg/FFprobe/MLT on PATH once the release bundle contains them.
- A user's unrelated FFmpeg installation can no longer change UV Studio render behavior in packaged mode.
- Capability availability and execution use the same release trust source instead of disagreeing about PATH.
- Installer/update/recovery must preserve exact component paths declared in the manifest and restart the product after payload activation.
- Optional independently installed tools not declared as product-owned components keep their own adapter-specific verification rules; this decision does not silently make arbitrary external binaries part of the baseline release.
