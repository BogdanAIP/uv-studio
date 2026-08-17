# D-050 — Per-user versioned Windows installation with deep verification before activation

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The Stage 9 portable payload now has a product-owned release manifest, immutable/mutable boundary and a single frozen desktop launcher. A normal user must not need to unpack archives, install Python/Node/FFmpeg, use a terminal or grant administrator rights merely to install UV Studio.

The installer also cannot make the release payload mutable in-place. Future updates and rollback require release identities to remain distinguishable, while uninstall must not destroy canonical projects, configuration or recovery data under the D-045 user-data root.

## Decision

UV Studio uses NSIS for the Windows x86_64 installer build. The release build pins the NSIS compiler version and acquisition hash as build-only provenance; NSIS is not an application runtime dependency.

Installation is per-user and requests the normal user execution level. The stable installation root is:

`%LOCALAPPDATA%/Programs/UV Studio`

Immutable releases are stored side by side under:

`%LOCALAPPDATA%/Programs/UV Studio/versions/<release-id>`

The release ID is supplied by the controlled release build and combines product/build identity using a Windows-path-safe representation. The Start Menu shortcut points directly to the selected release's manifest-owned frozen launcher. `current-release.txt` is activation metadata for installer/updater coordination; it is never a substitute for D-044 payload identity.

### Verify before activation

Copying files is not sufficient evidence that an installed release is trustworthy. The frozen launcher exposes a private `--verify-release` command which:

1. infers the release root from its own executable;
2. requires that the executable is the manifest-owned backend/launcher entrypoint;
3. performs a complete D-044 SHA-256 verification;
4. exits non-zero without launching services if verification fails.

The installer copies a new immutable version first and invokes this deep verifier before writing `current-release.txt`, replacing the Start Menu shortcut or exposing the release as current. A failed verification removes the rejected version directory and terminates installation with a non-zero result.

Reinstalling the exact same release ID may reuse the existing version only when the same deep verifier accepts it. A corrupt existing directory is removed and reinstalled from the installer payload.

### Uninstall and user data

The uninstaller removes only the stable application root, versioned immutable payloads, user-scoped uninstall registration and Start Menu shortcuts. It deliberately does **not** delete `%LOCALAPPDATA%/UV Studio` or any valid D-045 override. Canonical projects, configuration, secrets, backups and recovery state therefore survive uninstall by default.

User-data deletion, if later offered, must be a separate explicit destructive action with its own confirmation and backup/recovery semantics; it is not an uninstall side effect.

### Update compatibility

The versioned layout is the foundation for the Stage 9 updater/rollback work. A future updater may stage and deep-verify a new sibling version, atomically switch activation metadata/shortcuts, retain a previous verified version for rollback and clean older inactive versions according to policy. It must not patch the active immutable release in place.

## Consequences

- Normal installation does not require UAC/admin access or machine-wide registry writes.
- Multiple immutable release versions can coexist without mixing runtime files.
- Installer success requires post-copy cryptographic verification by UV Studio itself.
- Uninstall is safe for user projects and recovery data by construction.
- Build CI must prove silent install, deep verification, real desktop smoke, silent uninstall, application-root removal and user-data preservation on a clean Windows runner.
- Code signing remains a separate release gate: unsigned development/PR installers may be built for verification, while production publication must fail closed when the required signing identity is unavailable.
