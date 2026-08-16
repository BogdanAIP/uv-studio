# D-045 — Packaged mutable state lives outside the immutable release payload

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Before Stage 9, UV Studio intentionally stored development projects and machine configuration under repository-local `data/projects` and `data/config`. That is convenient for isolated source-tree development, but it is not a valid installed-product default: an application payload may be installed under a protected directory, updates may replace it, and D-044 now treats the release payload as an immutable exact inventory.

Canonical project state, runtime configuration and provider secrets are mutable user data. Letting any of them live inside the verified application payload would either make ordinary use invalidate the release manifest or encourage the installer/updater to overwrite user-owned state.

## Decision

Development and packaged runs have different default mutable-data roots while preserving existing explicit environment overrides.

### Development mode

When `UV_STUDIO_RELEASE_ROOT` is absent/blank, the historical repository-local defaults remain:

- `ROOT/data/projects`
- `ROOT/data/config`

This keeps development/test state isolated from a user's installed product profile.

### Packaged mode

When `UV_STUDIO_RELEASE_ROOT` is configured, the application payload is immutable and default mutable state moves outside it.

The packaged user-data root is resolved in this order:

1. explicit `UV_STUDIO_USER_DATA_DIR` override;
2. `%LOCALAPPDATA%/UV Studio` when `LOCALAPPDATA` is available (the normal Windows release path);
3. `$XDG_DATA_HOME/uv-studio` for portable non-Windows validation;
4. `~/.local/share/uv-studio` fallback.

The default packaged locations are:

- `<user-data-root>/projects`
- `<user-data-root>/config`

Existing `UV_STUDIO_PROJECTS_DIR` and `UV_STUDIO_CONFIG_DIR` remain higher-priority exact overrides for administrators, portable installs and future UX-selected storage locations.

## Safety rules

Mutable Project Store/configuration roots must not overlap:

- the vendored source/runtime compatibility tree;
- the configured immutable release root;
- each other, in either ancestor/descendant direction.

These are startup/configuration errors rather than silent relocation. A bad override must fail closed so project files, secrets or machine state cannot be mixed into application code or into one another.

## Migration and updates

This decision establishes the location boundary, not the complete Stage 9 backup/update system.

The first packaged release has no older installed UV Studio data-layout version to migrate from. Future packaged updates must treat the user-data root as persistent across app-payload replacement and add explicit versioned data migrations before changing stored schemas or locations.

Repository-development projects are not silently copied into the installed profile: development and installed product state are deliberately separate. Existing project archive export/import remains the explicit portable transfer mechanism until Stage 9 adds user-facing backup/recovery tooling.

## Consequences

- Installing under Program Files or another protected app directory no longer implies writing projects/secrets there.
- Replacing or recovering the immutable release payload does not itself delete canonical user data.
- D-044 exact release inventory remains stable during normal editing/configuration use.
- Development behavior remains compatible unless packaged mode is explicitly enabled.
- Stage 9 still needs launcher-created directories/permissions, backup/recovery UX, versioned data-layout markers and packaged clean-machine evidence.
