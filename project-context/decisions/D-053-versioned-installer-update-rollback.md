# D-053 — Versioned installer as the Stage 9 update and rollback carrier

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

D-050 establishes a per-user Windows installation with immutable sibling releases under `versions/<release-id>`, post-copy D-044 deep verification and a direct Start Menu shortcut to the selected frozen launcher. D-051 separately prepares Project Store metadata before services start and rolls a failed schema migration back to exact original metadata bytes. D-052 makes the Windows media payload an explicit curated runtime payload while keeping D-044 exact after curation.

Application rollback and user-data rollback must remain separate. Re-selecting older application binaries must never silently replace projects, configuration, secrets or recovery data with older copies.

## Decision

The first Windows update mechanism is the **versioned UV Studio installer itself**. A newer signed installer is both an installation artifact and an update carrier. An older signed installer remains a rollback carrier for its own immutable release. No update operation patches the active release directory in place.

### Forward update

For an installed release `A`, installer `B` performs the D-050 transaction:

1. stage `B` as a sibling under `versions/B`;
2. deep-verify the complete installed `B` payload using `B`'s own frozen launcher;
3. if verification fails, remove the rejected `B` directory and leave `A` selected;
4. only after verification succeeds, replace activation metadata/Start Menu target with `B`;
5. retain `A` as an inactive immutable sibling for rollback.

First launch of `B` then runs D-051 Project Store preparation before backend/frontend services start. A failed D-051 migration aborts `B` startup and restores original metadata bytes; it does not mutate or delete either application release.

### Application rollback

Rollback to `A` is performed by running installer `A` again. If `versions/A` already exists, D-050 requires `A`'s own deep verifier to accept that existing payload before it can be selected again. A corrupt cached sibling is removed and restored from installer `A` before activation.

Selecting `A` again does **not** downgrade Project Store data. If `A` cannot understand the current Project Store schema, D-051 fails closed before any service starts. Application rollback therefore never becomes an implicit destructive data rollback.

### Update discovery and retention

Stage 9 does not add a resident network updater, background polling service or delta-patch format. Release discovery/download policy can be added after the roadmap as a separate signed-channel concern. The production update artifact remains a complete signed installer so clean installs and updates share the same build, signing, D-044 and install verification boundaries.

The newly selected release and at least one previously installed release may coexist. Stage 9 does not automatically delete inactive siblings during update. Uninstall remains different from update: the uninstaller removes the application root/all immutable siblings but preserves D-045 user data.

## Acceptance evidence

Windows Release run #46 on exact head `261dc2b47204b978d1113a6f49cbb8bbaee954d9` completed successfully and exercised the real curated payload through the full state machine:

1. silent clean install of release `A`;
2. product-owned D-044 deep verification and desktop smoke of `A`;
3. persistent D-045 user-data sentinel creation;
4. build/install of a distinct same-length synthetic release `B` from the exact known-good payload;
5. proof that `B` becomes selected while immutable sibling `A` remains present;
6. D-044 deep verification and desktop smoke of `B`;
7. re-run of installer `A` as rollback carrier;
8. proof that `A` is selected again while `B` remains intact and user data is unchanged;
9. desktop smoke of the reselected `A`;
10. silent uninstall proving immutable application state is removed while D-045 user data survives.

The same exact head also passed the ordinary cross-platform CI suite. The update/rollback mechanism is therefore accepted as the Stage 9 application-version transaction.

## Production publication boundary

Unsigned PR/development installers may exercise this state machine. A production update/rollback artifact must pass the Stage 9 code-signing gate before publication. Update transport must never bypass signature/integrity policy merely because an installation already exists.
