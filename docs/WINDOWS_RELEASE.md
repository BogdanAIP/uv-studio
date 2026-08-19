# UV Studio Windows release guide

This guide describes the Stage 9 Windows product boundary implemented by the repository. It documents installation and recovery behavior; it does not by itself mean that a candidate artifact has passed the public signing and publication gates.

## Installation and first launch

UV Studio uses a per-user NSIS installation. Administrator rights are not required for the intended install path.

The immutable application root is:

```text
%LOCALAPPDATA%\Programs\UV Studio
```

Each installed build lives under a versioned directory:

```text
%LOCALAPPDATA%\Programs\UV Studio\versions\<release-id>
```

The active version is selected by:

```text
%LOCALAPPDATA%\Programs\UV Studio\current-release.txt
```

The installer verifies the copied release payload before activating that version. It creates both a Start Menu entry and a desktop shortcut for the current user. Both shortcuts start the frozen UV Studio supervisor.

The supervisor starts the local frozen backend and bundled Next frontend, waits for them to become healthy, and then starts the manifest-owned Rust desktop host. The host renders the product UI in a dedicated Windows window through Microsoft Edge WebView2 at the private loopback origin `http://127.0.0.1:3000`. The normal product launch does not open a browser tab or expose browser chrome.

WebView2 Evergreen Runtime is a Windows machine prerequisite rather than a bundled second Chromium. UV Studio checks it fail-closed; if it is unavailable the native host exits with an actionable Windows error instead of silently changing to a browser-based product surface.

Closing the native UV Studio window ends the desktop host. The frozen supervisor then shuts down the bundled frontend and backend children so normal window close does not leave local UV Studio services running.

## User data

Mutable data is intentionally outside the immutable application root:

```text
%LOCALAPPDATA%\UV Studio
```

Important locations are:

```text
%LOCALAPPDATA%\UV Studio\projects
%LOCALAPPDATA%\UV Studio\config
%LOCALAPPDATA%\UV Studio\logs
%LOCALAPPDATA%\UV Studio\recovery\migrations
%LOCALAPPDATA%\UV Studio\webview2
```

The `webview2` directory contains browser-engine profile/cache data for the native product window. It is machine-local presentation state and is not canonical project state. Projects and configuration therefore do not belong to a specific installed application version.

## Updates and rollback

Stage 9 uses the versioned installer as the update and rollback carrier. A new release is copied into its own version directory, verified, and only then selected as current. An older verified release can be selected again without rewriting project data.

Project-schema maintenance is fail-closed. Before a migration mutates project files, UV Studio prepares the migration plan and recovery material. Migration recovery snapshots are stored under:

```text
%LOCALAPPDATA%\UV Studio\recovery\migrations
```

If preparation or migration fails, the application must not silently publish a partially migrated canonical project.

## Diagnostics

Use the in-product **Diagnostics** page for packaged-runtime health. Packaged diagnostics report the frozen runtime, release-manifest integrity and the product-owned media-tool resolution used by the application.

For troubleshooting, inspect:

```text
%LOCALAPPDATA%\UV Studio\logs
```

Installer verification failures may also leave diagnostic material there so a rejected release can be investigated without activating it.

## Media, language and desktop runtimes

The Stage 9 package carries the runtime components selected by the release manifest. A packaged application must not silently fall back to a system FFmpeg, FFprobe or MLT executable when a manifest-owned executable is required.

The Rust desktop host is also an immutable release-manifest component. Its release build is pinned by the product release profile, committed `desktop-host/Cargo.lock`, and Cargo `--locked`; exact Cargo package metadata and license material are staged under `legal/desktop-rust/` before D-044 hashing.

The user should not need to install Python, Node/npm, Rust, FFmpeg, FFprobe or MLT separately for the packaged Windows product. Rust is build-time only. WebView2 Evergreen Runtime is the Windows presentation runtime prerequisite described above.

## Uninstall

Uninstall removes the installed application root, Start Menu group and UV Studio desktop shortcut. It intentionally preserves mutable user data under:

```text
%LOCALAPPDATA%\UV Studio
```

This prevents uninstalling the application from deleting projects, configuration, WebView2 presentation state or recovery material. Delete that directory manually only when the data is no longer needed and after making any desired backup.

## Release integrity and trust

`release-manifest.json` is the product-owned immutable payload inventory. Deep verification checks the exact files, sizes and SHA-256 identities represented by the release before activation and during packaged diagnostics.

Public trust is a separate publication gate. Under D-059, both UV-owned Windows executables (`backend/uv-studio-backend.exe` and `desktop/uv-studio-desktop.exe`) plus the installer/uninstaller surfaces are to be signed with Authenticode and a trusted RFC3161 timestamp, while bundled third-party binaries are not re-signed. Public SHA-256 checksums are generated only after signing and all other payload mutations are complete.

Do not treat an unsigned development or CI candidate as a publicly trusted release merely because its internal release manifest verifies successfully.
