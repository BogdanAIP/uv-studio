# D-053 — Versioned installer as the Stage 9 update and rollback carrier

- **Status:** Proposed
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

D-050 establishes a per-user Windows installation with immutable sibling releases under `versions/<release-id>`, post-copy D-044 deep verification and a direct Start Menu shortcut to the selected frozen launcher. D-051 separately prepares Project Store metadata before services start and rolls a failed schema migration back to exact original metadata bytes. D-052 makes the Windows media payload an explicit curated runtime payload while keeping D-044 exact after curation.

Stage 9 still needs an update/rollback strategy. A network auto-updater is not required to prove that the desktop product can move safely between versions, and introducing a second resident service or patching engine would add a new trust boundary without improving the core safety property.

Application rollback and user-data rollback must also remain separate. Re-selecting older application binaries must never silently replace projects, configuration, secrets or recovery data with older copies.

## Proposed decision

The first Windows update mechanism is the **versioned UV Studio installer itself**. A newer signed installer is both an installation artifact and an update carrier. An older signed installer remains a rollback carrier for its own immutable release.

No update operation patches the active release directory in place.

### Forward update

For an installed release `A`, installer `B` performs the same D-050 transaction as a clean install:

1. stage `B` as a sibling under `versions/B`;
2. deep-verify the complete installed `B` payload using `B`'s own frozen launcher;
3. if verification fails, remove the rejected `B` directory and leave `A` selected;
4. only after verification succeeds, replace activation metadata/Start Menu target with `B`;
5. retain `A` as an inactive immutable sibling for rollback.

First launch of `B` then runs D-051 Project Store preparation before backend/frontend services start. A failed D-051 migration aborts `B` startup and restores original metadata bytes; it does not mutate or delete either application release.

### Application rollback

Rollback to `A` is performed by running installer `A` again. If `versions/A` already exists, D-050 requires `A`'s own deep verifier to accept that existing payload before it can be selected again. A corrupt cached sibling is removed and restored from installer `A` before activation.

Selecting `A` again does **not** downgrade Project Store data. If `A` cannot understand the current Project Store schema, D-051 fails closed before any service starts. This prevents application rollback from becoming an implicit destructive data rollback.

A later recovery UI may help the user select a compatible earlier release and may surface migration recovery snapshots/full `.uvproj.zip` backups, but those remain explicit operations.

### Update discovery

Stage 9 does not require a resident network updater, background polling service or delta-patch format. Release discovery/download policy can be added after the roadmap as a separate signed-channel concern. The first production update artifact remains a complete signed installer so the same build, signing, D-044 and install verification boundaries apply to clean installs and updates.

### Retention

The newly selected release and at least one previously installed release may coexist. Stage 9 does not automatically delete inactive siblings during update. Cleanup policy must never remove the currently selected release and must not remove the only known rollback candidate without an explicit retention decision.

Uninstall remains different from update: the uninstaller removes the application root/all immutable siblings but preserves D-045 user data.

## Required evidence before acceptance

Windows release CI must prove the state machine with real installers and the complete curated release payload:

1. install release ID `A` silently and verify/desktop-smoke it;
2. create persistent D-045 user-data sentinel state;
3. build/install a second release ID `B` from the same known-good payload as an update probe;
4. use a same-length synthetic `B` identity so the update proof does not change the Windows path budget under test;
5. prove `current-release.txt` and the Start Menu shortcut select `B` while verified sibling `A` still exists;
6. deep-verify and desktop-smoke `B`;
7. run installer `A` again;
8. prove `A` is selected again, `B` remains intact, and user data is unchanged;
9. desktop-smoke the reselected `A`;
10. uninstall and prove the immutable application root is removed while D-045 user data survives.

Using the same payload with distinct same-length synthetic release IDs in CI isolates the **version-selection transaction** from unrelated application feature changes. Schema forward/failure behavior is independently covered by D-051 tests.

## Production publication boundary

Unsigned PR/development installers may exercise this state machine. A production update/rollback artifact must pass the Stage 9 code-signing gate before publication. Update transport must never bypass signature/integrity policy merely because an installation already exists.
