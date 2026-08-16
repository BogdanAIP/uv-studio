# D-046 — Exact supported language runtimes and Windows Python release lock

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The development dependency contract intentionally uses bounded direct ranges so maintainers can evaluate dependency upgrades. That is not sufficient for a shipped desktop application: resolving the same ranges on different dates or Python patch levels can produce different transitive graphs.

Stage 9 also cannot simply copy the historical development runtime versions into the installer. The existing permanent CI used floating Python `3.11` and Node `20`; cross-platform evidence already showed that floating Python resolved to different patch releases, and Node 20 is no longer a suitable shipping baseline. A release runtime must be an exact, currently supported version that is proven against UV Studio before it becomes part of the package contract.

## Decision

The first Windows x86_64 Stage 9 release profile pins:

- **CPython 3.13.14**
- **Node.js 24.19.0**

These candidates were selected only after dedicated Windows compatibility jobs proved the existing UV Studio core/unit and frontend build contracts respectively.

The machine-readable profile is `packaging/runtime-profile.windows-x86_64.json`. It identifies the target platform, exact Python version and Python constraints file, plus exact Node version and the existing npm lockfile.

### Python dependency ownership

`requirements-uv.txt` remains the short, human-reviewed set of direct UV Studio runtime requirements with compatibility ranges. It describes what UV Studio intentionally depends on.

`requirements-uv-release-win-x86_64.txt` is the shipping resolution for the selected Python/runtime/platform profile. It contains the complete 32-package graph observed and tested on Windows x86_64 / CPython 3.13.14, pinned as exact `name==version` constraints.

Release installation/build commands must resolve direct requirements through this constraints file rather than installing the broad ranges by themselves.

`tools/verify_release_python_lock.py` then verifies all of the following:

- the executing Python patch version exactly matches the release profile;
- every locked package exists at the exact locked version;
- no application runtime package exists outside the lock, apart from bootstrap package-management tools (`pip`, `setuptools`, `wheel`).

The verifier is deliberately stricter than `pip check`: a dependency graph can be internally consistent while still drifting away from the release that was reviewed and tested.

### Frontend dependency ownership

The frontend already has a complete npm lock (`frontend/package-lock.json`) and CI uses `npm ci`, so Stage 9 does not create a second duplicate frontend package lock. The release profile pins the Node runtime independently to 24.19.0; compatibility CI must prove `npm ci`, lint, high-severity audit and production build on that exact Node version.

## Evidence before acceptance

The Python 3.13.14 Windows compatibility job successfully:

- installed the existing direct core requirements;
- passed `pip check`;
- imported the UV Studio server;
- passed all 379 unit tests;
- recorded the complete 32-package resolved graph used for the release constraints file.

The Node 24.19.0 Windows compatibility job successfully:

- installed the existing `package-lock.json` graph through `npm ci`;
- passed frontend lint;
- passed the configured high-severity npm audit;
- built the production Next frontend.

## Byte-level reproducibility

Exact package versions are necessary but not sufficient for byte-for-byte product integrity. Stage 9 will assemble the actual selected wheels/runtime archives into the Windows release payload and D-044 will record exact file sizes and SHA-256 in the product release manifest. Package index resolution is therefore not the final trust boundary.

Build-only tooling such as PyInstaller or installer compilers must not be added to this runtime lock. They require a separate build-tool contract and must not appear in the installed Python runtime graph.

## Compatibility policy

The existing Python 3.11 and Node 20 permanent application jobs are retained temporarily as backward-compatibility evidence while Stage 9 is in draft. They are not the shipping runtime authority after this decision. Once the packaged application is proven end-to-end on the pinned release profile, permanent CI may be migrated deliberately rather than silently floating versions.

A future Python or Node release upgrade must update the profile and lock only after the same compatibility evidence is repeated. It is a reviewed product-runtime change, not an automatic dependency refresh.
