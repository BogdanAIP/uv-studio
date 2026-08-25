# UV Studio Desktop Update Contract

**Status:** CURRENT SUPPORTING TARGET CONTRACT  
**Decision authority:** D-068

## User outcome

A normal UV Studio user maintains one installed application and updates it in place from the UI instead of accumulating a new side-by-side installation for every release.

Target surface:

```text
Settings / About
  Current version: N
  [Check for updates]

If N+1 exists:
  Version N+1 available
  [What's new]
  [Download and update]

After verified download:
  [Restart and update]
```

Automatic update checking may be configurable. Unattended installation is not the initial default.

## Ownership

The Update Service is product infrastructure below the UI and above the installer/release mechanism.

```text
GitHub Releases / future release source
        |
 machine-readable update manifest
        |
   UV Update Service
  /    |      |      \
check download verify handoff
        |
 out-of-process updater/installer
        |
 maintained UV Studio installation
```

The release source is not product state. GitHub Releases is acceptable for the initial implementation.

## Data boundary

Application/runtime files may be replaced during an update. User-owned data must remain separate and protected:

- Project Store projects and `.uvproj.zip` archives;
- user settings intended to persist;
- imported/project-owned media;
- model/runtime caches where compatible;
- logs/backups according to retention policy.

Application-version migration must never delete project data merely to simplify installation cleanup.

## Version identities

Keep separate:

- UV Studio application version;
- updater/installer compatibility version if needed;
- Project Store schema version;
- production/domain document schema versions;
- model/provider/runtime versions.

A newer application version may migrate older project schemas through the existing Project Store migration boundary; those schema identities do not become the application version.

## Update manifest

The bounded manifest should provide enough data to make a deterministic update decision, at minimum:

```text
version
channel
platform / architecture
artifact identity
integrity digest
signing/verification metadata
release notes
minimum compatible updater/application where required
migration compatibility information where required
```

Do not scrape arbitrary release-page text to decide what executable to install.

## Safety

- verify digest/signature/expected artifact identity before installation;
- fail closed on mismatch;
- do not overwrite a running executable/runtime in place from inside the same process;
- use a proven out-of-process update/installer handoff;
- retain a rollback/recovery path for interrupted replacement;
- surface actionable update failures to the user;
- never use update cleanup to remove project folders.

## Required release evidence

Clean installation and upgrade are separate tests.

Required N-1 -> N scenario:

```text
install previous supported stable N-1
 -> create/open representative real project
 -> persist representative settings/state
 -> invoke/update to candidate N
 -> relaunch N
 -> confirm maintained installation identity
 -> open/migrate project
 -> verify production + Timeline state
 -> verify intended settings survived
 -> complete a representative user workflow
```

The packaged application, not only development servers, must pass this release proof.

## Multiple existing copies

Historical development copies or deliberately side-by-side builds are not automatically merged or deleted. Once the maintained stable installation identity exists, future stable installers/updaters default to replacing that installation. A later cleanup UX may offer removal of known obsolete application copies while protecting project/user data.
