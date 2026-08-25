# D-068 — Desktop in-place updates and version migration

**Status:** Accepted  
**Date:** 2026-08-25

## Context

UV Studio is intended to become a normal installed Windows desktop application. Requiring the user to download and install each release as a separate application would create duplicate installations, stale shortcuts, ambiguous versions and unnecessary risk to project continuity.

The release architecture already requires clean installation, migration, backup/recovery and signed artifacts. It therefore also needs an explicit product-owned update contract rather than treating updates as an installer detail.

## Decision

UV Studio will support **in-place desktop updates** from the installed application through a visible Update UI and a product-owned Update Service.

The normal lifecycle is:

```text
installed UV Studio
 -> check update metadata
 -> show available version + release notes
 -> user chooses Update
 -> download release artifact
 -> verify integrity/signature
 -> close running application
 -> updater replaces the current application installation
 -> run version/project migrations as required
 -> restart UV Studio
 -> verify healthy startup
```

A normal update MUST preserve one installation identity instead of adding another side-by-side installation by default.

### 1. One installed application identity

Program binaries and mutable user/project data are separate concerns.

An update may replace application/runtime files, but MUST NOT delete or relocate user projects, project archives, settings, model/runtime caches or imported media merely because the application version changed.

The installer/updater should detect the existing UV Studio installation and default to updating it. Side-by-side installation may exist only as an explicit advanced/development choice, not the normal release behavior.

### 2. Update UI

The installed application must expose at minimum:

- current application version;
- `Check for updates` action;
- available version when newer;
- release notes or a concise change summary;
- visible download/update progress;
- explicit success/failure state;
- `Restart and update` or equivalent controlled transition when required.

Automatic **checking** may be enabled by preference. Automatic unattended **installation** is not the initial default; installation remains an explicit user action.

### 3. Update source and manifest

The first implementation may use GitHub Releases as the distribution source. UV Studio should consume a bounded update manifest rather than infer release behavior from arbitrary HTML.

The manifest/artifact metadata should include at least:

- application version;
- release channel (`stable` initially; optional preview/dev channels later);
- platform/architecture;
- release artifact identity;
- SHA-256 or stronger integrity digest;
- signing/verification metadata where available;
- release notes/change summary;
- minimum updater/application compatibility when needed;
- migration requirements when needed.

Application version, Project Store schema version and individual production-document schema versions remain separate identities.

### 4. Verification and trust

The updater MUST fail closed when the downloaded artifact does not match the expected digest/signature/identity.

Final public release remains subject to the Stage-9 signing/security/dependency gate. The update mechanism must never silently install an unverified arbitrary executable merely because a remote endpoint returned a newer version string.

### 5. Out-of-process replacement and rollback

The running application must not overwrite its own active executable/runtime in an unsafe partial state. The final updater design therefore uses an out-of-process updater/installer handoff or another proven native mechanism.

Before destructive replacement, the updater must retain enough state to recover from an interrupted/failed update. The exact mechanism may be installer rollback, atomic directory switch, retained previous package or equivalent evidence-backed design.

A failed update must produce a diagnosable state and must not corrupt project data.

### 6. Upgrade compatibility test

Release CI must prove upgrade behavior, not only clean installation.

The required representative flow is:

```text
install supported previous version (N-1)
 -> create/open a real project
 -> persist representative settings/state
 -> update in place to candidate version N
 -> launch N
 -> verify one normal UV Studio installation identity
 -> verify project opens/migrates
 -> verify settings intended to persist remain
 -> verify canonical production/Timeline state remains valid
 -> verify normal user workflow still succeeds
```

At minimum the current release candidate must be tested from the immediately previous supported stable release. Additional migration ranges may be required when schema compatibility policy widens.

Clean-install tests and N-1 -> N upgrade tests are separate release gates; one does not substitute for the other.

### 7. Existing multiple installations

The updater is not required to guess and destructively merge arbitrary historical development copies. Once the maintained installer/update identity exists, future stable releases use that identity in place.

A migration/cleanup UX may detect known older installed stable versions and offer removal or replacement, but user project locations must be protected and never deleted as part of application cleanup.

## Consequences

- Stage 9 must deliver a real Update Service and UI, not just versioned installers.
- Releases must publish machine-readable update metadata and verifiable artifacts.
- Packaging tests must include upgrade paths with real project state.
- Project migrations become part of release compatibility evidence.
- The normal user experience becomes one maintained UV Studio installation that evolves across versions.

## Relationship to earlier decisions

- D-007 makes Windows a first-class target; D-068 defines the maintained Windows desktop update behavior.
- D-009 Project Store remains canonical and is protected from application-file replacement.
- D-038 development lifecycle is unrelated to installed application versioning; Git branch/PR state never becomes update metadata.
- Stage-9 release/signing requirements remain authoritative and are strengthened by the upgrade test defined here.
